#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""memory_echo.py — before you write a NEW memory, look at what you already wrote.

    python memory_echo.py "the memory you are about to save"
    python memory_echo.py --selftest

WHY. The obvious failure of a memory system is forgetting. The one that actually happens is
**writing the same lesson again**, in slightly different words, for the thirtieth time — and feeling
insight while doing it. Duplicates are worse than useless: they dilute every future search, so the
corpus gets bigger and retrieval gets worse at exactly the same rate.

This does not stop you. It shows you the closest existing memories and lets you decide whether you
are adding a fact or re-learning one.

★★★★★ IT RANKS. IT DELIBERATELY DOES NOT GATE, AND THAT IS A MEASURED DECISION.

  The tempting design is a similarity threshold: "score above X, refuse the write." I measured that
  on a real corpus and it does not work. A lesson that genuinely echoed **29 existing files** scored
  **0.189**. An unrelated, genuinely-new fact scored **0.160**. There is no gap. Any threshold
  drawn between those two numbers is a coin toss wearing the costume of a rule — and it would be a
  coin toss with the authority to block a real memory.

  So: **rank, show the top few, and let the human or agent read them.** A ranking that is 60% useful
  is worth having. A gate that is 60% accurate is worse than nothing, because its refusals look
  principled.

  ⚠ A future maintainer WILL be tempted to add the threshold. The selftest asserts the no-gate
    property so that change fails loudly instead of quietly discarding somebody's memory.
