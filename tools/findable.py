#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""findable.py — will I be able to FIND this record later, and will it WIN? Ask before writing it.

    python findable.py "<title or path>" "<the question I'd actually ask when I need this>"
    python findable.py --selftest

★★★★★ WHY, AND WHY IT IS A WRITE-TIME TOOL.

J, 2026-08-25: *"How would you set up a system that would do that for any agent. Did you not ever
build it?"* I checked instead of guessing: no. `memory_echo` asks whether I have already written
this. `keyword_probe` MEASURED that bare keys retrieve 40/40. The measurement existed and the
**enforcement** did not — the same shape as `whereis.currency()`, which annotates staleness and never
acts on it.

★ THE IDEA: findability is not a property of a title. It is a property of the PAIR — how you wrote it,
  and how you would later ask for it. So the write step must produce two things: the record, and the
  QUESTION you expect to ask when you need it, phrased the way you would ask it while stuck.

★★★★ AND IT IS TWO QUESTIONS, NOT ONE — J CAUGHT THIS BEFORE IT SHIPPED.
  My first version compared the TITLE against the question and nothing else. J asked: *"Does your
  retrieval system not read documents when it's finding them and only titles?"* It reads them. From
  `recall.py:238`, the real scoring line:

      weighted += min(b, 4) + 10 * n + 8 * d        # body (capped), name x10, description x8

  and the PRIMARY key is coverage — how many distinct query terms the file touches — counting a term
  found in the body OR the name OR the description.

  So the body gets you FOUND, and the title gets you RANKED FIRST. A word in the filename is worth
  10; the same word appearing fifty times in the body is worth 4. Body saturates, title does not.

  ⚠ My title-only version would therefore have FAILED records that are perfectly findable through
    their body. A gate that rejects good records is worse than no gate, because you learn to ignore
    it — and I was about to put it in the template.

Hence two verdicts, which fail for different reasons and want different fixes:
    FOUND?  question vs. the whole record (title + description + body) — the cliff test
    WINS?   question vs. title + description only — the ranking test
  Failing FOUND means rewrite the content. Failing WINS means rename the file.

★★ THE CLIFF IS WHY THIS IS A GATE AND NOT A VIBE. 24 probes, two corpora: 0 shared content words
   → 0/4 found; ≥1 shared content word → 20/20 found, all in the top three.

⚠⚠ WHAT IT DOES NOT FIX. It catches records that CANNOT be found. It does nothing about records I
   never think to search for — the dead reranker figure that cost me an evening was the second kind.
   It was findable the whole time; I never asked. One tool should not claim both.
