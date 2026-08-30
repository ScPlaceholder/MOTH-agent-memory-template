#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wired.py — is component X ACTUALLY wired into module Y? Ask the syntax tree, not the text.

    python wired.py splade recall.py          # is splade wired into recall?
    python wired.py fusion                    # who imports fusion, across the project?
    python wired.py --selftest

★★★★★ WHY THIS EXISTS. 2026-08-25, and it cost an hour plus a false statement to J.

I grepped `recall.py` for `splade`, `rerank`, `fuzzy`. All returned hits. I reported to J that my
system had 10 of 11 architecture boxes wired in.

**They were comments.** One of them was literally a note recording J asking whether SPLADE and
fusion had been tested. I matched prose and reported it as architecture — then concluded the missing
box was RRF fusion and **started building it**, before discovering `fusion.py` had existed since
2026-08-17 with RRF, a passing selftest, and a pre-registered measurement gate.

Third time that day. Earlier: grepped for `fuse`, got counts of 1 and 3, nearly concluded it was
wired — every match was the substring inside the word **re-fuse**.

★★★ THE MECHANICAL POINT. `grep` answers *does this string appear in this file*. It cannot
distinguish code from comment, a definition from a mention, or wiring from **a note about wiring**.
My files are heavily commented on purpose — so the density of prose about a component is highest
exactly where that component is most discussed, which is exactly where I most want a reliable
answer. **Grep's false-positive rate is worst on precisely the questions worth asking.**

