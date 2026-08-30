#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""benchmark.py — the first test in this repository that can actually FAIL.

    python benchmark.py                 # run against the shipped sample corpus
    python benchmark.py --root <dir> --probes <file>
    python benchmark.py --selftest

★★★★★ WHY THIS EXISTS, AND WHY IT IS DIFFERENT FROM A SELFTEST.

The tools' `--selftest`s check that the code does what the code intends. **None of them establish
that retrieval WORKS**, because they build their own tiny fixtures and then ask questions about
them — using the fixture's own words.

The trap this avoids is specific and easy to fall into: an agent evaluating its own memory picks the
probe questions, so it reaches for topics it already knows are absent, watches nothing come back,
and records a pass. **That test cannot fail.** It confirms that absent things are absent, which is
equally true of a broken system and an empty folder.

So this benchmark ships with a **corpus somebody else wrote** and probes in **three sections that are
reported separately and never summed**, because each answers a different question:

  [1] works     Questions phrased the way a person actually asks, months later. **This is the score.**
                Near-perfect is the expectation; a miss here is a real bug.
  [2] boundary  Questions sharing ZERO content words with their answer. **Expected to find nothing.**
                Not failures, not scored — this is the documented limit, shown with its fix.
  [3] absent    Topics not in the corpus at all. Must return nothing; proves it does not fabricate.

⚠ **SECTIONS [2] AND [3] CANNOT FAIL, AND THAT IS WHY THEY ARE NOT SCORED.** [3] returns nothing for
  a broken system, an empty folder and a perfect one alike. [2] finding nothing is correct behaviour.
  Folding either into the headline is how a benchmark starts flattering itself — or, as happened
  here, starts *libelling* itself: with [2] in the main table the summary read `hit@1: 5/10`, which a
  stranger reads as mediocrity, while the same corpus answered the natural phrasing of those same
  questions at rank 1.
