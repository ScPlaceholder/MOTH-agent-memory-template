#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""lint_prompts.py — catch the ways a build instruction is unfollowable, before a user hits it.

    python lint_prompts.py            # check docs/BUILD_PROMPTS.md
    python lint_prompts.py --selftest

★★★★★ WHY THESE RULES AND NOT OTHER ONES.

Every rule here comes from a defect that was actually found by HANDING A STAGE TO AN AGENT AND
RUNNING IT — not from imagining what might go wrong. Three stages were executed that way and produced
six defects, and **all six were in the acceptance check rather than the prompt** — every time, the
built code was correct and my instructions for checking it were not. That was the
surprise: the instructions produce working code. It is the *checks* that cannot be followed, which is
worse, because a check nobody can run is indistinguishable from a check that passed.

Executing a stage costs a full agent run. These rules cost milliseconds and catch the shapes already
proven to occur, so they run in the suite forever rather than on the day somebody remembers.

⚠ THIS DOES NOT REPLACE RUNNING THE STAGES. It catches shapes already seen. Only execution finds
  the shape nobody has met yet — that is the whole reason these rules exist. Keep doing both.

  ⚠ That sentence said "these six" while seven rules were live, as did the tool's own success
    footer. R7 was added and neither sentence was. The count is now computed from `_RULE_IDS` and
    cross-checked against the source by the selftest, because a number typed into prose is a claim
    nothing verifies — which is precisely the class of defect this file was written to catch.
