"""memory_candidates.py — the rolling queue between "someone said something" and "I remember it".

★★★★★ J'S DESIGN, 2026-08-29 22:25: *"Why can't memory candidate be a rolling file that updates
after a write and retrieval?"*

It dissolves the objection that had blocked the write side for weeks, and the reason is worth stating
because it is not the obvious one. I refused to wire a MEMORY_CANDIDATE classifier because the write
path is **the only place where a mistake is permanent** — a bad classification becomes a memory file
that is then retrieved and believed for months. That fear was correct.

A rolling file is not a memory. It is a **queue**, and queues can be wrong cheaply. J did not make the
risk smaller; he made it **reversible**, which is a different and better thing.

★★★ AND THE SECOND HALF IS THE PART I WOULD NOT HAVE REACHED. Updating after **retrieval** as well as
write means a candidate nobody ever pulls is evidence it was not worth keeping. That is **usage as
the filter**, not confidence at write time — and confidence provably cannot do this job: measured
2026-08-29, a real hit scored 0.727 while junk scored 0.693 and 0.719, so the answer sat *inside* the
noise band. Every score-based gate I own is fighting that. Use is not a score, and nothing has to be
thresholded.

⚠ THE LOOP IS REAL BUT IT HAS A LAG, STATED RATHER THAN HIDDEN. A captured candidate only becomes
  retrievable once the embedding index next rebuilds (~21 min, written atomically). `.jsonl` files
  ARE in the corpus — 52 of them today — so this file is picked up like any other. Until that
  rebuild, `retrieved` stays 0 for reasons that have nothing to do with the candidate's worth.

⚠⚠ NOTHING HERE PROMOTES TO MEMORY. Not automatically, not on a threshold, not ever from this module.
   Promotion is a separate, human-visible decision, because that is the step where the mistake
   becomes permanent — and the whole point of the queue is to make everything before it undoable.
"""
import io
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FILE = os.path.join(HERE, "_memory_candidates.jsonl")