"""
import argparse
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DF_PATH = os.path.join(HERE, ".keyize_df.json")

# ★ THRESHOLD CHOSEN ON A PRINCIPLE, NOT TUNED ON THE OUTCOME. A term in more than a fifth of all
#   documents is a stopword in practice: matching on it narrows nothing. Fixed BEFORE looking at how
#   any of my own titles scored — a threshold invented after seeing the data is a preference wearing
#   a decimal point.
COMMON_FRACTION = 0.20

STOP = {"the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for", "is", "it",
        "be", "was", "were", "do", "does", "did", "not", "no", "my", "i", "you", "your", "we",
        "that", "this", "these", "those", "what", "when", "how", "why", "can", "cannot", "with",
        "from", "at", "as", "by", "so", "then", "than", "there", "here", "have", "has", "had",
        "would", "could", "should", "will", "about", "into", "out", "up", "down", "me", "am"}


def words(s):
    return {w for w in re.findall(r"[a-z0-9']+", str(s).lower().replace("-", " "))
            if w not in STOP and len(w) > 2}


def build_df(corpus_dir):
    """Count document frequency across a corpus. One pass, no index required.

    ★ ADDED WHEN THIS TOOL WAS PORTED OUT OF ITS HOME REPO, 2026-08-25 — and the port is what found
      the problem. The original read a cached `.keyize_df.json` that exists only on the machine it
      was written on. Copied here, `--selftest` failed instantly with FileNotFoundError.
      ⚠ It failed LOUDLY only because `load_df()` was written to RAISE rather than return an empty
        dict. An empty df marks every term rare, so a "graceful" version would have PASSED every
        record it was ever shown — a gate that cannot fail, shipped into a template, in a repo whose
        own sample memory is called `example-empty-is-not-clean`.
    """
    df, n = {}, 0
    for dirpath, dirnames, filenames in os.walk(corpus_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d != "__pycache__"]
        for fn in filenames:
            if not fn.lower().endswith((".md", ".txt")):
                continue
            try:
                text = io.open(os.path.join(dirpath, fn), encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            n += 1
            for w in words(text) | words(fn):     # a term counts ONCE per document, not per hit
                df[w] = df.get(w, 0) + 1
    return df, n


def load_df(corpus_dir=None, hint=None):
    """Cached df if present, else counted from the corpus. Raises if neither is possible.

    ⚠ NEVER returns an empty df on failure. An empty df makes every term look rare, which turns this
      gate into a rubber stamp — and a check that cannot fail is worse than no check, because it
      gets mistaken for coverage.
    """
    # ★★★★ AN EXPLICIT corpus_dir WINS OVER THE CACHE. Found 2026-08-25 by a local reviewer whose
    #   own explanation was wrong — it claimed this function "silently fails", then described it
    #   raising a RuntimeError, which is the opposite of silent. But it pointed at the right
    #   function and the right trigger, so I reproduced it instead of dismissing it, and the bug
    #   was real:
    #   ⚠ this used to test the cache FIRST. So on any machine where `.keyize_df.json` exists — i.e.
    #     the repo this tool was written in — `corpus_dir` was SILENTLY IGNORED. The fix I had just
    #     made for the df=0 problem ("measure against the corpus the record actually lives in")
    #     worked in the template, which has no cache, and did NOTHING here.
    #   ★ THAT IS THE THIRD TIME TONIGHT I PATCHED THE PATH THAT DOES NOT RUN — after the guidance
    #     scope going into recall's slow walk while flat.exe answers, and the scope block referencing
    #     two names that do not exist at module level. Same evening, same shape, three times.
    #   An argument that is silently ignored is worse than one that errors: the caller believes they
    #   controlled something they did not.
    # ★★★★★ EXPLICIT CORPUS vs INFERRED HINT — separated 2026-08-26, and conflating them cost me
    #   two wrong verdicts in one night, in opposite directions.
    #   HISTORY. (1) Originally the cache won unconditionally, so an explicit corpus was SILENTLY
    #   IGNORED — a local reviewer caught that. (2) I fixed it by making any corpus_dir win, and the
    #   CLI began inferring one from the record's own directory. That fixed a df=0 bug in the
    #   template and INTRODUCED a new one here: checking a memory that lives in an 18-file folder
    #   measured rarity against 18 documents, so ordinary words like "tool" and "verdict" were
    #   called COMMON and the record was reported unfindable. Against the real 26,523-document
    #   corpus every one of them is rare and both verdicts pass.
    #   ★ THE DISTINCTION I HAD MISSED: a corpus the caller NAMES is an instruction and must win.
    #     A corpus INFERRED from a file path is a guess, and a guess must not override real data.
    #     They are not the same argument and should never have shared a parameter.
    #   ⚠ And note how this was caught: the tool PRINTED ITS DENOMINATOR ("3 of 18 docs") and the
    #     number looked wrong. Same night I wrote [[my-tools-compute-the-number-and-then-do-not-say-it]];
    #     saying the number is what exposed the misconfiguration within five minutes.
    if corpus_dir:
        df, n = build_df(corpus_dir)
        if n == 0:
            raise RuntimeError("the corpus at %s contains no .md/.txt documents — refusing to "
                               "score, because an empty corpus makes every word look distinctive."
                               % corpus_dir)
        return df, n
    if os.path.exists(DF_PATH):
        d = json.load(io.open(DF_PATH, encoding="utf-8"))
        return d["df"], int(d["n_docs"])
    root = (hint
            or os.environ.get("MEMORY_DIR")
            or os.path.join(os.path.dirname(HERE), "memory"))
    if not os.path.isdir(root):
        raise RuntimeError(
            "no term statistics: %s is absent and there is no corpus at %s. Point MEMORY_DIR at "
            "your memory directory." % (DF_PATH, root))
    df, n = build_df(root)
    if n == 0:
        raise RuntimeError("the corpus at %s contains no .md/.txt documents — refusing to score, "
                           "because an empty corpus makes every word look distinctive." % root)
    return df, n


def _desc_of(text):
    m = re.search(r"^description:\s*[\"']?(.*?)[\"']?\s*$", text or "", re.M)
    return m.group(1) if m else ""


def check(title, question, body="", df=None, n_docs=None, corpus=None, hint=None):
    if df is None:
        df, n_docs = load_df(corpus, hint)
    q = words(question)
    t_words = words(title)
    d_words = words(_desc_of(body))
    b_words = words(body)

    # ★★★★★ SUBSTRING, NOT TOKEN EQUALITY — corrected 2026-08-25, hours after shipping this.
    #   I ran this tool on a memory I had just written and it reported WINS? NO. The title was
    #   `a-single-sample-instrument-cannot-prescribe-waiting`; the question said "wait". Tokenised,
    #   {waiting} and {wait} do not intersect, so it declared the record unrankable.
    #   ⚠ But `recall.py` does NOT tokenise the target. Its scorer is
    #         b, n, d = low.count(t), name.count(t), desc.count(t)
    #     — SUBSTRING counts. `"wait" in "…prescribe-waiting"` is True, so recall would have
    #     credited that filename match at 10x. The record was perfectly rankable and my gate said
    #     otherwise.
    #   ★ A FALSE FAILURE, which is the exact defect this file's own docstring warns about: "a gate
    #     that rejects good records is worse than no gate, because you learn to ignore it." J caught
    #     one form of that before it shipped. This is a second form, and it DID ship — into the
    #     template — because I modelled what I assumed recall does instead of reading what it does.
    #   The query terms are still tokenised and stop-filtered (that half matches recall's `_terms`);
    #   only the TARGET side becomes a raw surface, exactly as in recall.
    def _hits(qterms, surface_words, raw):
        low = (raw or "").lower()
        return sorted({t for t in qterms if t in low or any(t in w for w in surface_words)})

    rank_raw = "%s %s" % (title, _desc_of(body))
    found_raw = "%s %s %s" % (title, _desc_of(body), body)

    cut = int(n_docs * COMMON_FRACTION)
    shared_found = _hits(q, t_words | d_words | b_words, found_raw)
    shared_rank = _hits(q, t_words | d_words, rank_raw)
    rare_found = [w for w in shared_found if df.get(w, 0) <= cut]
    rare_rank = [w for w in shared_rank if df.get(w, 0) <= cut]

    return {"shared_found": shared_found, "shared_rank": shared_rank,
            "rare_found": rare_found, "rare_rank": rare_rank,
            "df": {w: df.get(w, 0) for w in shared_found},
            "cut": cut, "n_docs": n_docs, "has_body": bool(b_words),
            "q_words": sorted(q), "t_words": sorted(t_words)}


def report(title, question, body="", verbose=True, corpus=None, hint=None):
    r = check(title, question, body, corpus=corpus, hint=hint)
    if not verbose:
        return r
    print("\n  TITLE    %s" % title)
    print("  QUESTION %s" % question)
    if not r["has_body"]:
        print("  ⚠ no body supplied — FOUND? is being judged on the title alone, which understates it.")
    print("  " + "-" * 68)

    # ---- 1. FOUND? ---------------------------------------------------------------
    if not r["rare_found"]:
        if r["shared_found"]:
            print("  ✗ FOUND?  NO — shares only COMMON words (%s), each in >%d of %d docs."
                  % (", ".join(r["shared_found"][:5]), r["cut"], r["n_docs"]))
            print("            Matching on a word that frequent narrows nothing. Treat as no share.")
        else:
            print("  ✗ FOUND?  NO — the record and the question share NO content word at all.")
            print("            Measured: 0 shared words scored 0/4. A cliff, not a near-miss.")
        print("            FIX: change the CONTENT — say the thing using a word from the question.")
        print("            question: %s" % ", ".join(r["q_words"][:10]))
    else:
        print("  ✓ FOUND?  yes — %s (≥1 shared distinctive word retrieved 20/20, top three)"
              % ", ".join("%s df=%d" % (w, r["df"][w]) for w in r["rare_found"][:5]))
        _zero = [w for w in r["rare_found"] if r["df"][w] == 0]
        if _zero:
            print("  ⚠ df=0 for %s — that word is in the record but in NO document I counted."
                  % ", ".join(_zero))
            print("    Either it is genuinely unique, or I am measuring the WRONG CORPUS.")
            print("    df=0 scores as maximally rare, so a mis-aimed run passes everything.")

    # ---- 2. WINS? ----------------------------------------------------------------
    # ★★★★★ THIS VERDICT USED TO BE CALLED "WINS?" AND IT OVERCLAIMED. Renamed 2026-08-25, within
    #   an hour of shipping, after testing it against reality instead of against itself.
    #   I ran it on a memory I had just written; it said WINS? yes. Then I ran the actual query
    #   through recall.py: the record was NOT in the top five. It was indexed (3 records, corpus.bin
    #   rebuilt after the write) — it simply lost to files that ALSO carry a x10 name match.
    #   ⚠ The check only ever proved that a distinctive query word sits in a high-weight FIELD. It
    #     never modelled the FIELD OF COMPETITORS, so it was reporting a NECESSARY condition in the
    #     grammar of a sufficient one. "WINS?" is a promise; "CAN RANK?" is what the evidence
    #     supports.
    #   ★ Two false verdicts from this tool in one hour, in opposite directions: a false NO from
    #     tokenising what recall substring-matches, and a false YES from naming a precondition as an
    #     outcome. Both found the same way — by running the real engine and comparing, rather than
    #     re-reading my own model of it.
    if not r["rare_rank"]:
        print("  ⚠ CAN RANK? NO — nothing distinctive in the TITLE or DESCRIPTION.")
        print("              Name scores x10 and description x8; body saturates at 4. You may be")
        print("              found and still lose to any file with the word in its name.")
        print("              FIX: RENAME. Put a word from the question in the filename.")
    else:
        print("  ✓ CAN RANK? yes — %s sits in a x10/x8 field" % ", ".join(r["rare_rank"][:5]))
        print("              ⚠ NECESSARY, NOT SUFFICIENT. This does not say you will out-rank the")
        print("              field — other files may carry the same word in THEIR names. To know,")
        print("              run the question through recall.py and look for yourself.")

    return r


def selftest():
    fails = []
    df = {"kraken": 12, "privateer": 4, "system": 9000, "memory": 8000,
          "wetness": 31, "guardian": 300, "restart": 900}
    n = 26523

    # the cliff — nothing shared anywhere must fail FOUND
    r = check("a-quiet-channel", "which ship do I want most", "", df, n)
    if r["shared_found"]:
        fails.append("invented a shared word: %s" % r["shared_found"])

    # ★ J'S CASE, THE ONE THAT BROKE v1: findable through the BODY while the title shares nothing.
    #   v1 compared title-only and would have failed this record, which recall finds correctly.
    r = check("a-quiet-channel-is-not-an-empty-one",
              "what happened with the kraken privateer",
              "I was thinking about the kraken privateer variant that evening.", df, n)
    if not r["rare_found"]:
        fails.append("a record findable via its BODY was reported unfindable — the v1 bug")
    if r["rare_rank"]:
        fails.append("body words leaked into the RANKING surface: %s" % r["rare_rank"])

    # and the inverse must hold: title match counts for both
    r = check("kraken-privateer-notes", "what is the kraken privateer", "", df, n)
    if "kraken" not in r["rare_rank"] or "kraken" not in r["rare_found"]:
        fails.append("a title match did not count for both verdicts: %s" % r)

    # a shared COMMON word must not count as distinctive — without this every record 'passes'
    # by containing the word "memory"
    r = check("memory-system-notes", "how does my memory system work", "", df, n)
    if r["rare_found"]:
        fails.append("a df-8000 word was treated as distinctive: %s" % r["rare_found"])

    # kebab-case must tokenise, or every slug silently has no words and everything fails
    r = check("how-thick-is-the-wet-layer", "can the sim do wetness", "", df, n)
    if "wet" not in r["t_words"]:
        fails.append("kebab slug did not tokenise: %s" % r["t_words"])

    # frontmatter description must reach the RANKING surface (it carries the x8)
    r = check("opaque-slug", "why does the guardian restart",
              "---\ndescription: the guardian restart loop\n---\nbody text", df, n)
    if "guardian" not in r["rare_rank"]:
        fails.append("frontmatter description did not reach the ranking surface: %s" % r["rare_rank"])

    # stopwords must not create a false share
    if check("this-is-the-thing", "is the that", "", df, n)["shared_found"]:
        fails.append("stopwords produced a false share")

    # the real DF file must have the shape we assume
    try:
        real_df, real_n = load_df()
        if not isinstance(real_df, dict) or real_n <= 0:
            fails.append(".keyize_df.json has an unexpected shape")
    except Exception as e:
        fails.append("could not load the real DF file: %s: %s" % (type(e).__name__, e))

    for f in fails:
        print("   -", f)
    print("findable selftest:", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("target", nargs="?", help="a title/slug, or a path to an existing record")
    ap.add_argument("question", nargs="?")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if not a.target or not a.question:
        ap.error("give me a title (or path) AND the question you would ask to find it")

    body, title, corpus, hint = "", a.target, None, None
    if os.path.isfile(a.target):
        body = io.open(a.target, encoding="utf-8", errors="replace").read()
        title = os.path.basename(a.target)
        # ★ MEASURE AGAINST THE CORPUS THE RECORD ACTUALLY LIVES IN — 2026-08-25, found by running
        #   it. Checking `sample/memory/the-cache-key-omitted-the-locale.md` reported `users df=0`,
        #   which is impossible for a word that is IN the record: the default corpus was a different
        #   directory that simply does not contain it.
        #   ⚠ And df=0 is scored as maximally RARE, so pointing this tool at the wrong corpus makes
        #     every record pass. The failure mode of a mis-aimed gate is not noise — it is silent
        #     approval, which is the same shape as the empty-df hazard one function up.
        hint = os.path.dirname(os.path.abspath(a.target))
    r = report(title, a.question, body, corpus=corpus, hint=hint)
    return 0 if (r["rare_found"] and r["rare_rank"]) else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