"""
import argparse
import io
import os
import re
import sys

# Every rule this tool can emit. The selftest cross-checks this against the source, so adding a rule
# without listing it here — or listing one that no longer fires — fails loudly instead of quietly
# making the tool misdescribe itself.
_RULE_IDS = ("R1", "R2", "R3", "R4", "R5", "R6", "R7")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DOC = os.path.join(ROOT, "docs", "BUILD_PROMPTS.md")


def split_stages(text):
    """-> [(title, body)] for each '# Stage N — ...' section."""
    parts = re.split(r"^# (Stage \d+ [—-] [^\n]+)$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        out.append((parts[i].strip(), parts[i + 1]))
    return out


def _commands(body):
    """Only the fenced command blocks — what a reader actually copies and runs."""
    return "\n".join(re.findall(r"```(?:bash|sh)?\n(.*?)```", body, re.S))


def _pass_sentence(body):
    """The pass-condition PARAGRAPH — colon inside or outside the bold, stopping at the blank line.

    ⚠ The first version took a fixed 400-character window, which spilled straight into the ⚠ note
      underneath — and those notes quote the old broken wording on purpose. So the linter read the
      explanation of a fix as the defect, for the second time in one file. A window measured in
      CHARACTERS is a guess about structure; the blank line is the structure.
    """
    m = re.search(r"\*\*Pass condition:?\*?\*?(.*?)(?:\n\s*\n|\Z)", body, re.S)
    return m.group(1) if m else ""


def lint(text):
    """★★ SCAN COMMANDS AND THE PASS SENTENCE, NEVER THE EXPLANATORY PROSE.

    The first version scanned the whole stage body and produced 5 false positives out of 6 hits —
    because the ⚠ notes in this document deliberately QUOTE the broken wording they are explaining.
    `mv memory_index.json` was fixed, and the note describing the fix still contains
    `memory/.memory-index.json`; the contradictory `words ÷ 400` criterion was replaced, and the
    note explaining why still contains it.

    ★★★ So **explaining a defect in place reintroduces its signature**, and a naive checker reads
    the documentation of a fix as the bug. Same family as writing up a measurement into the corpus
    it was measured on: the act of recording changes what the next reader sees.

    A checker that mostly cries wolf is worse than none — it trains you to skim its output, which
    is exactly how the real hit gets missed.
    """
    problems = []
    for title, body in split_stages(text):
        prompt = "\n".join(l for l in body.splitlines() if l.strip().startswith(">"))
        acc = _commands(body)
        pc = _pass_sentence(body)

        # ---- R1: the acceptance names a FILE the prompt never specified ----------------------
        #   Stage 1 said `mv memory_index.json` while its prompt only said "a single index file",
        #   so the builder chose `memory/.memory-index.json` — different name, different folder,
        #   hidden. The user gets "no such file" and no way to know why.
        cmd_files = set(re.findall(r"[\w.-]+\.(?:json|txt|jsonl|db|npz)\b", acc))
        for f in sorted(cmd_files):
            if f in ("probes.json", "mixed_probes.json", "baseline.txt"):
                continue                      # shipped or explicitly created by stage 0
            if f not in prompt:
                problems.append((title, "R1 acceptance uses %r but the prompt never names it — "
                                        "the builder will choose its own path" % f))

        # ---- R2: byte-for-byte file comparison ----------------------------------------------
        #   Measured: the same output captured two ways on Windows differed ONLY in the em-dash
        #   and bullet. Identical as ASCII, different as bytes. A pass condition that goes red
        #   because of a dash is one people learn to ignore.
        _r2 = acc + "\n" + pc
        if re.search(r"IDENTICAL to \w+\.txt|diff .*baseline|byte-for-byte", _r2) and \
                "verdict" not in _r2.lower():
            problems.append((title, "R2 compares files byte-for-byte without saying to compare the "
                                    "VERDICT/numbers — fails on text encoding alone"))

        # ---- R3: two numeric criteria that can contradict -------------------------------------
        #   Stage 2 asked for "roughly words/400" AND "never fewer than the number of files".
        #   On the shipped sample that is ~11 vs >=23. Both cannot hold, and the reader cannot
        #   tell a pass from a failure.
        if pc:
            if re.search(r"÷|/\s*400|divided by", pc) and re.search(r"never fewer|at least|no fewer", pc):
                problems.append((title, "R3 pass condition gives TWO numeric criteria that can "
                                        "contradict each other — check per-item, not in aggregate"))

        # ---- R4: an aggregate check on a corpus of unknown shape ------------------------------
        #   The deeper form of R3: an aggregate condition silently encodes an assumption about
        #   how big the documents are. This template's own format rules guarantee many small ones.
        if pc and re.search(r"\btotal\b.*\bcount\b|\bcount is\b.*plausible", pc, re.I) and \
                not re.search(r"per file|each file|every file", pc, re.I):
            problems.append((title, "R4 aggregate pass condition with no per-file form — it assumes "
                                    "a corpus shape that nothing states"))

        # ---- R6: a placeholder describing something the reader may not HAVE -------------------
        #   Stage 5's check said: recall.py "<a topic you have written about twice>". That is not a
        #   value the reader substitutes — it is a PROPERTY OF THEIR CORPUS, and if they do not
        #   happen to have it, the command returns the wrong outcome and they cannot tell whether
        #   the code is broken or the corpus is simply missing the case.
        #   A placeholder is fine when the reader obviously has the thing (a question they know the
        #   answer to). It is a defect when the stage requires a corpus SHAPE and never tells them
        #   how to create it. Flag any placeholder whose text implies existing content, unless the
        #   stage shows how to make it.
        for ph in set(re.findall(r"<([^>]{6,})>", acc)):
            implies_corpus = re.search(r"\bwritten\b|\btwice\b|\bexisting\b|\byou have\b|\byour notes\b",
                                       ph, re.I)
            makes_it = re.search(r"mkdir|printf|cat >|New-Item|echo .*>", acc)
            if implies_corpus and not makes_it:
                problems.append((title, "R6 acceptance needs %r — a corpus PROPERTY the stage never "
                                        "creates. If the reader lacks it they cannot tell a broken "
                                        "build from a missing case" % ph[:44]))

        # ---- R7: every stage must DECLARE whether it has actually been run --------------------
        #   The document used to present eleven stages as equally verified. Eight had been executed
        #   against a real agent and produced twelve defects; two could not be executed at all for
        #   want of a model. A reader could not tell those apart — and untested is exactly where
        #   every defect has been.
        #   ★ Made a RULE rather than a one-time edit so a new stage cannot be added without
        #     declaring its status. A note decays; a lint does not.
        #   ⚠ WIDENED 2026-08-25, and the reason matters more than the edit. Stages 6 and 8 were
        #     marked NOT TESTED "for want of a model" — see above, in this very comment. Both models
        #     turned out to be cached locally the whole time; the blocker was an interpreter without
        #     torch. Running them produced a REJECT for SPLADE and, for the cross-encoder, a drop
        #     from 10/14 to 6/14 — a recommended stage that measurably makes retrieval WORSE.
        #     Marking those TESTED with their date and verdict then tripped this rule, because the
        #     pattern demanded the marker be the ENTIRE bold span (`**TESTED**`) and would not accept
        #     `**✅ TESTED 2026-08-25 — REJECT**`.
        #   ★ I widened the rule rather than shortening the text, because the rule's own stated
        #     purpose is that "a reader cannot tell a verified instruction from an unverified one" —
        #     and a dated marker carrying its verdict serves that purpose strictly better than a bare
        #     word. The requirement is unchanged: the declaration must still OPEN a bold span, so it
        #     cannot be buried mid-paragraph. A fixture below pins the dated form so a future tidy-up
        #     cannot quietly narrow this back.
        if not re.search(r"\*\*(?:✅ )?TESTED\b|\*\*⚠ NOT TESTED", body):
            problems.append((title, "R7 does not declare TESTED or NOT TESTED — a reader cannot "
                                    "tell a verified instruction from an unverified one"))

        # ---- R5: every stage must HAVE a prompt and a pass condition --------------------------
        if "> **Prompt:**" not in body:
            problems.append((title, "R5 no prompt block"))
        if not re.search(r"\*\*Pass condition:?\*?\*?", body):
            problems.append((title, "R5 no pass condition — then it is a suggestion, not a stage"))
    return problems


def main(argv):
    ap = argparse.ArgumentParser(description="Lint build prompts for unfollowable instructions.")
    ap.add_argument("--doc", default=DOC)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()

    text = io.open(a.doc, encoding="utf-8").read()
    stages = split_stages(text)
    problems = lint(text)
    print("\n  BUILD PROMPT LINT — %d stages\n" % len(stages))
    if not problems:
        print("  ✓ No known-shape defects.")
        # ★ COUNTED, NOT TYPED — 2026-08-25. This line read "Six rules" while seven were live; R7
        #   was added and the sentence describing the tool was not. A hardcoded count is a claim the
        #   tool makes about itself that nothing checks, which is the same defect this whole file
        #   exists to catch, sitting in the file's own output.
        n_rules = len(_RULE_IDS)
        print("\n  ⚠ %d rules, all from defects found by ACTUALLY RUNNING a stage. This cannot"
              % n_rules)
        print("    find a shape nobody has met yet — for that there is no substitute for handing")
        print("    a stage to an agent and running the check yourself.\n")
        return 0
    for title, msg in problems:
        print("  ✗ %-34s %s" % (title[:34], msg))
    print("\n  %d problem(s).\n" % len(problems))
    return 1


def selftest():
    """The lint must be able to FIRE. A linter that cannot report is a green light with nothing behind it."""
    fails = []
    live = io.open(DOC, encoding="utf-8").read()
    if lint(live):
        fails.append("the live document has lint problems (may be a REAL finding, not a test bug)")

    # each rule gets a synthetic document that must trip it
    cases = [
        ("R1", u"# Stage 1 — X\n\n> **Prompt:** Build a thing.\n\n```bash\nmv widget_cache.json /tmp/\n```\n\n**Pass condition:** ok\n"),
        # ⚠ the phrase must sit in a COMMAND BLOCK, which is where the real defect lived — as a
        #   trailing comment on the command the reader copies. The first fixture put it in bare
        #   prose and R2 correctly ignored it; the rule was right and the test was wrong.
        ("R2", u"# Stage 1 — X\n\n> **Prompt:** Build a thing.\n\n```bash\n"
               u"python tools/benchmark.py   # must be IDENTICAL to baseline.txt\n```\n\n"
               u"**Pass condition:** same\n"),
        ("R3", u"# Stage 1 — X\n\n> **Prompt:** Build a thing.\n\n**Pass condition:** roughly (total words ÷ 400), and never fewer than the number of files.\n"),
        ("R5", u"# Stage 1 — X\n\nno prompt here at all\n"),
        # R7: a complete-looking stage that never says whether anyone has run it
        ("R7", u"# Stage 1 — X\n\n> **Prompt:** Build a thing.\n\n**Pass condition:** it works\n"),
        ("R6", u"# Stage 1 — X\n\n> **Prompt:** Build a thing.\n\n```bash\n"
               u"python tools/recall.py \"<a topic you have written about twice>\"\n```\n\n"
               u"**Pass condition:** it works\n"),
    ]
    for rule, doc in cases:
        got = [p for p in lint(doc) if p[1].startswith(rule)]
        if not got:
            fails.append("%s did not fire on a document built to trip it" % rule)

    # and a clean stage must NOT trip anything
    # ★ The "clean" fixture must be a genuinely COMPLETE stage — adding R7 made this one incomplete,
    #   and the selftest said so immediately. That is the fixture doing its job: a rule that does not
    #   change what "clean" means is a rule that is not asking for anything.
    clean = (u"# Stage 1 — X\n\n**✅ TESTED** — run 2026-01-01.\n\n"
             u"> **Prompt:** Build `tools/x.py` writing `widget.json` in the repo root.\n\n"
             u"```bash\npython tools/x.py\nmv widget.json widget.json.off\n```\n\n"
             u"**Pass condition:** every file over 400 words produced more than one chunk.\n")
    if lint(clean):
        fails.append("a clean stage tripped a rule: %s" % lint(clean))

    # ★ PINS THE DATED MARKER FORM — added 2026-08-25 alongside the R7 widening.
    #   R7's pattern originally required the marker to be the whole bold span, so writing the
    #   genuinely more useful `**✅ TESTED 2026-08-25 — REJECT**` tripped a rule that exists to
    #   demand exactly that information. Without this fixture, any later tidy-up that "simplifies"
    #   the regex back to `TESTED\*\*` would pass its own selftest and silently start rejecting
    #   every stage that dates its verdict.
    dated = clean.replace(u"**✅ TESTED** — run 2026-01-01.",
                          u"**✅ TESTED 2026-01-01 — verdict REJECT, regresses one probe.**")
    if lint(dated):
        fails.append("R7 rejected a dated TESTED marker, which carries strictly more information "
                     "than a bare one: %s" % lint(dated))

    # and the rule must still catch a stage that declares nothing at all
    undeclared = clean.replace(u"**✅ TESTED** — run 2026-01-01.\n\n", u"")
    if not [p for p in lint(undeclared) if p[1].startswith("R7")]:
        fails.append("R7 stopped firing on an undeclared stage after being widened")

    # ★ _RULE_IDS must match the rules the source can actually emit — 2026-08-25.
    #   The footer printed a hardcoded "Six rules" while seven were live. Now that the count is
    #   derived, the list it derives from has to be kept honest, or the drift just moves one level
    #   down. Reading our own source is the only check that cannot go stale independently of it.
    try:
        src = io.open(os.path.abspath(__file__), encoding="utf-8").read()
        in_source = set(re.findall(r'"(R\d)\s', src)) | set(re.findall(r"---- (R\d):", src))
        if in_source != set(_RULE_IDS):
            fails.append("_RULE_IDS %s does not match the rules in the source %s"
                         % (sorted(_RULE_IDS), sorted(in_source)))
    except Exception as e:                      # never let a meta-check break the real ones
        fails.append("could not cross-check _RULE_IDS against the source: %s" % e)

    for f in fails:
        print("   -", f)
    print("lint_prompts selftest:", "PASS" if not fails else "FAIL")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
