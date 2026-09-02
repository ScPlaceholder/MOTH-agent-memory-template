"""rolling_context.py — carry state across a compaction without carrying the whole archive.

An agent's context window is compacted or discarded between sessions. Whatever was not written down
is gone, and the failure is silent: the next session simply does not know, and cannot tell that it
does not know. So each session writes a dated snapshot, and the next one reads back a small, bounded
number of the most recent ones.

    python rolling_context.py --write "current task; open questions; what I was about to do"
    python rolling_context.py --read              the last N snapshots, newest first
    python rolling_context.py --status            what exists, what would be read
    python rolling_context.py --prune             DRY RUN by default; --go to act

★★★★★ CAP THE READING, NOT THE ARCHIVE. THIS IS THE WHOLE DESIGN AND IT WAS LEARNED THE HARD WAY.

  The obvious implementation keeps the last three snapshots and deletes the rest — and it is wrong
  twice over.

  1. **The cap it enforces was already enforced somewhere better.** The reason to limit snapshots is
     that they are read at startup and too many would drown the load. But the reader takes only the
     newest few. **The load was never uncapped.** So the deletion achieves nothing the reader was not
     already achieving, while being the only operation in the system that destroys data.

  2. **A retention rule whose selector is "oldest" is only safe while the directory stays
     homogeneous, and nothing ever rechecks that.** In the system this was extracted from, a reading
     journal lived in the snapshot folder. Listed by date it was the fourth entry down. A
     delete-oldest rule would have destroyed it, correctly by its own logic, and the logic was never
     wrong — the assumption underneath it had quietly stopped being true.

  They are small text files. Disk is not the constraint and never was.

⚠ SO: `--prune` MATCHES A DATED NAME PATTERN, NEVER AN AGE RANK. It dry-runs by default, honours a
  `.keep` sidecar, and prints every file it is NOT touching — because the dangerous case is not
  deleting the wrong file, it is deleting the wrong file silently.
"""
import argparse
import os
import re
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

DEFAULT_DIR = os.environ.get("ROLLING_CONTEXT_DIR", "context_snapshots")
DEFAULT_TIERS = int(os.environ.get("ROLLING_CONTEXT_TIERS", "3"))

# ★ The ONLY thing --prune will ever consider. A file that does not match this is not a snapshot,
#   whatever else is true about it, and it is invisible to deletion by construction.
SNAPSHOT_RE = re.compile(r"^snapshot_(\d{4}-\d{2}-\d{2})(?:_(\d{2})(\d{2}))?\.md$")


def snapshots(dirpath=DEFAULT_DIR):
    """Every file that IS a snapshot, newest first. Non-matching files are not returned at all."""
    if not os.path.isdir(dirpath):
        return []
    out = []
    for fn in os.listdir(dirpath):
        if SNAPSHOT_RE.match(fn):
            out.append(os.path.join(dirpath, fn))
    return sorted(out, reverse=True)


def foreign(dirpath=DEFAULT_DIR):
    """Files in the snapshot directory that are NOT snapshots.

    ★ This function is the guard. The retention bug it prevents is not 'delete too many' but
    'the directory stopped being what the rule assumed'. Anything listed here is why --prune must
    never select by age."""
    if not os.path.isdir(dirpath):
        return []
    return sorted(os.path.join(dirpath, f) for f in os.listdir(dirpath)
                  if not SNAPSHOT_RE.match(f) and not f.startswith("."))


def write(text, dirpath=DEFAULT_DIR, now=None):
    now = now if now is not None else time.time()
    os.makedirs(dirpath, exist_ok=True)
    name = "snapshot_%s.md" % time.strftime("%Y-%m-%d_%H%M", time.localtime(now))
    p = os.path.join(dirpath, name)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write("# session snapshot %s\n\n%s\n"
                 % (time.strftime("%Y-%m-%d %H:%M", time.localtime(now)), text.strip()))
    return p


def read(dirpath=DEFAULT_DIR, tiers=DEFAULT_TIERS):
    """The last `tiers` snapshots, newest first, as (path, text).

    ⚠ Returns [] when the directory is missing OR empty, and the caller cannot distinguish those —
      so `main` reports them separately. An empty read presented as 'nothing happened last session'
      is exactly the silent failure this file exists to prevent."""
    picked = snapshots(dirpath)[:max(1, tiers)]
    out = []
    for p in picked:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                out.append((p, fh.read()))
        except OSError:
            continue
    return out


def prune_plan(dirpath=DEFAULT_DIR, keep=None):
    """What --prune WOULD delete, and everything it would not. Never touches anything itself.

    `keep` defaults generously: a snapshot is only ever a candidate if it matches the name pattern
    AND is outside the newest `keep`. A `<name>.keep` sidecar exempts a file permanently.
    """
    keep = DEFAULT_TIERS * 10 if keep is None else keep
    allsnaps = snapshots(dirpath)
    protected, candidates = allsnaps[:keep], allsnaps[keep:]
    kept_by_sidecar = [p for p in candidates if os.path.exists(p + ".keep")]
    delete = [p for p in candidates if p not in kept_by_sidecar]
    return {"delete": delete, "protected_recent": protected,
            "protected_sidecar": kept_by_sidecar, "not_snapshots": foreign(dirpath)}