"""
import argparse
import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recall as _recall  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEF_CORPUS = os.path.join(ROOT, "sample", "memory")
DEF_PROBES = os.path.join(ROOT, "sample", "probes.json")

MIX_CORPUS = os.path.join(ROOT, "sample", "mixed")
MIX_PROBES = os.path.join(ROOT, "sample", "mixed_probes.json")

# Every (corpus, probes) pair shipped in this repo. The selftest iterates this, so adding a corpus
# adds its validation automatically rather than leaving it silently unchecked.
SHIPPED_PAIRS = [(DEF_CORPUS, DEF_PROBES), (MIX_CORPUS, MIX_PROBES)]


def _wrap(text, width):
    """Minimal greedy wrapper — keeps the 'why' notes readable without pulling in textwrap."""
    out, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    return out


def _rank(q, expect, corpus, top):
    hits = _recall.recall(q, [corpus], top=top)
    names = [os.path.splitext(os.path.basename(h[1]))[0] for h in hits]
    return (names.index(expect) + 1 if expect in names else 0), names


def run(corpus, probes_path, top=3):
    """-> (works, boundary, absent). THREE SECTIONS, NEVER SUMMED.

    ★★★★★ THE SPLIT IS THE WHOLE DESIGN, and it was a correction.

    These probes used to live in one table, so a query deliberately written to share NO vocabulary
    with its answer appeared as a headline `MISS` beside genuine results, and the summary read
    `hit@1: 5/10` — which a stranger reads as "this system is mediocre".

    It was not measuring the system. It was measuring how adversarially the probe author had chosen
    to write the questions. **Asking a note about military strategy whether the sky is blue is not a
    hard query, it is a nonsense one**, and scoring it as a failure manufactures a defect that never
    existed. Meanwhile the same corpus answers the NATURAL phrasing of those very questions at rank
    1.

    So each section now answers exactly one question and is reported on its own:

      works     Does it work? Ask the way a human asks. Should be near-perfect. **This is the score.**
      boundary  Where does it stop? Zero shared vocabulary. **Expected to find nothing — not scored,
                not a failure.** Shown so a user meets the limit here, with the fix beside it,
                instead of discovering it alone in their own corpus and filing a bug.
      absent    Does it invent things? Must return nothing. Cannot fail for a broken system, so it
                is never scored either.

    ⚠ A boundary probe that unexpectedly SUCCEEDS is reported too. It means the limit moved, and a
      documented limit that silently stopped being true is worse than an undocumented one.
    """
    # ★★★★★ THE REFUSALS BELOW ARE THE MOST IMPORTANT CODE IN THIS FILE, and three of them were
    #   MISSING until an external review found them — in the one repository whose headline lesson is
    #   that empty is not the same as clean. All three are the same disease:
    #
    #     • the corpus EXISTS but is empty          -> scored 0/10, read as "retrieval is broken"
    #     • the probes file is missing or corrupt   -> raw traceback at a non-programmer
    #     • the probes file parses but has NO probes -> **"VERDICT: WORKING"**
    #
    #   That last one is the worst thing this project has produced. A malformed probes file — which
    #   is exactly what an agent generating probes for a user will occasionally emit — made the
    #   acceptance check report success over ZERO tests. A benchmark that cannot fail, shipped
    #   inside the document arguing against benchmarks that cannot fail.
    #
    #   "Cannot tell" is not "measured zero". Every one of these now refuses and says why.
    if not os.path.isdir(corpus):
        raise SystemExit(
            "corpus not found: %s\n"
            "⚠ REFUSING TO REPORT A SCORE. A missing corpus makes every probe 'fail' and every\n"
            "  absent-control 'pass' — a number that describes the missing folder, not the\n"
            "  retrieval. Point --root at a real corpus." % corpus)

    n_md = sum(1 for _r, _d, fs in os.walk(corpus) for f in fs if f.endswith(".md"))
    if not n_md:
        raise SystemExit(
            "corpus is empty: %s\n"
            "⚠ REFUSING TO REPORT A SCORE. The folder exists but contains no .md files, so every\n"
            "  probe would 'fail' and every absent-control would 'pass'. That is a description of\n"
            "  an empty folder, not a measurement of retrieval — and it reads as a broken system.\n"
            "  (Note: only .md is indexed. A folder of .txt or .py will look empty here.)" % corpus)

    try:
        spec = json.load(io.open(probes_path, encoding="utf-8"))
    except IOError:
        raise SystemExit(
            "probes file not found: %s\n"
            "⚠ REFUSING TO RUN. Pass --probes with a real file, or omit it to use the shipped\n"
            "  example probes." % probes_path)
    except ValueError as e:
        raise SystemExit(
            "probes file is not valid JSON: %s\n  (%s)\n"
            "⚠ REFUSING TO RUN. A half-written probes file must not become a score." % (probes_path, e))
    if not isinstance(spec, dict):
        raise SystemExit(
            "probes file has the wrong shape: %s\n"
            "⚠ REFUSING TO RUN. Expected an object with 'works' / 'boundary' / 'absent' keys;\n"
            "  got %s. Copy sample/probes.json as a starting shape." % (probes_path, type(spec).__name__))
    if "probes" in spec and "works" not in spec:
        raise SystemExit(
            "%s uses the old single-'probes' layout.\n"
            "⚠ REFUSING TO RUN. That layout scored documented limits as failures. Split it into\n"
            "  'works' / 'boundary' / 'absent' — see sample/probes.json." % probes_path)
    if not spec.get("works"):
        raise SystemExit(
            "no 'works' probes in %s\n"
            "⚠ REFUSING TO REPORT A VERDICT. With nothing to ask, every check trivially passes and\n"
            "  this would print WORKING having tested NOTHING — a benchmark that cannot fail, which\n"
            "  is the one thing this tool exists to prevent. Add questions you know the answers to."
            % probes_path)

    works = []
    for p in spec.get("works", []):
        rank, names = _rank(p["q"], p["expect"], corpus, top)
        works.append((p["q"], p["expect"], rank, names))

    boundary = []
    for p in spec.get("boundary", []):
        rank, names = _rank(p["q"], p["expect"], corpus, top)
        boundary.append((p["q"], p["expect"], rank, p.get("why", "")))

    absent = []
    for q in spec.get("absent", []):
        absent.append((q, _recall.recall(q, [corpus], top=top)))
    return works, boundary, absent


def overlap_study(pairs=None, top=3):
    """-> rows of (tag, n_shared_words, rank, query).

    ★★★★★ THE MOST USEFUL MEASUREMENT IN THIS REPOSITORY, and it is not a score.

    A hit@1 figure is nearly meaningless on its own, because it silently reports *how the probes
    were written*. Write questions using the answer file's vocabulary and it approaches 100%. Write
    them avoiding that vocabulary entirely and it approaches 0. The number moves with the probe
    author's discipline, not with the retrieval.

    So sort every probe by the one variable that actually governs a lexical matcher: **how many
    content words the question shares with its answer file.** That turns an opinion about quality
    into a boundary you can act on. See `--overlap`.
    """
    rows = []
    for corpus, probes_path in (pairs or SHIPPED_PAIRS):
        tag = os.path.basename(corpus)
        spec = json.load(io.open(probes_path, encoding="utf-8"))
        # ⚠ BOTH sections, deliberately. 'works' and 'boundary' are not two kinds of probe — they are
        #   one continuum, separated only by shared vocabulary. Reading one section would hide that,
        #   and would also leave half the probe set unvalidated while still printing PASS.
        for p in spec.get("works", []) + spec.get("boundary", []):
            path = os.path.join(corpus, p["expect"] + ".md")
            if not os.path.exists(path):
                continue
            body = io.open(path, encoding="utf-8", errors="replace").read()
            shared = set(_recall.terms(p["q"])) & set(_recall.terms(body))
            hits = _recall.recall(p["q"], [corpus], top=top)
            names = [os.path.splitext(os.path.basename(h[1]))[0] for h in hits]
            rank = names.index(p["expect"]) + 1 if p["expect"] in names else 0
            rows.append((tag, len(shared), rank, p["q"]))
    return rows


def print_overlap(rows, top=3):
    # ⚠ `top` IS A PARAMETER BECAUSE IT USED TO BE A LITERAL, AND THE LITERAL LIED.
    #   This printed `"found in top %d" % 3` — a format placeholder filled with a constant, which is
    #   the fossil of a value that WAS a variable. Meanwhile `--top` is a real flag threaded through
    #   run(), verify() and the score line. It was never threaded here, so `--overlap --top 10`
    #   silently computed and labelled at 3 and gave the user no sign their flag did nothing.
    #   A hardcoded number in output that nothing keeps in sync with the real setting is a label
    #   that becomes a lie the first time the setting changes.
    zero = [r for r in rows if r[1] == 0]
    some = [r for r in rows if r[1] > 0]
    zf = sum(1 for r in zero if r[2] > 0)
    sf = sum(1 for r in some if r[2] > 0)
    s1 = sum(1 for r in some if r[2] == 1)

    print("\n  WHERE LEXICAL RETRIEVAL STOPS  (%d probes, %d corpora)\n"
          % (len(rows), len(set(r[0] for r in rows))))
    print("    shared content words     probes    found in top %d" % top)
    print("    ---------------------    ------    ---------------")
    print("    none                     %6d    %d" % (len(zero), zf))
    print("    one or more              %6d    %d   (%d at rank 1)" % (len(some), sf, s1))
    if zero:
        print("\n    the probes that share NO word with their answer:")
        for tag, n, rank, q in zero:
            print("      %-6s %-5s %s" % (tag, ("rank %d" % rank) if rank else "MISS", q[:58]))
    print("\n  ⚠ Read this rather than the hit@1 figure. hit@1 mostly reports how many zero-overlap")
    print("    probes the author happened to write; this reports the boundary itself.\n")


def verify(root, probes_path, top=3):
    """★★★★★ THE ACCEPTANCE TEST — written for the person who COMMISSIONED the work, not the one who
    did it.

    The realistic way this template gets used: someone who can read code and design an architecture,
    but does not write code freehand, asks their agent to build it. The agent can. The agent will
    produce something that looks exactly right.

    Then the only question that matters — *did it work?* — gets asked of **the agent that just built
    it**, which will answer yes, sincerely. That is not dishonesty; it is the failure this whole
    repository is about. Correct-looking code that was never exercised is the default output of any
    builder, human or otherwise.

    So this mode exists to be run BY THE USER and READ BY THE USER. Not summarised by the agent.
    One command, plain English, and a verdict that can be pasted to somebody else unaltered.

    ⚠ It must therefore state what it CANNOT check, or it becomes the rubber stamp it replaces.
    """
    ok_run = True
    print("\n" + "=" * 74)
    print("  ACCEPTANCE CHECK — run this yourself and read this output, not a summary of it.")
    print("=" * 74)

    try:
        works, boundary, absent = run(root, probes_path, top)
    except SystemExit as e:
        print("\n  ✗ COULD NOT RUN: %s\n" % e)
        print("  This is a real failure. The tool could not even reach your memory files.\n")
        return 1

    # ★★★★★ DO THE PROBES EVEN BELONG TO THIS CORPUS? Check before scoring anything.
    #
    #   Caught by running my own instructions instead of trusting them. `docs/BUILD_PROMPTS.md`
    #   stage 0 says "run --verify against your memory folder" — so a user does exactly that, keeps
    #   the DEFAULT probes (which name files in `sample/`), and gets **"0 of 10. NOT WORKING."** in
    #   red, with a wall of failures, while nothing whatsoever is wrong.
    #
    #   That is a manufactured failure in the one file whose entire job is to prevent manufactured
    #   failures — and it lands on a first-time user who cannot read the code to discover otherwise.
    #   They would conclude the system is broken and be completely reasonable to do so.
    #
    #   Same principle as run() refusing a missing corpus: **"these do not go together" is not
    #   "measured zero".** A score computed over mismatched inputs is not a weak result, it is not a
    #   result. Refuse, and say precisely what to do instead.
    spec_names = [p[1] for p in works] + [p[1] for p in boundary]
    present = [n for n in spec_names if os.path.exists(os.path.join(root, n + ".md"))]
    if spec_names and not present:
        print("\n  ⚠ THESE PROBES ARE NOT FOR THIS CORPUS — REFUSING TO SCORE.\n")
        print("    Not one of the %d files these questions expect exists in:" % len(spec_names))
        print("        %s\n" % root)
        print("    That is a mismatch, NOT a failure. Scoring it would print '0 of %d' and a red"
              % len(works))
        print("    verdict, which would be a manufactured defect rather than a measurement.\n")
        print("    You have pointed --root at your own notes while still using the example")
        print("    questions, which name files in sample/. Do one of these:\n")
        print("      • Check the shipped example works:   python tools/benchmark.py --verify")
        print("      • Check YOUR notes: write your own probes and pass --probes <yourfile>.")
        print("        Copy sample/probes.json as a starting shape. Ten questions you already")
        print("        know the answers to is enough, and writing them yourself is the point —")
        print("        if your agent writes the questions too, the exam is circular.\n")
        return 2
    if len(present) < len(spec_names):
        print("\n  ⚠ PARTIAL MISMATCH: %d of %d expected files are missing from this corpus."
              % (len(spec_names) - len(present), len(spec_names)))
        print("    Those questions cannot succeed and will appear below as failures that are not")
        print("    yours. Fix the probe file before trusting the verdict.\n")

    missed = [r for r in works if r[2] == 0]
    weak = [r for r in works if r[2] > 1]
    fabricated = [(q, h) for q, h in absent if h]

    print("\n  1. Can it find things you know are there?")
    print("     %d of %d realistic questions found their answer." % (len(works) - len(missed), len(works)))
    if missed:
        ok_run = False
        print("     ✗ THESE FOUND NOTHING — this is the failure that matters:")
        for q, exp, _, _ in missed:
            print("         %s" % q[:64])
            print("             should have found: %s" % exp)
    if weak:
        print("     • %d found it, but not first. Not a failure; worth a look." % len(weak))

    print("\n  2. Does it make things up?")
    if fabricated:
        ok_run = False
        print("     ✗ %d question(s) about topics NOT in your notes returned results anyway." % len(fabricated))
        for q, h in fabricated:
            print("         %r returned %d hit(s)" % (q, len(h)))
    else:
        print("     No. %d questions about absent topics returned nothing, correctly." % len(absent))

    # ★★★ LIST THEM, do not just count them.
    #   `docs/BUILD_PROMPTS.md` stage 6 tells the reader to "find the questions listed under Where
    #   does it stop" and compare after adding embeddings — and this section printed a bare COUNT,
    #   so that instruction was impossible to follow. Found by re-reading my own instructions against
    #   the actual output rather than trusting them; second one of exactly this kind in an hour.
    #
    #   And a count was the wrong output regardless. These are the only failures in the whole report
    #   with a free fix available to the reader, so summarising them to a number hides the single
    #   most actionable thing the tool knows.
    # ⚠ COUNT THE TWO CASES SEPARATELY. The header used to say "N find nothing" over a list in which
    #   one of them had MOVED and now ranked 1 — the summary contradicting its own detail one line
    #   later. Caught only by exercising the MOVED branch, which had never run.
    still = [b for b in boundary if not b[2]]
    moved = [b for b in boundary if b[2]]
    print("\n  3. Where does it stop?")
    if moved:
        print("     %d question(s) share no wording with their answer: %d still find nothing, "
              "%d NOW FIND IT." % (len(boundary), len(still), len(moved)))
    else:
        print("     %d question(s) share no wording at all with their answer, and find nothing."
              % len(boundary))
    for q, exp, rank, why in boundary:
        if rank:
            print("       ⚠ MOVED — now finds %s at rank %d. The documented limit has changed;" % (exp, rank))
            print("         update the docs, because a limit that quietly stopped being true")
            print("         misleads worse than no limit at all.")
            print("           %s" % q[:66])
        else:
            print("       • %s" % q[:66])
            print("           should find: %s" % exp)
    print("\n     That is expected and documented — the known limit, not a defect. **And it is")
    print("     fixable by you, for free:** add the words you would SEARCH with to those files'")
    print("     `description` lines. Measured on the shipped corpora, doing that rescued 4 of 4,")
    print("     every one to rank 1. See docs/FORMAT.md.")

    print("\n" + "-" * 74)
    if ok_run:
        print("  VERDICT: WORKING. Every realistic question found its answer, and it invented nothing.")
    else:
        print("  VERDICT: NOT WORKING YET. Section 1 or 2 above has a ✗. Show that to whoever built")
        print("           it — it is a specific, reproducible failure, not a vague complaint.")
    print("-" * 74)

    # ⚠ An acceptance test that lists only what it proved is the rubber stamp it was meant to replace.
    print("\n  WHAT THIS DOES NOT TELL YOU:")
    print("    • Nothing about YOUR real notes unless you pointed --root at them. By default this")
    print("      checks the shipped example corpus, which proves the tools run and nothing more.")
    print("    • Nothing about whether the probes are good. If your agent WROTE the probes as well")
    print("      as the code, this check is circular — it picked both the exam and the answers.")
    print("      Write at least a few questions yourself. That is the part nobody can do for you.")
    print("    • Nothing about the engines in the architecture diagram that are not in this repo.\n")
    return 0 if ok_run else 1


def _pos_int(v):
    """--top must be >= 1.

    argparse accepted -1 happily, and `hits[:-1]` silently DROPS THE LAST RESULT rather than
    erroring — so `--top -1` returned a quietly incomplete answer, and in benchmark.py printed
    `hit@-1` beside a wrong score. A wrong number that looks like a number is worse than a crash.
    """
    import argparse as _a
    i = int(v)
    if i < 1:
        raise _a.ArgumentTypeError("--top must be 1 or more (got %s)" % v)
    return i


def main(argv):
    ap = argparse.ArgumentParser(description="Measure retrieval against a known-answer corpus.")
    ap.add_argument("--root", default=DEF_CORPUS)
    ap.add_argument("--probes", default=DEF_PROBES)
    ap.add_argument("--top", type=_pos_int, default=3)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--overlap", action="store_true",
                    help="report WHERE lexical retrieval stops, across every shipped corpus")
    ap.add_argument("--verify", action="store_true",
                    help="plain-English acceptance check — run this yourself, read it yourself")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.overlap:
        # ★ THREAD --top THROUGH. It reached run(), verify() and the score line and stopped here,
        #   so `--overlap --top 10` used 3 and said 3. Found by a local reviewer that got the
        #   MECHANISM right and the consequence wrong: it said print_overlap "ignores the provided
        #   top parameter", when there was no parameter to ignore — it had never been passed.
        print_overlap(overlap_study(top=a.top), top=a.top)
        return 0
    if a.verify:
        return verify(a.root, a.probes, a.top)

    works, boundary, absent = run(a.root, a.probes, a.top)
    at1 = sum(1 for r in works if r[2] == 1)
    atk = sum(1 for r in works if r[2] > 0)
    n = len(works)

    print("\n  corpus: %s" % a.root)
    print("\n  [1] DOES IT WORK — %d questions phrased the way a person actually asks\n" % n)
    for q, exp, rank, names in works:
        mark = "hit@1" if rank == 1 else ("hit@%d" % rank if rank else "MISS ")
        print("    %-6s %s" % (mark, q[:66]))
        if rank != 1:
            print("             wanted %s" % exp)
            print("             got    %s" % (", ".join(names[:3]) or "nothing"))
    print("\n    hit@1: %d/%d    hit@%d: %d/%d      <- THIS is the score" % (at1, n, a.top, atk, n))

    # ★★ Reported, never scored. These are the documented edge: questions sharing no vocabulary with
    #    their answer. Finding nothing here is CORRECT BEHAVIOUR and printing it as a failure was the
    #    defect this section exists to undo.
    if boundary:
        print("\n  [2] WHERE IT STOPS — %d question%s sharing NO word with their answer"
              % (len(boundary), "" if len(boundary) == 1 else "s"))
        print("      (expected to find nothing; NOT failures, NOT scored)\n")
        surprises = 0
        for q, exp, rank, why in boundary:
            if rank:
                surprises += 1
                print("    ⚠ MOVED  %s" % q[:64])
                print("             found %s at rank %d — the documented limit is no longer true" % (exp, rank))
            else:
                print("    as documented   %s" % q[:60])
                if why:
                    for line in _wrap(why, 74):
                        print("                    %s" % line)
        print("\n    ⚠ The fix for every one of these is free and belongs to whoever writes the note:")
        print("      put the words you would SEARCH with into the description. Measured: doing that")
        print("      rescued 4 of 4 of these, every one to rank 1. See docs/FORMAT.md.")
        if surprises:
            print("\n    ⚠ %d boundary case(s) started working. Good news, but update the docs — a" % surprises)
            print("      documented limit that quietly stopped being true misleads worse than none.")

    bad = [(q, h) for q, h in absent if h]
    print("\n  [3] DOES IT INVENT THINGS (not scored): %d absent topics, %d returned hits"
          % (len(absent), len(bad)))
    for q, h in bad:
        print("    ⚠ %r returned %d hit(s) — the matcher is too loose" % (q, len(h)))
    # ⚠ Sections [2] and [3] are deliberately absent from the verdict. [2] finding nothing is the
    #   documented design; [3] cannot fail for a broken system. Only [1] can be red.
    # ★ RED means a realistic question FAILED TO FIND ITS ANSWER AT ALL. Rank 2 is the system
    #   working — demanding rank 1 everywhere would re-create the problem this restructure fixed,
    #   just one notch quieter: a green tool reporting a failure that is not one. hit@1 stays visible
    #   above as the quality figure; it is simply not the pass/fail line.
    missed = [r for r in works if r[2] == 0]
    ok = not missed and not bad
    print("\n  VERDICT: %s" % ("working — every realistic question found its answer" if ok
                               else "SOMETHING IS WRONG — %d realistic question(s) found nothing"
                                    % len(missed)))
    print("    Only section [1] counts. [2] is the documented limit and is supposed to find")
    print("    nothing; [3] cannot fail even for a broken system. Summing the three would produce")
    print("    a number that answers no question anybody has.\n")

    return 0 if ok else 1


def selftest():
    """Checks the BENCHMARK, not the retrieval. Its job is to refuse to flatter."""
    fails = []

    # ★★★ 1. A missing corpus must REFUSE, not score 0/10. Scoring zero on nothing looks like a
    #    measurement of the retrieval and is a measurement of the empty folder.
    tmp = tempfile.mkdtemp(prefix="bench_selftest_")
    try:
        run(os.path.join(tmp, "does-not-exist"), DEF_PROBES)
        fails.append("a missing corpus produced a score instead of refusing")
    except SystemExit:
        pass

    # ★★★ 2. THE PROBES MUST NOT REUSE THE ANSWER FILE'S WORDS. This is the property that makes the
    #    benchmark meaningful, and it is a property of the DATA, so nothing else can check it.
    #
    # ⚠ THIS LOOP USED TO BE HARDCODED TO THE DEFAULT PAIR, and that was a real defect: the moment a
    #   second corpus shipped, the suite validated one probe set and silently ignored the other —
    #   while still printing an unqualified PASS. A checker that covers a fixed subset of the data
    #   reports on the subset and is read as reporting on all of it. Iterate SHIPPED_PAIRS instead,
    #   so adding a corpus automatically adds its validation.
    for corpus, probes_path in SHIPPED_PAIRS:
        tag = os.path.basename(corpus)
        spec = json.load(io.open(probes_path, encoding="utf-8"))
        # ⚠ BOTH sections, deliberately. 'works' and 'boundary' are not two kinds of probe — they are
        #   one continuum, separated only by shared vocabulary. Reading one section would hide that,
        #   and would also leave half the probe set unvalidated while still printing PASS.
        for p in spec.get("works", []) + spec.get("boundary", []):
            path = os.path.join(corpus, p["expect"] + ".md")
            if not os.path.exists(path):
                fails.append("[%s] probe expects %r which is not in the corpus" % (tag, p["expect"]))
                continue
            qt = set(_recall.terms(p["q"]))
            title = set(_recall.terms(p["expect"].replace("-", " ")))
            overlap = qt & title
            if len(overlap) > 1:
                fails.append("[%s] probe %r shares %d words with its answer's FILENAME (%s) — it may "
                             "pass by string match rather than retrieval"
                             % (tag, p["q"][:40], len(overlap), overlap))

        # ★★★★ 3. THE SECTIONS MUST BE HONESTLY SORTED, and this is the guard that keeps the whole
        #    restructure from decaying back into the thing it replaced.
        #
        #    A zero-overlap question sitting in 'works' is a documented limit disguised as a defect:
        #    it drags the headline score down for a reason that has nothing to do with retrieval
        #    quality — precisely the failure that motivated splitting the file. And a probe in
        #    'boundary' that DOES share vocabulary is not a boundary case at all; it is an ordinary
        #    question parked where nobody scores it, which quietly hides a real regression.
        #
        #    Both directions are checked, because a category system polices nothing if membership is
        #    decided by whoever last edited the JSON.
        for p in spec.get("works", []):
            body = io.open(os.path.join(corpus, p["expect"] + ".md"),
                           encoding="utf-8", errors="replace").read()
            if not (set(_recall.terms(p["q"])) & set(_recall.terms(body))):
                fails.append("[%s] 'works' probe %r shares NO content word with its answer — that is "
                             "a BOUNDARY case, and scoring it makes the tool look broken when it is "
                             "behaving exactly as documented" % (tag, p["q"][:44]))

        for p in spec.get("boundary", []):
            body = io.open(os.path.join(corpus, p["expect"] + ".md"),
                           encoding="utf-8", errors="replace").read()
            shared = set(_recall.terms(p["q"])) & set(_recall.terms(body))
            if shared:
                fails.append("[%s] 'boundary' probe %r DOES share %s with its answer — it is an "
                             "ordinary question hiding in the unscored section, where a real "
                             "regression would go unnoticed" % (tag, p["q"][:44], sorted(shared)))

        # ★ 4. absent controls must genuinely be absent from THIS corpus. A control that is absent
        #   from one corpus and present in another is not a control for both.
        for q in spec.get("absent", []):
            if _recall.recall(q, [corpus], top=3):
                fails.append("[%s] 'absent' control %r matches the corpus — it is not a control"
                             % (tag, q))

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    for f in fails:
        print("   -", f)
    print("benchmark selftest:", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
