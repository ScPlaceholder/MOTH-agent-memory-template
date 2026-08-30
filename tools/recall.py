#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recall.py — search the memory tree before acting.

    python recall.py "the terms you would have guessed at"
    python recall.py --selftest

WHY THIS EXISTS. Storage is not the hard part of agent memory; **retrieval is**. An agent with a
thousand well-written memories and no cheap way to reach them behaves exactly like an agent with
none. The failure is silent: it does not error, it simply answers from whatever is in context and
never learns that the answer was already on disk.

So the design goal is not "find the best match". It is **make retrieving cheaper than re-deriving**,
because that is the only property that changes behaviour. A retrieval step that costs more effort
than guessing will be skipped every time, correctly.

RANKING: COVERAGE-FIRST, NOT TF-IDF — and this is a measured choice, not a preference.
  For this corpus shape (many short single-fact files), what a user wants is the file that mentions
  the MOST OF THEIR TERMS, not the file where one rare term is statistically surprising. Classic
  tf-idf rewards a long document that happens to contain one unusual word, which is precisely the
  wrong answer when the corpus is deliberately made of small notes.
  Two consequences, both deliberate:
    * a file matching 4 of your 5 terms outranks one matching 1 rare term;
    * BODY HITS ARE CAPPED (see BODY_CAP) so a file cannot win by repeating a term twenty times.

⚠ A NOTE ON MEASURING THIS YOURSELF. Do not evaluate retrieval by asking about topics you know are
  absent and observing that nothing comes back. That test cannot fail and measures nothing. See
  README, "Benchmarking".
"""
import argparse
import io
import os
import re
import shutil
import sys
import tempfile

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOTS = [os.path.join(os.path.dirname(HERE), "memory")]

# ★ Body hits are capped so repetition cannot buy rank. Measured: without a cap, one long file that
#   says a term many times displaces short files that actually answer the question.
BODY_CAP = 4
# ★ A hit in the frontmatter description is worth more than one in the body: the description is the
#   author's own statement of what the file is FOR.
DESC_WEIGHT = 3
NAME_WEIGHT = 4

# ★★★★★ THIS LIST WAS FAR TOO SHORT, AND THE BENCHMARK PROVED IT — 2026-08-25.
#   The first real retrieval measurement scored hit@1 6/10, and diagnosing the four misses found ONE
#   cause in ALL FOUR: the wrong file won on function words this set was missing.
#       "old rows where we cannot tell which region..."  -> beaten on {old, cannot, which}
#       "the slow tail is the container waking up..."    -> beaten on {rather, than}
#       "people in one country were shown..."            -> beaten on {one}
#   ⚠ AND COVERAGE-FIRST AMPLIFIES IT, which is the uncomfortable part: the headline ranking feature
#     rewards matching MANY query terms, so when most of them are noise it rewards matching noise. A
#     file hitting 3 junk words scores 0.3^2 and beats the right file hitting 1 real word at 0.1^2.
#     The feature is not wrong; it is only ever as good as the terms fed into it.
#   ★ A GENERAL fix, not tuning to the probes: "a retrieval system should not treat 'than' as a
#     content word" is true with no reference to any benchmark. Adjusting weights until my own ten
#     questions passed would be overfitting; enlarging a demonstrably deficient stopword list is
#     repairing a defect the benchmark happened to reveal.
STOP = {
    "the", "a", "an", "and", "or", "but", "nor", "so", "yet", "is", "are", "was", "were", "be",
    "been", "being", "am", "do", "does", "did", "have", "has", "had", "will", "would", "shall",
    "should", "can", "could", "may", "might", "must", "cannot",
    "to", "of", "in", "on", "for", "with", "at", "by", "from", "into", "onto", "up", "down", "out",
    "over", "under", "about", "after", "before", "during", "while", "than", "then", "through",
    "between", "against", "without", "within", "upon", "off", "back",
    "i", "my", "me", "we", "us", "our", "you", "your", "he", "she", "his", "her", "they", "them",
    "their", "it", "its", "this", "that", "these", "those", "which", "who", "whom", "whose", "what",
    "where", "when", "why", "how", "there", "here", "some", "any", "all", "each", "every", "other",
    "another", "such", "same", "one", "two", "no", "not", "only", "own", "both", "more", "most",
    "as", "get", "got", "make", "made", "take", "took", "come", "came", "go", "went", "see", "saw",
    "say", "said", "tell", "told", "know", "knew", "think", "thought", "want", "need", "rather",
    "just", "very", "much", "many", "still", "even", "also", "like", "way", "thing", "things",
}


def terms(query):
    """Query -> the distinct meaningful lowercase terms, order preserved."""
    out, seen = [], set()
    for raw in re.findall(r"[A-Za-z0-9_][A-Za-z0-9_'-]*", (query or "").lower()):
        # ★★ SPLIT ON HYPHENS, keeping the joined form too.
        #    Every memory NAME is kebab-case, so pasting a memory's own filename as the query
        #    produced one unmatchable term and found NOTHING — you could not look a file up by the
        #    name it is stored under, which is close to the most obvious query anyone makes.
        #    (codex, 2026-08-25; reproduced before fixing.)
        for t in ([raw] + raw.split("-")) if "-" in raw else [raw]:
            if t in STOP or len(t) < 2 or t in seen:
                continue
            seen.add(t)
            out.append(t)
    return out


def split_front(text):
    """(frontmatter_dict_ish, body). Tolerates a missing or malformed frontmatter block."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    head, body = text[3:end], text[end + 4:]
    fm = {}
    for line in head.splitlines():
        if ":" in line and not line.strip().startswith("#"):
            k, _, v = line.partition(":")
            fm[k.strip().lstrip("- ")] = v.strip()
    return fm, body