"""
import argparse
import io
import os
import re
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
DEFAULT_ROOTS = [os.path.join(os.path.dirname(HERE), "memory")]


def _tokens(text):
    return set(_recall.terms(text or ""))


def similarity(draft, path):
    """Jaccard over meaningful tokens, weighted toward the description.

    Deliberately simple. A cleverer metric would still not separate the 0.189 echo from the 0.160
    non-echo — the corpus does not contain that separation, so no scorer can extract it. Complexity
    here would buy false confidence, not accuracy.
    """
    try:
        text = io.open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return 0.0
    fm, body = _recall.split_front(text)
    d = _tokens(draft)
    if not d:
        return 0.0
    body_t = _tokens(body)
    desc_t = _tokens(fm.get("description", "")) | _tokens(fm.get("name", "").replace("-", " "))
    both = body_t | desc_t
    if not both:
        return 0.0
    # ★★★★ BOUNDED TO [0,1] — found by external review, 2026-08-25.
    #   This was `(len(d & both) + len(d & desc_t)) / len(d | both)`: the description bonus went
    #   into the numerator alone, so a one-word draft against a one-word description scored
    #   **2.0**. Measured. A "similarity" above 1 is not a similarity, and every printed ranking
    #   built on it was quietly meaningless at the top end.
    #   ⚠ The docstring above already promised "Jaccard over meaningful tokens". It was not one.
    #     A comment describing what the code was supposed to do is not evidence that it does.
    base = len(d & both) / float(len(d | both))
    bonus = 0.25 * (len(d & desc_t) / float(len(d))) if d else 0.0   # description overlap, weighted
    return min(1.0, base + bonus)


def echoes(draft, roots=None, top=3):
    rows = []
    for path in _recall.walk(roots or DEFAULT_ROOTS):
        s = similarity(draft, path)
        if s > 0:
            rows.append((s, path))
    rows.sort(key=lambda r: (-r[0], r[1]))
    return rows[:top]


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
    ap = argparse.ArgumentParser(description="Show the closest existing memories before you write.")
    ap.add_argument("draft", nargs="*", help="the memory you are about to save")
    ap.add_argument("--root", action="append", default=None)
    ap.add_argument("--top", type=_pos_int, default=3)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    draft = " ".join(a.draft)
    if not draft.strip():
        ap.error("give me the draft memory")

    hits = echoes(draft, a.root, a.top)
    if not hits:
        print("  no overlap found with any existing memory.")
        print("  ⚠ That is NOT a clean bill of health — it means these words are new, which is a")
        print("    weaker statement than the idea being new. Open the top hits anyway if any exist.")
        return 0

    print("\n  closest %d existing memories — OPEN THEM BEFORE WRITING:\n" % len(hits))
    for s, path in hits:
        # ⚠ GUARDED: a memory can be deleted or mid-sync between ranking and display. similarity()
        #   already tolerates that; this reopen did not, so the command could crash AFTER doing all
        #   its work. Found by external review — and it is the same OSError case I had just guarded
        #   in recall.score_file, left unfixed in its sibling. The fix travels with the file, not
        #   with the lesson.
        try:
            fm, _ = _recall.split_front(io.open(path, encoding="utf-8", errors="replace").read())
        except OSError:
            print("    %.3f  %s  (unreadable now — deleted or syncing)" % (s, os.path.basename(path)))
            continue
        print("    %.3f  %s" % (s, os.path.basename(path)))
        if fm.get("description"):
            print("           %s" % fm["description"][:110])
    print("\n  ⚠ These scores RANK; they do not decide. On a real corpus a 29-fold echo scored 0.189")
    print("    and an unrelated new fact scored 0.160 — no threshold can separate them. Read the")
    print("    files; the number only chooses which three to put in front of you.\n")
    # ★ ALWAYS 0. This tool has no failing exit code ON PURPOSE — see selftest.
    return 0


def selftest():
    fails = []
    tmp = tempfile.mkdtemp(prefix="echo_selftest_")
    # ⚠ Cleaned up at the end. Before this, every --selftest run left a directory behind;
    #   15 had accumulated in the system temp dir before an external review pointed at it.
    #   A tool that litters while proving it is healthy is making a claim it undermines.

    def w(name, desc, body):
        io.open(os.path.join(tmp, name + ".md"), "w", encoding="utf-8").write(
            "---\nname: %s\ndescription: %s\nmetadata:\n  type: feedback\n---\n\n%s\n" % (name, desc, body))

    w("measure-before-optimising", "Guessing at the hot path wasted an afternoon",
      "I optimised the function I assumed was slow. Profiling showed the cost was elsewhere entirely.")
    w("unrelated-holiday-note", "The office is shut on the 3rd", "Nobody is in. Do not schedule the review.")

    roots = [tmp]

    # 1. a near-duplicate should rank above an unrelated file
    hits = echoes("I optimised the function I assumed was slow instead of profiling first", roots, top=2)
    if not hits:
        fails.append("no echo found for a draft that plainly restates an existing memory")
    elif os.path.basename(hits[0][1]) != "measure-before-optimising.md":
        fails.append("ranking failed: the unrelated note outranked the near-duplicate (top was %s)"
                     % os.path.basename(hits[0][1]))

    # 2. ★★★★★ THE NO-GATE PROPERTY. This is the assertion that protects a design decision, not a
    #    behaviour: main() must return 0 for BOTH a heavy echo and a novel draft. If a maintainer
    #    adds a threshold that blocks writes, this fails loudly instead of silently eating memories.
    #   (stdout is muted here only so `--selftest` output stays readable; the exit codes are the
    #    thing under test and they are captured, not suppressed.)
    _real = sys.stdout
    try:
        sys.stdout = io.StringIO()
        rc_echo = main(["--root", tmp, "I optimised the function I assumed was slow"])
        rc_new = main(["--root", tmp, "the widget calibration drifts in cold weather"])
    finally:
        sys.stdout = _real
    if rc_echo != 0 or rc_new != 0:
        fails.append("GATE DETECTED: exit codes were echo=%s new=%s. This tool must RANK and never "
                     "block — measured, a 29-fold echo scored 0.189 and an unrelated fact 0.160, so "
                     "any threshold is a coin toss with the power to discard a real memory."
                     % (rc_echo, rc_new))

    # 2b. ★★★★ SIMILARITY MUST BE IN [0,1]. It returned 2.0 for a one-word draft against a
    #     one-word description: the description bonus was added to the numerator alone.
    w("cache", "cache", "cache")
    sc = similarity("cache", os.path.join(tmp, "cache.md"))
    if not (0.0 <= sc <= 1.0):
        fails.append("similarity returned %.3f — outside [0,1], so it is not a similarity and every "
                     "ranking built on it is meaningless at the top end" % sc)

    # 3. ⚠ the honest-empty control: a draft sharing no vocabulary must return NOTHING, and the
    #    caller must not be able to read that as "this idea is new".
    if echoes("zzzq wgrbl fnord", roots, top=3):
        fails.append("returned echoes for a draft sharing no vocabulary with the corpus")

    # 4. an empty draft must not match everything
    if echoes("", roots, top=3):
        fails.append("an empty draft returned matches")

    for f in fails:
        print("   -", f)
    print("memory_echo selftest:", "PASS" if not fails else "FAIL")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