def selftest():
    import shutil
    import tempfile
    fails = []
    d = tempfile.mkdtemp(prefix="_rc_")
    try:
        # a normal run of snapshots, plus ONE file that is not a snapshot and sorts in the middle
        for day in range(1, 8):
            with open(os.path.join(d, "snapshot_2026-08-%02d.md" % day), "w", encoding="utf-8") as fh:
                fh.write("day %d" % day)
        journal = os.path.join(d, "reading_journal_james_principles.md")
        with open(journal, "w", encoding="utf-8") as fh:
            fh.write("not a snapshot")

        # (1) reading is bounded and newest-first
        got = read(d, tiers=3)
        if len(got) != 3:
            fails.append("read() must return exactly the tier count, got %d" % len(got))
        if got and not got[0][0].endswith("2026-08-07.md"):
            fails.append("read() must be newest-first, got %s" % (got[0][0] if got else None))

        # (2) ★★ THE LOAD-BEARING TEST: the non-snapshot must be invisible to every delete path,
        #     at ANY retention setting, including one that would delete almost everything.
        for keep in (0, 1, 2, 3, 6):
            plan = prune_plan(d, keep=keep)
            if journal in plan["delete"]:
                fails.append("★★ prune would delete a NON-SNAPSHOT (%s) at keep=%d — an age-ranked "
                             "selector in a directory that is no longer homogeneous" % (journal, keep))
            if any(not SNAPSHOT_RE.match(os.path.basename(p)) for p in plan["delete"]):
                fails.append("prune selected a file that does not match the snapshot pattern")

        # (3) prune must SURFACE the foreign file rather than ignoring it silently
        if journal not in prune_plan(d, keep=2)["not_snapshots"]:
            fails.append("prune must report non-snapshots it found; silence is how the assumption "
                         "stops being rechecked")

        # (4) a .keep sidecar protects a file that would otherwise be a candidate
        target = os.path.join(d, "snapshot_2026-08-01.md")
        with open(target + ".keep", "w", encoding="utf-8") as fh:
            fh.write("")
        plan = prune_plan(d, keep=2)
        if target in plan["delete"]:
            fails.append("a .keep sidecar did not protect its file")
        if target not in plan["protected_sidecar"]:
            fails.append("a .keep-protected file must be reported as protected, not merely omitted")

        # (5) an empty or missing directory must not look like a successful read
        if read(os.path.join(d, "nope")) != []:
            fails.append("a missing directory must return no snapshots")

        # (6) writing then reading round-trips
        d2 = tempfile.mkdtemp(prefix="_rc2_")
        write("the thing I was about to do", dirpath=d2)
        if not read(d2, tiers=1) or "about to do" not in read(d2, tiers=1)[0][1]:
            fails.append("write/read round-trip lost the content")
        shutil.rmtree(d2, ignore_errors=True)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    for f in fails:
        print("  [FAIL] %s" % f)
    if not fails:
        print("  [PASS] reading is bounded and newest-first, a NON-SNAPSHOT is undeletable at every "
              "retention setting and is reported, .keep protects, a missing dir returns nothing.")
    print("\n  rolling_context selftest:", "PASS" if not fails else "FAIL")
    print("== rolling_context COMPLETE (rc=%d) ==" % (0 if not fails else 2))
    return 0 if not fails else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description="Bounded session-to-session context.")
    ap.add_argument("--dir", default=DEFAULT_DIR)
    ap.add_argument("--tiers", type=int, default=DEFAULT_TIERS)
    ap.add_argument("--write", metavar="TEXT")
    ap.add_argument("--read", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--prune", action="store_true")
    ap.add_argument("--keep", type=int, default=None)
    ap.add_argument("--go", action="store_true", help="actually delete (default is a dry run)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)

    if a.selftest:
        return selftest()
    if a.write:
        print("wrote", write(a.write, dirpath=a.dir))
        return 0
    if a.prune:
        plan = prune_plan(a.dir, keep=a.keep)
        print("prune plan for %s  (DRY RUN — pass --go to act)" % a.dir)
        print("  would delete        : %d" % len(plan["delete"]))
        for p in plan["delete"]:
            print("      -", os.path.basename(p))
        print("  keeping (recent)    : %d" % len(plan["protected_recent"]))
        print("  keeping (.keep)     : %d" % len(plan["protected_sidecar"]))
        # ⚠ printed even when empty: 'no foreign files' is a finding, and an absent line reads as
        #   'not checked'.
        print("  NOT SNAPSHOTS, never considered for deletion: %d" % len(plan["not_snapshots"]))
        for p in plan["not_snapshots"]:
            print("      ·", os.path.basename(p))
        if a.go:
            for p in plan["delete"]:
                os.remove(p)
            print("  deleted %d" % len(plan["delete"]))
        return 0

    rows = read(a.dir, tiers=a.tiers)
    if a.status or not a.read:
        allsnaps = snapshots(a.dir)
        print("rolling_context: %s" % a.dir)
        if not os.path.isdir(a.dir):
            print("  ⚠ DIRECTORY DOES NOT EXIST — this is cannot-tell, not 'no prior sessions'.")
            return 3
        print("  %d snapshot(s) on disk, %d would be read (tiers=%d)"
              % (len(allsnaps), len(rows), a.tiers))
        f = foreign(a.dir)
        if f:
            print("  ⚠ %d non-snapshot file(s) live here and are excluded from pruning by pattern:" % len(f))
            for p in f:
                print("      ·", os.path.basename(p))
        return 0
    if not rows:
        print("⚠ no snapshots read. The directory exists and is empty — that is different from a "
              "session with nothing to carry, and neither is a reason to proceed as if fresh.")
        return 3
    for p, text in rows:
        print("=" * 72)
        print("# %s" % os.path.basename(p))
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
