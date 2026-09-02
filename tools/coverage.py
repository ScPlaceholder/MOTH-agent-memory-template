#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""coverage.py — does every box of the reference architecture have a home in this repo?

    python coverage.py            # report
    python coverage.py --selftest # check the checker

★★★★★ WHY THIS IS A TEST AND NOT A CHECKLIST.

A checklist is a thing you TICK. A test is a thing that FAILS. Same information, completely
different behaviour — and the difference decides whether anyone ever finds out.

This exists because the coverage gaps in this repo were found by hand, with `grep`, and only
because somebody asked. Three boxes of the reference architecture had no home anywhere:
the sparse-expansion engine was mentioned once inside a *warning* and never given a build stage;
the two-layer boot design was absent entirely; the memory lifecycle was absent entirely. Every one
of them was invisible to every existing check, because nothing was looking.

⚠ WHAT THIS CANNOT DO, said up front so the green does not overclaim. It checks that each box is
  *addressed somewhere* — implemented, or specified with an acceptance test. **It cannot judge
  whether the treatment is any good.** A box marked SPEC has a prompt and a pass condition; it does
  not have working code, and this tool will never tell you otherwise. Read the STATUS column.
"""
import argparse
import io
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Every box of the reference architecture, with the evidence that it is addressed.
#   kind: CODE = shipped and running here.  SPEC = a build stage with an acceptance test.
#         PROMPT = agent behaviour, lives in the system prompt (no module to install).
#   needle: a regex that must appear in `where`. Deliberately a property of the FILE, so deleting
#           the section breaks the test — the point is that removal is loud.
BOXES = [
    ("1  two-layer: always-loaded core + on-demand streaming", "PROMPT",
     "docs/AGENT_INSTRUCTIONS.md", r"STREAMS ON DEMAND"),
    ("2  corpus content / index records", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 1 .*persistent index"),
    ("3  chunking at natural boundaries", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 2 .*Chunking"),
    ("4a engine: keyword (coverage-first)", "CODE",
     "tools/recall.py", r"BODY_CAP"),
    ("4b engine: keyize (query reduction)", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 3 .*Keyize"),
    ("4c engine: SPLADE (sparse expansion)", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 6 .*SPLADE"),
    ("4d engine: embeddings (dense semantic)", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 7 .*Embeddings"),
    ("4e engine: cross-encoder rerank", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 8 .*Cross-encoder"),
    ("5  per-engine query representation", "SPEC",
     "docs/BUILD_PROMPTS.md", r"expand the query the same way"),
    ("6  fusion & ranking (RRF)", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 4 .*Fusion"),
    ("6b ranking rules (coverage-first, body cap, short beats long)", "CODE",
     "docs/FORMAT.md", r"short precise notes outrank long journals"),
    ("7  end-to-end retrieval pipeline ordering", "SPEC",
     "docs/BUILD_PROMPTS.md", r"## Why this order"),
    ("7b fuzzy topic fallback (last resort)", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 9 .*Fuzzy topic fallback"),
    ("8  indexing & freshness (atomic, staleness)", "SPEC",
     "docs/BUILD_PROMPTS.md", r"Write the index atomically"),
    ("9  three query outcomes + confidence gate", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 5 .*three-outcome gate"),
    ("9b what the agent DOES with each outcome", "PROMPT",
     "docs/AGENT_INSTRUCTIONS.md", r"three outcomes and they are not the same"),
    ("10 lifecycle: reinforce / supersede / archive", "SPEC",
     "docs/BUILD_PROMPTS.md", r"# Stage 10 .*Lifecycle"),
    # ★ ADDED 2026-08-29, AND THE OMISSION IS THE POINT. The write side existed as a capability for
    #   hours before it existed as a BOX, so `coverage.py` reported "every box is addressed" while a
    #   whole half of the architecture sat outside its census. A list-walking audit cannot report the
    #   entry nobody added — the same defect this repo documents about stale counts, one level up.
    #   The lesson is not "remember to add boxes". It is that ANY completeness claim is bounded by a
    #   list somebody hand-maintains, so the claim must name its list: this says 'every box in BOXES',
    #   never 'every box'.
    ("11 write side: candidate queue (capture, retrieval-feedback, no auto-promotion)", "CODE",
     "tools/memory_candidates.py", r"def capture\("),
    ("11b write side: classifier filling the queue — MEASURED WEAK", "CODE",
     "tools/candidate_classify.py", r"def classify\("),
    # ★ ADDED 2026-09-02, and the census caught them before I did. Both were written that
    #   afternoon, both selftested, and `wired.py` reported NOT WIRED IN for each — no importer, no
    #   caller, no box. I had already told the designer "both gaps are closed", which was true of
    #   the FILES and false of the SYSTEM. Adding the box is what makes their absence loud later.
    ("12 dual librarian: guidance vs archive staleness, measured against the SOURCE", "CODE",
     "tools/librarians.py", r"def archive_status\("),
    ("13 multi-tier rolling context (cap the READING, never prune by age)", "CODE",
     "tools/rolling_context.py", r"def prune_plan\("),
    ("--  benchmark that can actually fail", "CODE",
     "tools/benchmark.py", r"def verify\("),
    ("--  acceptance check the USER runs", "CODE",
     "docs/BUILD_PROMPTS.md", r"acceptance check you run yourself"),
]


def audit():
    rows = []
    for name, kind, where, needle in BOXES:
        path = os.path.join(ROOT, where)
        try:
            text = io.open(path, encoding="utf-8", errors="replace").read()
        except IOError:
            rows.append((name, kind, where, "FILE MISSING"))
            continue
        ok = re.search(needle, text) is not None
        rows.append((name, kind, where, "ok" if ok else "NOT FOUND"))
    return rows


def main(argv):
    ap = argparse.ArgumentParser(description="Is every architecture box addressed somewhere?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    rows = audit()
    bad = [r for r in rows if r[3] != "ok"]
    print("\n  ARCHITECTURE COVERAGE — %d boxes\n" % len(rows))
    for name, kind, where, status in rows:
        mark = "  " if status == "ok" else "✗ "
        print("  %s%-6s %-58s %s" % (mark, kind, name[:58], where if status == "ok" else status))
    n_code = sum(1 for r in rows if r[1] == "CODE")
    n_spec = sum(1 for r in rows if r[1] == "SPEC")
    n_pr = sum(1 for r in rows if r[1] == "PROMPT")
    print("\n  CODE %d (shipped and running)   SPEC %d (build stage + acceptance test)   "
          "PROMPT %d (system prompt)" % (n_code, n_spec, n_pr))
    if bad:
        print("\n  ✗ %d BOX(ES) WITH NO HOME:" % len(bad))
        for name, _k, where, status in bad:
            print("      %-58s expected in %s (%s)" % (name[:58], where, status))
        print("\n  A box nobody has addressed is invisible to every other check in this repo.")
        return 1
    # ⚠ THE CLAIM NAMES ITS LIST, AND THAT IS THE WHOLE FIX. This read "Every box is addressed"
    #   until 2026-08-29, when a write-side capability shipped and sat OUTSIDE `BOXES` for hours
    #   while this line certified completeness over it. An audit that walks a hand-maintained list
    #   can only ever report on that list. Saying so converts a false universal into a true bounded
    #   claim and costs nothing — and it is the same defect this repo already documents about stale
    #   counts in prose, one level up: the count cannot see what nobody added to the thing it counts.
    print("\n  ✓ Every box in BOXES (%d) is addressed." % len(BOXES))
    print("    ⚠ That is coverage OF THIS LIST, not of the architecture. A capability nobody added"
          "\n      here is invisible to this check — which happened, to this file, on 2026-08-29.")
    print("  ⚠ ADDRESSED IS NOT IMPLEMENTED. Only the %d CODE rows ship working code; the %d SPEC" % (n_code, n_spec))
    print("    rows are build instructions with acceptance tests, and nothing here judges whether")
    print("    a treatment is any GOOD — only that it exists.\n")
    return 0


def selftest():
    """Check the checker. A coverage tool that cannot report a gap is worse than none."""
    fails = []
    rows = audit()

    # 1. the live repo must currently be clean
    if [r for r in rows if r[3] != "ok"]:
        fails.append("live repo has uncovered boxes (that may be a REAL finding, not a test failure)")

    # 2. ★ IT MUST BE ABLE TO GO RED. Point one box at a needle that cannot exist and confirm
    #    the audit reports it. Without this, "every box is addressed" is unfalsifiable.
    global BOXES
    saved = BOXES
    try:
        BOXES = saved[:1] + [("synthetic gap", "SPEC", "docs/BUILD_PROMPTS.md",
                              r"zzz_this_string_does_not_exist_zzz")]
        if not [r for r in audit() if r[3] != "ok"]:
            fails.append("a box with an impossible needle was still reported as covered")
    finally:
        BOXES = saved

    # 3. a missing FILE must be reported, not crash
    BOXES2 = [("synthetic missing file", "SPEC", "docs/no_such_file.md", r"anything")]
    saved = BOXES
    try:
        BOXES = BOXES2
        r = audit()
        if r[0][3] != "FILE MISSING":
            fails.append("a missing file was not reported as FILE MISSING")
    finally:
        BOXES = saved

    for f in fails:
        print("   -", f)
    print("coverage selftest:", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