★★ AND WHY A TOOL RATHER THAN A NOTE. I wrote the lesson down. I have written variants of it before.
A memo cannot install a skill — the only corrections that have ever stuck are the ones that made the
right thing CHEAPER than the wrong thing. Hand-writing an `ast.parse` every time is not cheaper than
grep. This is. [[a-memo-cannot-install-a-skill]] [[retrieval-first-check-the-record-before-acting]]
"""
import argparse
import ast
import io
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
SKIP = {".git", "__pycache__", "node_modules", ".venv", "venv", ".venv-voice"}


def analyse(path):
    """-> (imports, called_names). From the SYNTAX TREE, so comments cannot contribute.

    ⚠⚠ IMPORTS ARE NOT THE ONLY WIRING, AND THIS TOOL LEARNED THAT BY BEING WRONG.

    Within five minutes of writing it I asked `wired.py fusion` and got "only full_bench.py imports
    it" — which read as *fusion is benchmark-only, not in the live path*. **False.** `whereis.py`
    launches `fusion.py` as a SUBPROCESS:

        subprocess.run([RERANK_PY, os.path.join(HERE, "fusion.py"), query], ...)

    No import statement anywhere. Fully wired, in the live retrieval path, with a fallback that
    announces itself on stderr.

    ★★★ So the pair is symmetric and worth holding together: **grep OVER-reports** (it matches
    comments and notes about wiring), and **import-analysis UNDER-reports** (it misses subprocess,
    importlib, plugin registries, anything dispatched by name). Neither alone answers "is X wired
    in". A string literal naming the file is therefore treated as wiring too — and when the answer
    matters, the last word is still: run it and look at the output.
    """
    try:
        src = io.open(path, encoding="utf-8", errors="replace").read()
        tree = ast.parse(src, path)
    except (SyntaxError, OSError):
        return set(), set()
    imports, calls = set(), set()

    # ★★★ PASS 1 — IMPORTS AND ALIASES. THIS TOOL'S THIRD FALSE-NEGATIVE CLASS, found 2026-08-25.
    #   I asked whether `keyize` was wired into recall.py. This said "imported: YES, called:
    #   nothing", and on that basis I told J an engine on our architecture diagram was dead.
    #   It is not. recall.py:713 runs `_key = _keyize.keyize(_orig)`, behind
    #   `import keyize as _keyize`. The import was seen. The CALL was recorded under the alias
    #   `_keyize`, and check() compares against the real component name, so it never matched.
    #   ⚠ A lazy aliased import inside a function is not exotic — it is exactly how I write
    #     optional engines, so this blind spot pointed straight at the code I most often ask about.
    #   ⚠⚠ Note WHICH WAY the error runs. This tool UNDER-reports, so "not wired" is a weak claim
    #     and "wired" is a strong one. I quoted the weak one as a finding. Every positive it has
    #     given still stands — a tool that misses things does not invent them.
    #   Two passes, because a lazy import lives inside a function and ast.walk can reach the call
    #   before the import statement that names it.
    #
    # ★★★ FOURTH CLASS, FOUND 2026-08-25 AND DELIBERATELY NOT FIXED: a module bound to a LOCAL
    #   VARIABLE by assignment, then called through it. `tg.py` does exactly this, on the send path,
    #   for the guards that matter most:
    #       import claim_guard
    #       cg = _cg if _cg is not None else claim_guard      # ← the test-injection seam
    #       cg.warn(text)
    #   That reports "imported: YES, called: nothing" — the IDENTICAL signature that was wrong about
    #   `keyize` four hours earlier. I nearly told J the send-path guard was dead, and stopped only
    #   because I recognised the shape.
    #   ⚠ Catching it needs dataflow — tracking what each name is bound to, through conditionals and
    #     reassignment. That is a different and much larger tool. Half-building it yields a tracker
    #     that follows simple aliases and silently misses the rest: a MORE CONFIDENT version of the
    #     same blind spot, which is strictly worse than an honest gap.
    #   So it stays documented, and the rule above carries the weight:
    #   **"not wired" from this tool means GO AND LOOK. It never means "it is not wired".**
    aliases = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                real = a.name.split(".")[0]
                imports.add(real)
                if a.asname:
                    aliases[a.asname] = real
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                real = n.module.split(".")[0]
                imports.add(real)
                # `from keyize import keyize as k` — a bare k() is still a call into keyize
                for a in n.names:
                    aliases[a.asname or a.name] = real
        # ★ a STRING LITERAL naming a .py file is a dispatch-by-name, and it is real wiring.
        #   Taken from the syntax tree (ast.Constant), so a comment still cannot contribute.
        elif isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.endswith(".py"):
            imports.add(os.path.basename(n.value)[:-3])
            calls.add("%s (subprocess/by-name)" % os.path.basename(n.value)[:-3])

    # PASS 2 — calls, resolved through the alias table built above.
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                base = f.value.id
                calls.add("%s.%s" % (base, f.attr))
                if aliases.get(base, base) != base:
                    calls.add("%s.%s (via alias %s)" % (aliases[base], f.attr, base))
            elif isinstance(f, ast.Name):
                calls.add(f.id)
                if aliases.get(f.id, f.id) != f.id:
                    calls.add("%s.%s (via alias)" % (aliases[f.id], f.id))
    return imports, calls


def check(component, module_path):
    imports, calls = analyse(module_path)
    used = {c for c in calls if c.split(".")[0] == component}
    return component in imports, sorted(used)


def who_imports(component, root=HERE):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP and not d.startswith(".")]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            p = os.path.join(dirpath, fn)
            imports, calls = analyse(p)
            if component in imports:
                out.append((os.path.relpath(p, root),
                            sorted(c for c in calls if c.split(".")[0] == component)))
    return sorted(out)


def main(argv):
    ap = argparse.ArgumentParser(description="Is X actually wired into Y? AST, not grep.")
    ap.add_argument("component", nargs="?")
    ap.add_argument("module", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.component:
        ap.error("name a component")

    comp = a.component.replace(".py", "")
    if a.module:
        imported, used = check(comp, a.module)
        print("\n  %s in %s" % (comp, a.module))
        print("    imported : %s" % ("YES" if imported else "no"))
        print("    called   : %s" % (", ".join(used) if used else "nothing"))
        if not imported:
            print("\n  ⚠ NOT WIRED IN. If grep found the name, it found a comment or a string.")
        print()
        return 0 if imported else 1

    hits = who_imports(comp)
    print("\n  who imports %s\n" % comp)
    if not hits:
        print("    NOBODY. It exists (or does not) but nothing uses it.")
        print("    ⚠ That is a real answer — an orphan module is invisible to grep-based checks,")
        print("      which will happily match its own filename and every comment about it.\n")
        return 1
    for p, used in hits:
        print("    %-42s %s" % (p, ", ".join(used[:4]) if used else "(imported, no direct calls seen)"))
    print()
    return 0


def selftest():
    """★ The tool MUST distinguish a comment from an import, or it is grep with extra steps."""
    import tempfile
    import shutil
    fails = []
    tmp = tempfile.mkdtemp(prefix="wired_selftest_")
    try:
        # a file that MENTIONS splade in a comment and a string, but never imports it
        decoy = os.path.join(tmp, "decoy.py")
        io.open(decoy, "w", encoding="utf-8").write(
            "# splade is great and we should wire splade in one day\n"
            "MSG = 'splade results'\n"
            "import os\n"
            "def f():\n    return os.getcwd()\n")
        imported, used = check("splade", decoy)
        if imported or used:
            fails.append("a COMMENT + STRING mention was reported as wired — this is grep again")

        # a file that genuinely imports and calls it
        real = os.path.join(tmp, "real.py")
        io.open(real, "w", encoding="utf-8").write(
            "import splade\ndef g():\n    return splade.rank('q')\n")
        imported, used = check("splade", real)
        if not imported:
            fails.append("a genuine import was missed")
        if "splade.rank" not in used:
            fails.append("a genuine call was missed: %s" % used)

        # ★★ THE ALIASED LAZY IMPORT — the exact shape that made this tool call a live engine dead.
        #    recall.py does `import keyize as _keyize` inside a function, then `_keyize.keyize(q)`.
        #    Before 2026-08-25 that reported "imported: YES, called: nothing", and I repeated it to
        #    J as evidence that a documented engine was not on the retrieval path.
        aliased = os.path.join(tmp, "aliased.py")
        io.open(aliased, "w", encoding="utf-8").write(
            "def h(q):\n"
            "    import splade as _sp\n"
            "    return _sp.rank(q)\n")
        imported, used = check("splade", aliased)
        if not imported:
            fails.append("an aliased import was missed entirely")
        if not any("splade.rank" in u for u in used):
            fails.append("an aliased CALL was missed — the 2026-08-25 false negative: %s" % used)

        # ...and the alias must not make the decoy start passing. Widening a matcher is exactly how
        # an under-reporting tool turns into an over-reporting one.
        if any(check("splade", decoy)):
            fails.append("alias handling made the comment-only decoy report as wired")

        # from-import form must count too
        fromf = os.path.join(tmp, "fromf.py")
        io.open(fromf, "w", encoding="utf-8").write("from splade import rank\n")
        if not check("splade", fromf)[0]:
            fails.append("`from X import y` was not recognised as wiring")

        # ★★ SUBPROCESS DISPATCH IS WIRING. This tool's own false negative, caught by using it:
        #    whereis.py launches fusion.py by name with no import, and the first version reported
        #    it unwired. A comment must still NOT count — that is the whole point of the tool — so
        #    this asserts both halves at once.
        sub = os.path.join(tmp, "sub.py")
        io.open(sub, "w", encoding="utf-8").write(
            "import subprocess, os\n"
            "def h():\n"
            "    return subprocess.run(['python', os.path.join(HERE, 'fusion.py'), q])\n")
        if not check("fusion", sub)[0]:
            fails.append("subprocess dispatch by filename was not recognised as wiring")

        nosub = os.path.join(tmp, "nosub.py")
        io.open(nosub, "w", encoding="utf-8").write(
            "# we should call fusion.py here one day\nX = 1\n")
        if check("fusion", nosub)[0]:
            fails.append("a COMMENT naming fusion.py was counted as wiring — grep again")

        # a file that cannot be parsed must fail SAFE (report not-wired), never raise
        bad = os.path.join(tmp, "bad.py")
        io.open(bad, "w", encoding="utf-8").write("def (((\n")
        try:
            if check("splade", bad)[0]:
                fails.append("an unparseable file reported a component as wired")
        except Exception as e:
            fails.append("an unparseable file raised %s instead of failing safe" % type(e).__name__)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    for f in fails:
        print("   -", f)
    print("wired selftest:", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
