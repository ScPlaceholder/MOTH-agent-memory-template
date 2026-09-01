"""downstream_of.py — when a measurement turns out to be wrong, what did you already build on it?

    python tools/downstream_of.py results.jsonl
    python tools/downstream_of.py --selftest

★★★★★ WHY. You run an experiment, publish the number, and later prove the number was wrong. You then
  fix the cause, write it up carefully, and move on — while the REPORT built on that number is still
  sitting in someone's inbox, unretracted. Fixing the cause and undoing the damage are two different
  jobs, and only the first one feels like work.

  The motivating case: a benchmark arm was proved degraded, the finding was written up properly, and
  a grading sheet generated FROM that arm had already been sent to a colleague asking them to spend
  an evening judging it. The finding was audited. What the finding INVALIDATED was not.

★★★ WHAT IT ANSWERS. Given a file whose contents are now suspect, list every artifact that (a) was
  written AFTER it and (b) mentions it or was produced alongside it. That is a mechanical question
  about mtimes and references — the kind humans are reliably bad at answering from memory and a
  filesystem answers in a second.

⚠⚠ DELIBERATELY OVER-INCLUSIVE. A false positive costs ten seconds of reading; a false negative is
  the failure this exists to prevent. When the two error costs are that lopsided, tune all the way
  toward noise. It also catches artifacts that never NAME their source — a generated report often
  records its inputs only inside the generator, so a pure reference search misses the one file that
  matters. Same-working-window proximity is the fallback, and it is noisy on purpose.

⚠ MTIME IS THE RIGHT INSTRUMENT FOR THIS ONE QUESTION AND THE WRONG ONE FOR ITS NEIGHBOUR.
  mtime means LAST TOUCHED. It cannot tell you when work "landed" — a file edited twice reports only
  the second edit. But *"was this written after that?"* is literally what mtime means. Name the
  question the instrument actually answers before you quote its value.

⚠⚠⚠ IT REPORTS. It never deletes, never edits, never "cleans up". An artifact built on a bad number
   is evidence of what was believed and when, and destroying it destroys the trail.
"""

import argparse
import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SCAN_EXT = (".md", ".json", ".jsonl", ".txt", ".py")
WINDOW_S = 3600          # "written in the same working session as" — noisy on purpose


def derived_from(target, dirs=None, exts=None, window_s=WINDOW_S):
    """[(path, mtime, why)] for artifacts written after `target` that reference it.

    `why` names WHICH signal fired, so a reader can judge each hit instead of trusting the list.
    Returns None if the target cannot be read — 'cannot tell' must never render as 'nothing found'.
    """
    t = os.path.abspath(target)
    try:
        t_mtime = os.path.getmtime(t)
    except OSError:
        return None
    stem = os.path.basename(t)
    bare = os.path.splitext(stem)[0]
    out = []
    for d in (dirs or [ROOT, HERE]):
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            p = os.path.join(d, name)
            if os.path.abspath(p) == t or not os.path.isfile(p):
                continue
            if not name.lower().endswith(exts or SCAN_EXT):
                continue
            try:
                mt = os.path.getmtime(p)
            except OSError:
                continue
            if mt <= t_mtime:
                continue                  # written BEFORE it: cannot be derived from it
            why = []
            try:
                head = io.open(p, encoding="utf-8", errors="replace").read(200000)
            except OSError:
                head = ""
            if stem in head or bare in head:
                why.append("mentions %s" % stem)
            if mt - t_mtime < window_s and not why:
                why.append("written within the same working window")
            if why:
                out.append((p, mt, "; ".join(why)))
    return sorted(out, key=lambda x: -x[1])


def selftest():
    ok = True
    import tempfile
    import glob
    d = tempfile.mkdtemp(prefix="_dso_")
    try:
        base = time.time() - 10000
        target = os.path.join(d, "result.jsonl")
        io.open(target, "w", encoding="utf-8").write("x")
        os.utime(target, (base, base))

        after_ref = os.path.join(d, "report.md")
        io.open(after_ref, "w", encoding="utf-8").write("built from result.jsonl\n")
        os.utime(after_ref, (base + 60, base + 60))

        before = os.path.join(d, "old.md")
        io.open(before, "w", encoding="utf-8").write("mentions result.jsonl too\n")
        os.utime(before, (base - 60, base - 60))

        far_after = os.path.join(d, "unrelated.md")
        io.open(far_after, "w", encoding="utf-8").write("nothing to do with it\n")
        os.utime(far_after, (base + 99999, base + 99999))

        names = [os.path.basename(p) for p, _m, _w in derived_from(target, dirs=[d])]

        # (1) a later artifact that names the target is reported
        if "report.md" not in names:
            print("  [FAIL] a later file naming the target was not reported"); ok = False
        else:
            print("  [PASS] later artifact referencing the target is reported")

        # (2) ★★ THE MIRROR. Something written BEFORE cannot derive from it, and reporting it would
        #     make the whole list untrustworthy — the value is that every row deserves a look.
        if "old.md" in names:
            print("  [FAIL] a file written BEFORE the target was reported as derived"); ok = False
        else:
            print("  [PASS] earlier files excluded (cannot derive from a later file)")

        # (3) an unrelated far-later file is not swept in by the time window alone
        if "unrelated.md" in names:
            print("  [FAIL] an unrelated far-later file was reported"); ok = False
        else:
            print("  [PASS] unrelated far-later files are not swept in")

        # (4) ★ THE CASE THIS EXISTS FOR. A generated report often records its inputs only inside the
        #     GENERATOR, so it never names its own source. Proximity must still catch it.
        quiet = os.path.join(d, "sheet.md")
        io.open(quiet, "w", encoding="utf-8").write("no mention of the source anywhere\n")
        os.utime(quiet, (base + 120, base + 120))
        names2 = [os.path.basename(p) for p, _m, _w in derived_from(target, dirs=[d])]
        if "sheet.md" not in names2:
            print("  [FAIL] a same-window artifact that does NOT name its source was missed — that "
                  "is exactly the case this tool exists for"); ok = False
        else:
            print("  [PASS] same-window artifacts caught without a textual reference")

        # (5) a missing target returns None, never an empty list that reads as "nothing downstream"
        if derived_from(os.path.join(d, "nope.jsonl"), dirs=[d]) is not None:
            print("  [FAIL] a missing target returned a list — 'cannot tell' must not look like "
                  "'nothing found'"); ok = False
        else:
            print("  [PASS] a missing target returns None, distinguishable from an empty result")
    finally:
        import glob as _g
        for f in _g.glob(os.path.join(d, "*")):
            try:
                os.remove(f)
            except OSError:
                pass
        try:
            os.rmdir(d)
        except OSError:
            pass

    print("\n  downstream_of selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.target:
        ap.print_help(); sys.exit(0)

    hits = derived_from(a.target)
    if hits is None:
        print("  ? cannot read %s — this is 'cannot tell', not 'nothing downstream'" % a.target)
        sys.exit(1)
    print("\n  BUILT ON %s (or written right after it):" % os.path.basename(a.target))
    if not hits:
        print("    nothing found in the scanned directories")
        sys.exit(0)
    for p, mt, why in hits:
        print("    %s  %-38s %s" % (time.strftime("%d %b %H:%M", time.localtime(mt)),
                                    os.path.basename(p), why))
    print("\n  %d artifact(s). Over-inclusive ON PURPOSE — a false positive costs ten seconds;"
          % len(hits))
    print("  a false negative is a report built on a bad number, still sitting in someone's inbox.")
    sys.exit(2)