def score_file(path, qterms):
    """(score, description, matched_terms). Coverage-first; body hits capped."""
    try:
        text = io.open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return 0.0, "", []
    fm, body = split_front(text)
    name = (fm.get("name") or os.path.splitext(os.path.basename(path))[0]).lower()
    desc = (fm.get("description") or "").lower()
    low = body.lower()

    # ★★★★★ WORD-BOUNDARY MATCHING, NOT SUBSTRING — found by an external review, 2026-08-25.
    #   This block used `t in name` and `low.count(t)`, so **"bug" matched "debug"** and "cache"
    #   matched "cacheable". Measured before the fix: querying ["bug"] against a file containing
    #   only the word "debug" scored **5.00** and reported the term as MATCHED.
    #   ⚠ WHY IT IS WORSE THAN A RANKING WOBBLE: a false term hit counts toward COVERAGE, which is
    #     the headline claim of this whole tool. And the coverage multiplier IS mutation-tested —
    #     the test verifies the formula gets applied, and never checked that the term matcher
    #     feeding it was correct. **A verified formula over wrong inputs is still wrong.** The
    #     assertion guarded the arithmetic and not its operands.
    def _hits(term, hay):
        return re.search(r"\b%s\b" % re.escape(term), hay) is not None

    def _count(term, hay):
        return len(re.findall(r"\b%s\b" % re.escape(term), hay))

    matched, score = [], 0.0
    for t in qterms:
        hit = False
        if _hits(t, name.replace("-", " ")):
            score += NAME_WEIGHT
            hit = True
        if _hits(t, desc):
            score += DESC_WEIGHT
            hit = True
        n = _count(t, low)
        if n:
            score += min(n, BODY_CAP)
            hit = True
        if hit:
            matched.append(t)

    # ★★ COVERAGE-FIRST: the fraction of the query a file accounts for dominates the raw tally.
    #    Without this multiplier the ranking silently degrades into "who said it most".
    if qterms:
        score *= (len(matched) / float(len(qterms))) ** 2
    return score, (fm.get("description") or "").strip(), matched


def walk(roots, strict=True):
    """Yield every .md under `roots`.

    ⚠ A NONEXISTENT ROOT USED TO BE SKIPPED SILENTLY, so a typo'd --root produced a confident
      "no file matched" — indistinguishable from a real, correctly-searched absence. That is the
      same defect this whole project is about: cannot-tell reported as measured-nothing. It now
      says so on stderr, loudly, while still searching whatever roots ARE valid.
    """
    for root in roots:
        if not os.path.isdir(root):
            if strict:
                sys.stderr.write(
                    "  ⚠ NOT A DIRECTORY, SKIPPED: %s\n"
                    "    Any 'no match' below is about the roots that DO exist. This is not\n"
                    "    evidence the memory is empty.\n" % root)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in filenames:
                if fn.endswith(".md"):
                    yield os.path.join(dirpath, fn)


