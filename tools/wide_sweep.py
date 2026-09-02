#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wide_sweep.py — the dumb arm. No index, no ranking, no filter it can be wrong about.

    python tools/wide_sweep.py cache locale                    # AND across two terms
    python tools/wide_sweep.py --roots ./memory ./notes -- cache locale
    python tools/wide_sweep.py "cache key locale"               # one quoted phrase, literal
    python tools/wide_sweep.py --selftest

⚠ THE FIRST TWO LINES USED TO SHOW A QUOTED "cache locale" AND THE RUST FILE SHOWED IT UNQUOTED.
  Those are different queries — one is a literal phrase, the other is an AND over two terms — and
  the quoted one returns NOTHING against this repository's own sample data. The headline example
  in the file did not work, and worse, the two arms were documented with different invocations
  while their headers claimed identical semantics, so the comparison that "verified" the claim may
  never have compared like with like.

★★★★★ WHY YOU WANT A DELIBERATELY WORSE SEARCH IN THE BOX.

A ranked retrieval path can fail in several distinct ways, and only one of them is ranking:

    SCOPE      the file was never in the index — so the ranker was never asked
    ROUTING    you queried the wrong tool entirely, and trusted its silence
    RANKING    indexed, queried, and the good answer lost to a worse one

Only the third is a ranking problem. The first two are invisible from inside the ranked path,
because every one of them produces the same output as a genuine absence: nothing. If your only
instrument is the ranked search, a scope error and an empty corpus are the same reading.

This tool exists to be the second reading. It has no index to be stale, no gate to return ABSENT,
and no extension list to be wrong about — so when the ranked path says nothing and this says
something, that disagreement localises the failure to SCOPE or ROUTING without any further work.

⚠⚠⚠ THE FILTER IS THE DEFECT — this is the trap, and it is worth stating plainly.
  The obvious way to make a full-corpus sweep affordable is an extension whitelist: only look in
  .md and .txt, skip the rest. That version FEELS assumption-free and is not. It reinstates exactly
  the thing the sweep exists to bypass — a scope decision, made once, invisible at query time, and
  reported to you as absence. In a real corpus an extension whitelist will quietly exclude source
  files, log files, extensionless files, and transcripts, which is a large fraction of the prose an
  agent actually needs.
  **So this version has no extension whitelist at all.** It excludes only what cannot contain prose
  (binary signatures) and dependency trees (which are not your writing). If you are tempted to add
  an extension list here, read this paragraph again.

⚠⚠ IT IS NOT A BETTER SEARCH. It is a worse one that cannot lie about coverage. Its hits are
  UNRANKED and it says so. The value is entirely in "the ranked path found nothing AND this found
  something" — the disagreement, not the result.

⚠ COST IS THE DESIGN CONSTRAINT, AND IT DECIDES THE IMPLEMENTATION.
  A fallback is only useful if it can run on every query where the ranked path came back empty,
  which in practice is most of them. That budget is what forces the three choices below:
    * match on BYTES with a substring prefilter, rather than decoding every file to text
    * read the HEAD FIRST and test for binary before reading the rest — otherwise every large
      media file on the machine is loaded in full and then discarded. A check that runs after the
      expensive step saves nothing.
    * skip dependency trees by DIRECTORY NAME, never by file type
  A fallback expensive enough to need a flag becomes a fallback nobody runs. Unconditional is the
  whole point.

⚠⚠⚠ THIS IS THE PORTABLE, SLOWER ARM ON PURPOSE. `rust_sweep/` beside it is the same semantics in
  Rust for large corpora, and the claim that they are PINNED is checked by `sweep_conformance.py`
  rather than by inspection. Read that file's header before trusting this sentence.
  ★ THE FIRST VERSION OF THIS CLAIM WAS FALSE AND WAS PUBLISHED. It was "verified" by one query
    against a sample corpus with no ties, no generated files, no symlinks and nothing outside
    cp1252 — every dimension on which the arms actually differed was absent, so the check could not
    have come back negative. Four result-changing divergences and a crash were found afterwards by
    someone who had not written the code: a path tie-break that returned a different document from
    each arm, a silent symlink hole in the walk, a sticky argument parser, and blank-term handling
    that agreed on the count while disagreeing underneath it.
  ⚠ If you change a matching rule in one arm, change it in the other AND add a fixture to
    `_sweep_conformance/` that would catch them diverging. A conformance suite that cannot fail is
    worse than none, because it gets quoted afterwards as a measurement.
