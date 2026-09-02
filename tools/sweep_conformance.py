#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sweep_conformance.py — prove the two sweep arms agree, on a corpus that CAN disagree.

    python tools/sweep_conformance.py                 # needs the Rust binary built
    python tools/sweep_conformance.py --selftest

★★★★★ WHY THIS EXISTS, AND IT IS THE WHOLE LESSON.

`wide_sweep.py` and `rust_sweep/` claim in both their headers to be pinned to identical semantics.
That claim was first "verified" by running ONE query against the repository's `sample/` corpus and
observing byte-identical output. It passed. It was also worthless, because that corpus contains:

    no ties               so the final path tie-break was never exercised
    no generated files    so the authored-above-generated sort key was never exercised
    no symlinks           so the directory-walk divergence was invisible
    nothing outside cp1252 so the console crash could not fire

**Every dimension on which the two arms actually differed was absent from the test.** An independent
review then found four result-changing divergences and a crash. A check that cannot come back
negative is not evidence of agreement; it is evidence of nothing, and it is more dangerous than no
check at all because it is quoted afterwards as though it were a measurement.

⚠ SO THE FIXTURE IS THE POINT, not this runner. `_sweep_conformance/` is built to contain exactly
  the cases that separated the arms. If you add a rule to either implementation, add a fixture that
  would catch it diverging — otherwise this file becomes the same rubber stamp its predecessor was.

⚠ AND IT COMPARES THE FULL ORDERED LIST, not the headline count. Two of the real divergences
  produced the SAME match count with a different document dropped, or the same count with different
  hit totals underneath. Comparing "2 matched" to "2 matched" would have passed all of them.
"""

import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS = os.path.join(HERE, "_sweep_conformance")
RUST = os.path.join(HERE, "rust_sweep", "target", "release",
                    "rust_sweep.exe" if os.name == "nt" else "rust_sweep")

# (label, terms, limit) — each row exists because it caught a real divergence.
CASES = [
    ("ties: 10 identical files, limit 8 drops a different one in each arm", ["badger"], 8),
    ("generated: sidecar + name patterns must sort below authored", ["badger"], 20),
    ("non-cp1252: a corpus containing warning glyphs must not kill the printer", ["badger"], 20),
    ("AND across two terms", ["badger", "café"], 20),
    ("absent term must return nothing in both", ["wombat"], 20),
]


def run_py(terms, limit):
    p = subprocess.run([sys.executable, os.path.join(HERE, "wide_sweep.py"),
                        "--roots", CORPUS, "--limit", str(limit), "--"] + terms,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout, p.returncode


def run_rs(terms, limit):
    p = subprocess.run([RUST, "--roots", CORPUS, "--limit", str(limit), "--"] + terms,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.stdout, p.returncode


def parse(out):
    """(matched, [(generated, hits, basename), ...]) — the ORDERED list, not just the count."""
    m = re.search(r"(\d+)\s+matched", out)
    matched = int(m.group(1)) if m else None
    rows = []
    for line in out.splitlines():
        r = re.search(r"(\[gen\]|\s{5})\s*x(\d+)\s+d(\d+)\s+(.+?)\s*$", line)
        if r:
            rows.append((r.group(1).strip() == "[gen]", int(r.group(2)), os.path.basename(r.group(4))))
    return matched, rows


def compare(verbose=True):
    fails = []
    if not os.path.isdir(CORPUS):
        return ["conformance corpus missing: %s" % CORPUS]
    if not os.path.exists(RUST):
        # ⚠ AN UNBUILT BINARY IS 'CANNOT TELL', NEVER 'AGREES'. Returning pass here would restore
        #   the exact failure this file was written to end.
        return ["rust binary not built (%s) — CANNOT TELL, not agreement. "
                "cd tools/rust_sweep && cargo build --release" % RUST]
    for label, terms, limit in CASES:
        po, prc = run_py(terms, limit)
        ro, rrc = run_rs(terms, limit)
        pm, pr = parse(po)
        rm, rr = parse(ro)
        if pm != rm:
            fails.append("%s: matched %r vs %r" % (label, pm, rm))
        if pr != rr:
            fails.append("%s: ORDERED RESULTS DIFFER\n      py: %r\n      rs: %r" % (label, pr, rr))
        if prc != rrc:
            fails.append("%s: exit code %d vs %d" % (label, prc, rrc))
        if verbose and not fails:
            print("  [ok] %-64s %s matched" % (label[:64], pm))
    return fails


def selftest():
    """★ The runner's own teeth: it must FAIL when handed differing output, or it proves nothing."""
    fails = []
    a = parse("  wide_sweep: 2 matched (2 shown)\n       x5    d10   x\\a.md\n       x5    d10   x\\b.md\n")
    b = parse("  rust_sweep: 2 matched (2 shown)\n       x5    d10   x\\b.md\n       x5    d10   x\\a.md\n")
    if a[0] != b[0]:
        fails.append("counts should tie in this fixture")
    if a[1] == b[1]:
        fails.append("REORDERED results compared equal — the comparison is count-only, which is "
                     "exactly the blindness that let the tie-break divergence ship")
    g = parse("       [gen] x1    d1    y\\corpus_index.md\n")
    if not g[1] or g[1][0][0] is not True:
        fails.append("the [gen] marker is not parsed, so the generated sort key is untested")
    for f in fails:
        print("  [FAIL] %s" % f)
    if not fails:
        print("  [PASS] the comparison is order-sensitive and reads the [gen] marker")
    print("\n  sweep_conformance selftest:", "PASS" if not fails else "FAIL")
    print("== sweep_conformance COMPLETE (rc=%d) ==" % (0 if not fails else 2))
    return 0 if not fails else 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    f = compare()
    for x in f:
        print("  [DIVERGENCE] %s" % x)
    print("\n  sweep conformance:", "AGREE" if not f else "DIVERGE (%d)" % len(f))
    print("== sweep_conformance COMPLETE (rc=%d) ==" % (0 if not f else 2))
    sys.exit(0 if not f else 2)