def recall(query, roots=None, top=5):
    qterms = terms(query)
    if not qterms:
        return []
    rows = []
    for path in walk(roots or DEFAULT_ROOTS):
        s, desc, matched = score_file(path, qterms)
        if s > 0:
            rows.append((s, path, desc, matched))
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
    ap = argparse.ArgumentParser(description="Search the memory tree before acting.")
    ap.add_argument("query", nargs="*", help="the terms you would otherwise have guessed at")
    ap.add_argument("--top", type=_pos_int, default=5)
    ap.add_argument("--root", action="append", default=None, help="memory dir (repeatable)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    q = " ".join(a.query)
    if not q.strip():
        ap.error("give me something to search for")
    # ★★ A QUERY OF NOTHING-BUT-STOPWORDS IS NOT A SEARCH THAT FAILED.
    #    "the and of" printed `no file matched any of: ` — an empty list, and a confident report of
    #    absence over a search that never had a term to look for. Third instance today of the same
    #    disease in this one repo: cannot-search reported as found-nothing. Say which it is.
    qt = terms(q)
    if not qt:
        print("  ⚠ NOTHING TO SEARCH FOR. Every word in %r is a common word this tool ignores" % q)
        print("    (the, and, of, is...), so no search was performed. This is NOT a statement")
        print("    about your memory — try again with the distinctive words.")
        return 2

    hits = recall(q, a.root, a.top)
    qn = len(qt)
    if not hits:
        # ⚠ NOT "nothing relevant exists". Say what was actually established.
        print("  no file matched any of: %s" % ", ".join(terms(q)))
        print("  That means THIS CORPUS has no hit for these terms — it does not mean the question")
        print("  is unanswerable, and it is not evidence the memory system works.")
        return 1
    print("  %d hit(s) for %d term(s):\n" % (len(hits), qn))
    for s, path, desc, matched in hits:
        print("  %6.2f  %s" % (s, os.path.basename(path)))
        print("          covers %d/%d: %s" % (len(matched), qn, ", ".join(matched)))
        if desc:
            print("          %s" % desc[:110])
        print()
    return 0


def selftest():
    """Builds a throwaway corpus and checks the ranking PROPERTIES, not just that it returns rows.

    ⚠ The controls matter more than the happy path. A search that returns something for every query
      looks healthy and is useless, so each assertion below names a way the ranking could be wrong.
    """
    fails = []
    tmp = tempfile.mkdtemp(prefix="recall_selftest_")
    # ⚠ Cleaned up at the end. Before this, every --selftest run left a directory behind;
    #   15 had accumulated in the system temp dir before an external review pointed at it.
    #   A tool that litters while proving it is healthy is making a claim it undermines.

    def w(name, desc, body):
        io.open(os.path.join(tmp, name + ".md"), "w", encoding="utf-8").write(
            "---\nname: %s\ndescription: %s\nmetadata:\n  type: feedback\n---\n\n%s\n" % (name, desc, body))

    # ★★★★★ THIS FIXTURE IS BUILT SO COVERAGE IS THE ONLY THING THAT CAN DECIDE IT, and that took a
    #   second attempt. The first version had the expected winner carrying the query term in its NAME
    #   and DESCRIPTION, so it won on weighting alone — mutation-testing showed that deleting the
    #   coverage multiplier entirely left the selftest PASSING. The assertion was decoration.
    #   A test for a feature must FAIL when the feature is removed, or it is testing something else.
    #   So: `broad-notes` matches all three terms weakly, in the body only. `deep-single` matches ONE
    #   term as hard as possible — name, description and repeated body. Without the coverage
    #   multiplier the deep single-term file wins; with it, the file that answers more of the
    #   question wins. Verified by mutation, not by inspection.
    w("broad-notes", "Assorted short observations",
      "The invalidation happened once. The mtime was equal. The cache was reused.")
    w("cache-cache-cache", "cache cache cache and nothing else",
      ("cache " * 40) + "\nOne term, said as loudly as possible, about nothing in particular.")
    w("mtime-comparison-notes", "How mtime comparison decides staleness", "mtime and size are the inputs.")

    roots = [tmp]

    # 1. COVERAGE BEATS DEPTH — the headline ranking claim, and the fixture can now detect its loss.
    hits = recall("cache invalidation mtime", roots, top=3)
    if not hits:
        fails.append("no hits at all for a query that plainly matches the fixture")
    elif os.path.basename(hits[0][1]) != "broad-notes.md":
        fails.append("coverage-first failed: a file matching ONE term hard outranked the file "
                     "covering all three terms (top was %s). This is the ranking property the "
                     "README advertises." % os.path.basename(hits[0][1]))

    # 2. the body cap must actually bind
    s_long, _, _ = score_file(os.path.join(tmp, "cache-cache-cache.md"), ["cache"])
    if s_long > (BODY_CAP + DESC_WEIGHT + NAME_WEIGHT):
        fails.append("BODY_CAP did not bind: a file repeating one term scored %.1f" % s_long)

    # 3. NEGATIVE CONTROL — an absent topic must return nothing.
    #    ⚠ This asserts the tool is not fabricating; it does NOT show retrieval is good. That
    #      distinction is the entire point of the README's benchmarking warning.
    if recall("chip photolithography wafer", roots, top=3):
        fails.append("returned hits for a topic absent from the fixture — matching is too loose")

    # 4. a query of pure stopwords must be refused, not answered with everything
    if terms("the and of it"):
        fails.append("stopword-only query produced terms")
    if recall("the and of it", roots, top=3):
        fails.append("stopword-only query returned hits")

    # 4b. ★★★★★ WORD BOUNDARIES — the regression test for the worst finding of the external
    #     review. Substring matching let "bug" match "debug" and COUNT TOWARD COVERAGE, i.e. it
    #     corrupted the exact property this tool advertises and mutation-tests. The multiplier was
    #     verified; its inputs never were.
    w("debugging-notes", "About debugging the parser", "debug debug debug")
    s_sub, _, m_sub = score_file(os.path.join(tmp, "debugging-notes.md"), ["bug"])
    if m_sub or s_sub:
        fails.append("SUBSTRING MATCH: query 'bug' matched a file containing only 'debug' "
                     "(score %.2f, matched=%s). False term hits inflate COVERAGE, which is the "
                     "headline ranking claim." % (s_sub, m_sub))

    # 5. ★★★ HOSTILE INPUTS. A memory folder is edited by hand and synced between machines, so it
    #    WILL eventually contain a truncated file, a binary blob with a .md name, or a directory
    #    someone created called "notes.md". A search tool that raises on any of them takes the whole
    #    agent down for a reason that has nothing to do with the query.
    #    ⚠ These cases were run once by hand while checking a code review's claims and every one
    #      passed — which protects nothing tomorrow. A check performed once is a measurement; a
    #      check in the suite is a guarantee. Promoted here for that reason alone.
    import shutil
    hostile = tempfile.mkdtemp(prefix="recall_hostile_")
    try:
        open(os.path.join(hostile, "binary.md"), "wb").write(bytes(range(256)))
        io.open(os.path.join(hostile, "noheader.md"), "w", encoding="utf-8").write("no frontmatter, cache")
        io.open(os.path.join(hostile, "broken-front.md"), "w", encoding="utf-8").write(
            "---\nname: x\nno closing fence, cache")
        io.open(os.path.join(hostile, "empty.md"), "w", encoding="utf-8").write("")
        os.makedirs(os.path.join(hostile, "adir.md"))          # a DIRECTORY with a .md name
        try:
            got = recall("cache", [hostile], top=5)
        except Exception as e:                                  # noqa: BLE001 — that IS the assertion
            fails.append("recall RAISED on a hostile memory folder (%s: %s) — one malformed file "
                         "must not break search for every other file" % (type(e).__name__, e))
            got = []
        if len(got) != 2:
            fails.append("hostile folder: expected exactly the 2 readable files to match 'cache', "
                         "got %d — malformed entries should score 0, not vanish or crash" % len(got))

        # ⚠⚠ AND THE GUARD MUST BE EXERCISED WHERE IT LIVES. The check above goes through recall(),
        #   which walks with os.walk and therefore only ever yields FILES — so the unreadable-path
        #   branch in score_file is UNREACHABLE from it. Verified by mutation: deleting the
        #   try/except left the test above passing. score_file is callable directly, so the guard is
        #   real and needs a direct call to prove it.
        try:
            s_dir, _, _ = score_file(os.path.join(hostile, "adir.md"), ["cache"])
            if s_dir != 0.0:
                fails.append("score_file on an unreadable path returned %.2f, expected 0.0" % s_dir)
        except Exception as e:                                  # noqa: BLE001 — that IS the assertion
            fails.append("score_file RAISED on an unreadable path (%s: %s) — a directory named "
                         "*.md, or a file being synced, must score 0 rather than crash the caller"
                         % (type(e).__name__, e))
    finally:
        shutil.rmtree(hostile, ignore_errors=True)

    for f in fails:
        print("   -", f)
    print("recall selftest:", "PASS" if not fails else "FAIL")
    shutil.rmtree(tmp, ignore_errors=True)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
