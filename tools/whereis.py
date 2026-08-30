#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""whereis.py — look in memory BEFORE looking on disk.

    python whereis.py "the thing you are about to go hunting for"
    python whereis.py --selftest

★★★★★ THE ORDER IS THE ENTIRE POINT, and it is the only non-obvious idea in this repository.

A memory system fails silently. It does not throw; the agent simply answers from context and never
discovers the answer was already on disk. Telling an agent "remember to search your memory first"
does not fix this, because the instruction competes with an urge to just go and look — and the urge
wins, every time, at exactly the moment it matters.

So do not add a rule. **Change the cost.** This tool wraps the filesystem search you were going to
run anyway and puts recall in front of it. Searching memory stops being a thing you must remember to
do and becomes a thing that happens because you reached for the search you already wanted.

    the rule version:   "check memory first"      -> obeyed when convenient
    the cost version:   memory search is free,     -> obeyed always, because it costs
                        it is on the way              nothing to comply

⚠ IF YOU CHANGE ONE THING IN THIS FILE, DO NOT REORDER IT. Running the filesystem walk first and the
  recall second produces identical OUTPUT and destroys the entire benefit: by the time memory speaks,
  the agent has already found a path and stopped reading. The selftest asserts the ORDER, not the
  output, for exactly that reason — an output test cannot see this bug.
"""
import argparse
import fnmatch
import io
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recall as _recall  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".mypy_cache"}


def fs_search(patterns, root, limit=10):
    """Filename search over ALL query terms, ranked by how many of them a filename contains.

    ★★ IT USED TO SEARCH ONLY THE FIRST TERM, so the answer depended on WORD ORDER: "deployment
       migration" found nothing while "migration deployment" found `the-migration-ran-twice.md`.
       Same question, same corpus, different result — and nothing told the user that reordering
       their own words would have worked.

       This is the SECOND defect in this one line. The first was searching the first RAW word, so
       "the widget index" searched the disk for "the". That fix moved to the first MEANINGFUL word
       and stopped — repairing the visible half while a smaller version of the same assumption
       survived. Worth remembering: a fix aimed at the instance rather than the shape leaves the
       shape behind.
    """
    if isinstance(patterns, str):
        patterns = [patterns]
    pats = [p.strip("*").lower() for p in patterns if p and p.strip("*")]
    if not pats:
        return []
    scored = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for fn in filenames:
            low = fn.lower()
            n = sum(1 for p in pats if fnmatch.fnmatch(low, "*%s*" % p))
            if n:
                scored.append((n, os.path.join(dirpath, fn)))
    scored.sort(key=lambda x: -x[0])          # most terms matched first; stable within a tier
    return [p for _n, p in scored[:limit]]


def whereis(query, memory_roots=None, fs_root=None, top=5, _trace=None):
    """Memory first, filesystem second. `_trace` records the call order for the selftest."""
    trace = _trace if _trace is not None else []

    trace.append("recall")
    mem = _recall.recall(query, memory_roots, top=top)

    # ★★★★★ USE A MEANINGFUL TERM, NOT THE FIRST RAW WORD — found by external review, 2026-08-25.
    #   This was `query.split()[0]`, so **"the widget index" searched the filesystem for "the"**.
    #   The tool whose entire stated purpose is putting memory in front of a file search was, on its
    #   file-search half, hunting for a stopword. Every selftest passed throughout, because they
    #   asserted the ORDER of the two calls and never the QUALITY of either.
    #   ⚠ The lesson is not "add another test"; it is that a test aimed at one property is silent
    #     about every other property in the same function, and silence reads as health.
    trace.append("filesystem")
    _qt = _recall.terms(query)
    fs = fs_search(_qt or (query.split() or [query]), fs_root or PROJECT)

    return mem, fs


def main(argv):
    ap = argparse.ArgumentParser(description="Search memory before searching the disk.")
    ap.add_argument("query", nargs="*")
    ap.add_argument("--root", action="append", default=None, help="memory dir (repeatable)")
    ap.add_argument("--fs-root", default=None)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    q = " ".join(a.query)
    if not q.strip():
        ap.error("give me something to look for")

    mem, fs = whereis(q, a.root, a.fs_root)

    print("\n  1. WHAT THE RECORD ALREADY SAYS — read this before the file list\n")
    if mem:
        for s, path, desc, matched in mem:
            print("     %6.2f  %s" % (s, os.path.basename(path)))
            if desc:
                print("             %s" % desc[:100])
    else:
        print("     nothing in memory matched. That is a fact about this corpus, not a verdict on")
        print("     the question — and it is the moment to consider writing the answer down after.")

    print("\n  2. FILES ON DISK\n")
    if fs:
        for p in fs:
            print("     %s" % p)
    else:
        print("     no filename matched")
    print()
    return 0


def selftest():
    """Asserts the ORDER. An output-equality test cannot detect the only bug that matters here."""
    fails = []
    tmp = tempfile.mkdtemp(prefix="whereis_selftest_")
    # ⚠ Cleaned up at the end. Before this, every --selftest run left a directory behind;
    #   15 had accumulated in the system temp dir before an external review pointed at it.
    #   A tool that litters while proving it is healthy is making a claim it undermines.
    memdir = os.path.join(tmp, "memory")
    os.makedirs(memdir)
    io.open(os.path.join(memdir, "widget-index-lives-in-tools.md"), "w", encoding="utf-8").write(
        "---\nname: widget-index-lives-in-tools\ndescription: The widget index is generated, not stored\n"
        "metadata:\n  type: reference\n---\n\nThe widget index is rebuilt by tools/build.py.\n")
    os.makedirs(os.path.join(tmp, "tools"))
    io.open(os.path.join(tmp, "tools", "widget_build.py"), "w", encoding="utf-8").write("# widget\n")

    # ★★★★★ THE LOAD-BEARING ASSERTION: recall must be consulted BEFORE the filesystem walk.
    #   Reordering the two calls leaves every returned value identical, so only a trace can see it.
    trace = []
    mem, fs = whereis("widget", [memdir], tmp, _trace=trace)
    if trace != ["recall", "filesystem"]:
        fails.append("ORDER VIOLATED: expected recall before filesystem, got %r. This is the one "
                     "property the tool exists for and it produces identical output when broken."
                     % (trace,))
    # ★★★★★ THE STOPWORD REGRESSION. "the widget index" used to search the disk for "the".
    #   Asserting the filesystem half actually looks for a MEANINGFUL term, not word zero.
    tr3 = []
    m3, f3 = whereis("the widget index", [memdir], tmp, _trace=tr3)
    if not f3:
        fails.append("STOPWORD BUG: a query beginning with a stopword found no files — the disk "
                     "search is using the first RAW word ('the') instead of the first meaningful one")

    if not mem:
        fails.append("memory hit was not found — the fixture plainly contains it")
    if not fs:
        fails.append("filesystem hit was not found — the fixture plainly contains it")

    # ⚠ NEGATIVE CONTROL: a query matching nothing must return two empties, not an exception and not
    #   a fabricated hit. Empty is a legitimate answer; a crash or an invention is not.
    trace2 = []
    m2, f2 = whereis("zzz-nonexistent-token", [memdir], tmp, _trace=trace2)
    if m2 or f2:
        fails.append("returned hits for a token absent from the fixture")
    if trace2 != ["recall", "filesystem"]:
        fails.append("order not preserved on the empty path (%r)" % (trace2,))

    for f in fails:
        print("   -", f)
    print("whereis selftest:", "PASS" if not fails else "FAIL")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