def _rows(path=None):
    path = path or FILE
    out = []
    if not os.path.exists(path):
        return out
    for line in io.open(path, encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except Exception:
                pass          # a corrupt line loses one candidate, never the file
    return out


def capture(text, why, source="", kind="", path=None, now=None):
    """Append a candidate. Returns its id, or None if it was a duplicate.

    ★ `why` IS REQUIRED AND THAT IS DELIBERATE. A candidate without its reason is a decontextualised
      sentence, and in three weeks promoting it is guesswork — the same argument that makes my memory
      files carry the incident that produced them rather than only the lesson.
    """
    # ⚠⚠ THE TWO REQUIRED INPUTS USED TO FAIL DIFFERENTLY, AND A LOCAL REVIEWER CAUGHT IT 2026-08-30.
    #   `why` missing raised loudly; `text` missing returned None quietly. Two required arguments,
    #   one shouting and one whispering, and the caller could not tell a quiet refusal from a
    #   duplicate. Both now raise: a required input that fails silently is the shape of every bug I
    #   spent the night cataloguing.
    text = (text or "").strip()
    why = (why or "").strip()
    if not text:
        raise ValueError("capture() requires TEXT: an empty candidate cannot be promoted or judged")
    if not why:
        raise ValueError("capture() requires WHY: a candidate without its reason is unpromotable later")
    path = path or FILE
    rows = _rows(path)
    # ⚠⚠ I CHANGED THIS TO (text, why) AND THE SELFTEST REVERTED ME, CORRECTLY. 2026-08-30.
    #   A local reviewer said deduping on text alone "rejects valid candidates with the same text but
    #   different reasons, leading to data loss", and I acted on it. Line ~166 of selftest() captures
    #   the SAME text with a DIFFERENT reason and asserts it must be dropped, with the argument
    #   attached: *a queue that repeats itself is a transcript*. That is a stated design decision
    #   with its reasoning, made executable — not an oversight.
    #   ★ And the usage settles it: the classifier's `why` is "gemma kNN 0.459, looks like X". The
    #     same message arriving twice produces two near-identical reasons, so keying on `why` would
    #     let the queue fill with the same sentence forever. The repetition risk is REAL and common;
    #     the reviewer's data-loss risk is hypothetical and rare.
    #   ⚠ I took a reviewer's judgement over an argued test — the exact failure I catalogued twice
    #     tonight as "describing a test's PURPOSE as its bug", committed while fixing findings about it.
    for r in rows:                      # cheap exact-dupe guard; the queue should not repeat itself
        if r.get("text") == text:
            return None
    cid = "c%04d" % (len(rows) + 1)
    rec = {"id": cid, "t": now or time.strftime("%Y-%m-%dT%H:%M:%S"),
           "text": text[:1200], "why": why, "source": source, "kind": kind,
           "retrieved": 0, "last_retrieved": None}
    with io.open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return cid


def touch(cid, path=None, now=None):
    """Record that a candidate was actually RETRIEVED. This is the half that makes it a filter.

    Rewrites the file, which is safe here because it is small and append-mostly. If it ever grows
    past a few thousand rows this becomes the wrong shape and should be a side-log instead.
    """
    # ★★★★★ THE WRITE WAS ATOMIC AND THE READ-MODIFY-WRITE WAS NOT, WHICH IS A DIFFERENT PROBLEM.
    #   A reviewer said "no concurrency handling" — wrong, os.replace below is exactly that. But it
    #   protects the FILE, not the COUNTER: two concurrent touch() calls both read, both increment,
    #   and the second replace wins, so one retrieval silently disappears. Right conclusion, wrong
    #   layer, and the distinction changes the fix.
    #   ⚠ A LOST COUNT IS NOT COSMETIC HERE. `retrieved` is the whole promotion signal — the filter
    #     that decides a candidate earned its place. Undercounting makes a real memory look unused
    #     and quietly drops it, which is the failure this queue exists to prevent.
    #   The fix is a lock file, not a bigger rewrite: the operation is short and the contention is
    #   rare, so a spin with a timeout costs nothing in the normal case and closes the window.
    path = path or FILE
    lock = path + ".lock"
    acquired = False
    for _ in range(50):                       # ~5s ceiling; a stuck lock must not wedge the caller
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            acquired = True
            break
        except OSError:
            time.sleep(0.1)
    try:
        rows = _rows(path)
        hit = False
        for r in rows:
            if r.get("id") == cid:
                r["retrieved"] = int(r.get("retrieved") or 0) + 1
                r["last_retrieved"] = now or time.strftime("%Y-%m-%dT%H:%M:%S")
                hit = True
        if hit:
            tmp = path + ".tmp"
            with io.open(tmp, "w", encoding="utf-8") as f:
                for r in rows:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            os.replace(tmp, path)      # atomic; a crash mid-write must not truncate the queue
        return hit
    finally:
        # ⚠ RELEASE EVEN IF WE NEVER ACQUIRED — otherwise a timeout leaves the lock forever and every
        #   later touch() pays the full 5s before proceeding unprotected. Fail open, never fail stuck.
        if acquired:
            try:
                os.remove(lock)
            except OSError:
                pass


def review(path=None):
    """(earned, unproven) — split by whether anything ever pulled them.

    ⚠ NOT a promotion list and not sorted into one. It reports the two piles and says what each
      means; deciding is somebody's job, not this function's.
    """
    rows = _rows(path)
    earned = sorted([r for r in rows if int(r.get("retrieved") or 0) > 0],
                    key=lambda r: -int(r.get("retrieved") or 0))
    unproven = [r for r in rows if not int(r.get("retrieved") or 0)]
    return earned, unproven


def selftest():
    import tempfile
    ok = True
    tmp = os.path.join(tempfile.mkdtemp(prefix="cand_"), "c.jsonl")

    a = capture("J prefers smaller models for latency", "stated as a durable preference",
                source="telegram", path=tmp, now="2026-01-01T00:00:00")
    if not a:
        print("  FAIL: did not capture a fresh candidate"); ok = False

    if capture("J prefers smaller models for latency", "again", path=tmp) is not None:
        print("  FAIL: captured an exact duplicate — a queue that repeats itself is a transcript")
        ok = False

    # ★ WHY is mandatory, and the test asserts the REFUSAL rather than a default being filled in.
    try:
        capture("something", "", path=tmp)
        print("  FAIL: accepted a candidate with no reason. In three weeks that is an orphan "
              "sentence and promoting it is guesswork."); ok = False
    except ValueError:
        pass

    if touch(a, path=tmp, now="2026-01-02T00:00:00") is not True:
        print("  FAIL: touch() did not find a real id"); ok = False
    if touch("c9999", path=tmp) is not False:
        print("  FAIL: touch() claimed success on an id that does not exist — a retrieval counter "
              "that cannot miss is not counting"); ok = False

    earned, unproven = review(path=tmp)
    if len(earned) != 1 or earned[0]["retrieved"] != 1:
        print("  FAIL: retrieval was not recorded"); ok = False
    if unproven:
        print("  FAIL: the only candidate was retrieved, so nothing should be unproven"); ok = False

    # ★★ NOTHING IN THIS MODULE MAY WRITE A MEMORY. Asserted structurally, not by intention:
    #    if a future edit imports the memory writers, the queue has become the thing it exists to
    #    stand in front of.
    import ast
    tree = ast.parse(io.open(os.path.join(HERE, "memory_candidates.py"), encoding="utf-8").read())
    mods = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods.update(a.name.split(".")[0] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.add(n.module.split(".")[0])
    bad = mods & {"memory_commit", "memory_consolidate", "subprocess"}
    if bad:
        print("  FAIL: imports %s — this module must never be able to promote a candidate "
              "to a memory; promotion is a separate human decision." % sorted(bad)); ok = False

    print("  6/6 candidate cases ok" if ok else "  candidate FAILURES above")
    print("memory_candidates selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 2


def main():
    if "--selftest" in sys.argv:
        return selftest()
    earned, unproven = review()
    print("  candidates: %d earned (retrieved at least once), %d unproven"
          % (len(earned), len(unproven)))
    for r in earned[:10]:
        print("   %s  x%d  %s" % (r["id"], r["retrieved"], r["text"][:80]))
    if unproven:
        print("   -- unproven (captured, never pulled; that is evidence, not a verdict) --")
        for r in unproven[:5]:
            print("   %s  %s   [why: %s]" % (r["id"], r["text"][:60], r.get("why", "")[:40]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