"""

import argparse
import io
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# ⚠ Default to the template's own memory directory. Point it wherever your prose lives; there is
#   nothing machine-specific here on purpose, and a hard-coded absolute path would make the tool
#   silently search nothing on someone else's disk — which is the failure this file is about.
DEFAULT_ROOTS = [os.path.join(os.path.dirname(HERE), "memory")]
# ⚠ DIRECTORIES ONLY, and only ones that hold no prose of yours. NOT an extension list.
SKIP_DIRS = ("venv", ".venv", "site-packages", "node_modules", ".git", "__pycache__", "target")
# binary magic prefixes — cheaper and more honest than guessing from the filename
BINARY_MAGIC = (b"\x89PNG", b"RIFF", b"ID3", b"\xff\xd8\xff", b"PK\x03\x04", b"OggS",
                b"MZ", b"\x7fELF", b"\x1f\x8b")
MAX_BYTES = 64_000_000
DISAGREE_LOG = os.path.join(HERE, ".wide_sweep_disagreements.jsonl")


def _safe(line):
    """print() that cannot be killed by the corpus. See the call site for why this exists."""
    try:
        print(line)
    except UnicodeEncodeError:
        enc = (getattr(sys.stdout, "encoding", None) or "ascii")
        print(line.encode(enc, "replace").decode(enc, "replace"))


def _looks_binary(head):
    if head.startswith(BINARY_MAGIC):
        return True
    return b"\x00" in head[:1024]


def is_generated(path):
    """Did one of your own tools write this, rather than you?

    ⚠⚠ LABEL, DO NOT REMOVE. The sweep's entire virtue is that it excludes nothing — that is why it
      finds what an index cannot — so adding an exclusion to fix a DISPLAY problem trades away the
      one property it has. "What did my index actually hold for X" is a real question, and dropping
      generated files to tidy up the output makes it permanently unanswerable. These sort BELOW
      authored files and carry a tag; nothing is dropped.

    ⚠ THE NAME PATTERNS ARE INTERIM AND WILL ROT. The durable version is that each generator writes
      a sidecar beside its output and this reads the sidecar instead of guessing from the filename.
      The sidecar check is first so it wins as generators adopt it.
    """
    name = os.path.basename(path).lower()
    if os.path.exists(os.path.splitext(path)[0] + ".freshness.json"):
        return True
    return ("_meta" in name or "corpus_index" in name or "_disagreements" in name
            or name.endswith(".freshness.json") or "_index_meta" in name)


def sweep(terms, roots=None, limit=8):
    """[(hits, path, excerpt)] for files containing ALL terms. Unranked; order is hit count only.

    Returns (results, stats). stats carries what was skipped and why, because a sweep that quietly
    drops files is precisely the thing this exists to replace.
    """
    pats = [re.compile(re.escape(t).encode("utf-8"), re.I) for t in terms if t.strip()]
    if not pats:
        return [], {"error": "no usable terms"}
    prefilter = pats[0].pattern   # pats is already blank-filtered above
    t0 = time.time()
    out = []
    stats = {"scanned": 0, "binary": 0, "toobig": 0, "unreadable": 0}
    # ⚠ `roots is None` means "unset"; an EMPTY list means "you asked for nothing" and must not
    #   silently fall back to the default. Those are different requests.
    use = DEFAULT_ROOTS if roots is None else roots
    stats_missing = [r for r in use if not os.path.isdir(r)]
    for root in use:
        if not os.path.isdir(root):
            # ⚠ SAY IT. A missing root returns no matches, which reads exactly like an absent term.
            #   The Rust arm warned about this and this one silently continued -- so the file that
            #   preached the rule obeyed it and the file next to it did not.
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fn in files:
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > MAX_BYTES:
                        stats["toobig"] += 1
                        continue
                    # ⚠⚠ HEAD FIRST, THEN THE REST. The naive order — read the whole file, then ask
                    #   whether it was binary — loads every media file and archive on the machine in
                    #   full before discarding it. The binary check EXISTS in that version too; it
                    #   simply runs too late to save anything. Cost is decided by ordering here,
                    #   not by which files you skip.
                    with open(p, "rb") as fh:
                        head = fh.read(2048)
                        if _looks_binary(head):
                            stats["binary"] += 1
                            continue
                        data = head + fh.read()
                except OSError:
                    stats["unreadable"] += 1
                    continue
                stats["scanned"] += 1
                if not re.search(prefilter, data, re.I):
                    continue
                n = sum(len(pat.findall(data)) for pat in pats)
                if all(pat.search(data) for pat in pats):
                    m = pats[0].search(data)
                    exc = data[max(0, m.start() - 200):m.start() + 260].decode("utf-8", "replace")
                    # ⚠ DENSITY, NOT RAW COUNT. A raw hit count means the biggest file always wins,
                    #   and the biggest file in a memory system is usually an index dump containing
                    #   a copy of everything — so searching it for an answer is circular, and it
                    #   will outrank every note you actually wrote. Hits per KB puts a short note
                    #   above a huge dump. It is NOT a filter: nothing is excluded, so the sweep
                    #   keeps the one property it exists for.
                    kb = max(1, len(data) // 1024)
                    out.append({"hits": n, "density": n * 1000 // kb, "path": p,
                                "generated": is_generated(p), "excerpt": " ".join(exc.split())})
    stats["seconds"] = round(time.time() - t0, 2)
    stats["missing_roots"] = stats_missing
    # authored above generated; then density; then raw count; then path for a stable order
    out.sort(key=lambda r: (r["generated"], -r["density"], -r["hits"], r["path"]))
    # ⚠ REPORT THE TRUE MATCH COUNT SEPARATELY FROM THE SHOWN ONE. Found by racing this against the
    #   Rust arm: they disagreed on the number of matches and BOTH were right. This truncated to
    #   `limit` and then printed len() of the truncated list, so the headline number silently meant
    #   "shown" while reading as "found". A count that means something narrower than it says will be
    #   read as the wider thing every time.
    stats["matched"] = len(out)
    stats["shown"] = min(limit, len(out))
    return out[:limit], stats


def log_disagreement(query, n_hits, top_path):
    """Record ranked-said-nothing + sweep-found-something. THIS LOG IS THE PRODUCT.

    ⚠⚠ CALLED BY YOU, NOT BY THIS FILE — and that sentence is here because it was missing.
      This function shipped with zero call sites anywhere in the repository while its own first
      line declared itself the product. It could not have been called from inside `sweep()`:
      the disagreement is between the RANKED path and this one, and this file knows nothing about
      the ranked path. So it is a helper for the integration layer, by construction.
      ★ But "it cannot be called from here" is a reason it is not wired, not a reason nobody was
        told. A function that names itself the product and has no callers reads as working
        machinery to anyone skimming, including its author a week later.
      WIRE IT LIKE THIS, at whatever site owns both searches:

          hits = ranked_search(q)
          if not hits:
              res, _st = sweep(q.split())
              if res:
                  log_disagreement(q, len(res), res[0]["path"])

    Not the recovered answer — the RATE. After a week of real questions it tells you whether
    fall-through recovers anything or merely adds noise, and it costs nothing to collect. Without
    it you will keep the fallback because it feels prudent, which is not evidence.
    """
    try:
        with io.open(DISAGREE_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"query": query, "sweep_hits": n_hits,
                                 "top": top_path}, ensure_ascii=False) + "\n")
    except OSError:
        pass


def selftest():
    import tempfile
    ok = True
    d = tempfile.mkdtemp(prefix="_ws_")
    try:
        io.open(os.path.join(d, "plain.md"), "w", encoding="utf-8").write("the badger ate the pie\n")
        # ★ NO EXTENSION WHITELIST. A .py and an extensionless file must both be searched — the
        #   whitelist version of this excludes source files wholesale and still calls itself
        #   assumption-free, which is the single easiest way to reintroduce the scope defect.
        io.open(os.path.join(d, "code.py"), "w", encoding="utf-8").write("# badger in source\n")
        io.open(os.path.join(d, "noext"), "w", encoding="utf-8").write("badger with no extension\n")
        open(os.path.join(d, "pic.png"), "wb").write(b"\x89PNG\r\n\x1a\n" + b"badger" * 50)
        os.makedirs(os.path.join(d, "venv"))
        io.open(os.path.join(d, "venv", "dep.md"), "w", encoding="utf-8").write("badger dependency\n")

        res, st = sweep(["badger"], roots=[d])
        names = sorted(os.path.basename(r["path"]) for r in res)
        for want in ("plain.md", "code.py", "noext"):
            if want not in names:
                print("  [FAIL] %s not searched — an extension filter has crept back in" % want)
                ok = False
        if "pic.png" in names:
            print("  [FAIL] a PNG matched; binary detection is not working"); ok = False
        if "dep.md" in names:
            print("  [FAIL] searched inside venv — dependency trees are not your prose"); ok = False
        if ok:
            print("  [PASS] searches .py and extensionless files, skips binaries and venv")

        # ★ ALL terms must be present, or this becomes an OR-search that returns the whole corpus
        io.open(os.path.join(d, "two.md"), "w", encoding="utf-8").write("badger and mushroom\n")
        res2, _ = sweep(["badger", "mushroom"], roots=[d])
        n2 = sorted(os.path.basename(r["path"]) for r in res2)
        if n2 != ["two.md"]:
            print("  [FAIL] multi-term search is not an AND: got %r" % n2); ok = False
        else:
            print("  [PASS] multi-term search requires ALL terms")

        # ⚠ stats must report what was skipped — a sweep that silently drops files is the defect
        if "binary" not in st or "scanned" not in st:
            print("  [FAIL] stats do not report skips; silent dropping is what this replaces"); ok = False
        elif st["binary"] < 1:
            print("  [FAIL] the PNG was not counted as skipped-binary"); ok = False
        else:
            print("  [PASS] reports scanned/binary/toobig/unreadable rather than dropping quietly")

        # MIRROR: a term genuinely absent returns empty, or the sweep is useless as evidence
        res3, _ = sweep(["wombat"], roots=[d])
        if res3:
            print("  [FAIL] returned hits for an absent term"); ok = False
        else:
            print("  [PASS] a genuinely absent term returns nothing (so absence means something)")

        # ★ matched vs shown must be DISTINCT when truncation happens, or the headline lies
        for i in range(5):
            io.open(os.path.join(d, "m%d.md" % i), "w", encoding="utf-8").write("badger\n")
        _r4, st4 = sweep(["badger"], roots=[d], limit=2)
        if st4.get("shown") != 2 or st4.get("matched", 0) <= 2:
            print("  [FAIL] matched/shown collapsed under truncation: %r" % st4); ok = False
        else:
            print("  [PASS] 'matched' stays the true count when the display is truncated")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    print("\n  wide_sweep selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("terms", nargs="*")
    ap.add_argument("--roots", nargs="*", default=None,
                    help="directories to sweep (default: the template's memory/ directory)")
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    if not a.terms:
        ap.print_help(); sys.exit(0)
    res, st = sweep(a.terms, roots=a.roots, limit=a.limit)
    for _m in st.get("missing_roots") or []:
        print("  WARNING: root does not exist and was skipped: %s" % _m)
        print("           A missing root returns no matches, which reads exactly like an absent term.")
    print("  wide_sweep: %d matched (%d shown), %d scanned in %ss  "
          "[UNRANKED — order is hit count, not relevance]"
          % (st.get("matched", len(res)), st.get("shown", len(res)),
             st.get("scanned", 0), st.get("seconds")))
    for r in res:
        # ⚠⚠ NEVER DIE ON THE CORPUS YOU ARE SEARCHING. A Windows console defaults to cp1252, and
        #   this tool's own docstring contains ⚠ and ★ -- so running it over its own repository
        #   killed it mid-list with a partial result and a non-zero exit. A search tool that
        #   crashes on a document is worse than one that renders it imperfectly.
        _safe(  "    %s x%-4d d%-5d %s" % ("[gen]" if r["generated"] else "     ",
                                           r["hits"], r["density"], r["path"][-66:]))
        _safe("           ...%s..." % r["excerpt"][:220])
    sys.exit(0 if res else 2)
