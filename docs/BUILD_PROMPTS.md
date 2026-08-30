# Build prompts — the parts that are not in this repo

This repository ships **one** of the engines in the architecture it comes from: keyword search, plus
the file format and an honest benchmark. This file is how you get the rest built, by handing the
prompts below to a capable coding agent one at a time.

**It is not the same file as `AGENT_INSTRUCTIONS.md`, and they have opposite lifespans:**

| | what it is | where it goes | how long it lives |
|---|---|---|---|
| `AGENT_INSTRUCTIONS.md` | how the agent should **use** memory | its system prompt | permanently |
| `BUILD_PROMPTS.md` (this) | how to **construct** the missing engines | one chat, one stage at a time | discard when built |

---

## ⚠ Read this first — it is the part that makes the rest safe

A prompt saying *"build SPLADE and fuse it with keyword search using RRF"* will produce something.
It will be well-structured, plausibly commented, and **completely unverified** — and if you could
read the code well enough to check it, you would not need the prompt.

That is not a hypothetical failure mode. Every defect found during this repository's own review was
of exactly that kind: reviewed, sensible, never actually run. Correct-looking code that was never
exercised is the *default* output of any builder, human or machine.

So every stage below ends with **an acceptance check you run yourself**, and a stated
pass condition. Three rules:

1. **Do not move to the next stage until the current one passes.** The whole value of the sequence is
   that each stage is verifiable on its own. Build three at once and you have one large unverified
   thing again.
2. **Run the check yourself and read the output.** Not the agent's summary of the output. If you ask
   the thing that built it whether it works, it will say yes, sincerely.
3. **Write some of the probe questions yourself.** If the agent writes the code *and* the exam, the
   exam is circular. Five minutes of your own questions is the single highest-value contribution you
   make to this entire process.

## ⚠ Which of these has actually been run

Every stage below carries a **TESTED** or **NOT TESTED** line. That distinction is not decoration.

**Stages 0-10 have all been executed** — the first eight by handing the prompt, and only
the prompt, to a coding agent with none of the author's context, then running the acceptance check
against whatever it built. **That produced twelve defects, and all but one were in the acceptance
checks rather than the instructions.** Stages 6 and 8 were run later, directly, once it turned out
the models they needed had been on the machine all along; both came back REJECT and both say so on
their own page.

> ⚠ This paragraph read *"Eight stages were executed"* until 2026-08-25, after stages 6 and 8 had
> been run and their pages rewritten. The count in the prose was not updated with the thing it
> counted — the third stale count found in this repo in one evening, alongside a README advertising
> "three small tools" while eight shipped and a linter footer advertising six rules while seven ran.

> ⚠⚠ **AND IT WENT STALE AGAIN THE MOMENT A STAGE WAS ADDED — 2026-08-29.** This paragraph opened
> *"Every stage in this file has now been executed"*, which was true at ten stages and false the
> instant Stage 11 landed. Stage 11 is different in kind: its tools were **built directly and
> measured**, not produced by handing its prompt to a fresh agent, so "executed" would have claimed
> a check that never ran. Now reads "Stages 0-10", which is a bounded statement that a new stage
> cannot silently falsify.
> **Fourth stale count in this repo, and the first one caused by the person who wrote the warning
> about stale counts, seven lines below it.** Prose cannot compute; a total in a sentence is a claim
> nothing verifies. Roles do not drift — totals do.
> The linter's count is now computed from the rule list. Prose cannot compute, so prose should avoid
> counts it does not own.

The reason is worth understanding before you rely on an untested stage. A defect here is the **gap
between what the prompt specifies and what the check assumes.** Both read correctly to the person who
wrote them, because they fill that gap with the same assumption twice. It only becomes visible when
somebody without that context fills it differently.

So: **the prompt gets executed by someone, so its ambiguity produces a visible wrong choice. The
check gets executed by nobody, so its ambiguity produces nothing** — and nothing is indistinguishable
from a check that passed.

**Stages 6 and 8 have now been run too — 2026-08-25 — and both came back REJECT.**

> ⚠ This paragraph said *"Stages 6 and 8 have never been run at all and cannot be here, for want of
> the models."* **Both models were already on the machine when that was written.** The blocker was an
> interpreter without `torch`, not a fleet without models, and a failed import in one environment got
> reported as an absence in all of them. Two stages sat marked untestable for weeks over a virtualenv.
>
> **If you are reading this file to decide what to build, that correction is the most useful thing in
> it.** An untested marker is an honest label, and it is also a place where a comfortable assumption
> can sit indefinitely without anyone paying the cost of checking it. Stage 8 in particular would have
> shipped a recommendation that measurably makes retrieval worse.

Which leaves **Stages 0-10 executed and measured.** Two of them fail. That is a better document than
one where they all pass, because the two failures are the ones with the most confident literature
behind them. **Stage 11 is measured but not prompt-executed** — its tools were built directly, so no
fresh agent has ever been handed its prompt and had the check run against what they produced.

> ⚠⚠⚠ **AND THIS WAS THE SECOND COPY OF THE SAME CLAIM, FOUND 2026-08-29 MINUTES AFTER FIXING THE
> FIRST.** The paragraph 45 lines above said "every stage in this file has now been executed"; I
> corrected it to "Stages 0-10" and walked straight past this sentence, which said the same thing in
> different words. **I fixed the instance I was looking at, not the class.**
> That is the fifth stale count in this repo and the second one I caused tonight — and the lesson is
> narrower than "be careful": after correcting a claim, GREP FOR ITS SIBLINGS. A statement worth
> making once tends to have been made twice, and the copy you did not edit is the one that stays
> wrong, because you now believe you have handled it.

## Why this order

**Not the diagram's numbering.** The diagram is arranged for reading; this is arranged by *what can
be tested when*. A stage whose correctness cannot be demonstrated yet is a stage you are taking on
faith, which is the thing being avoided.

```
0.  baseline            measure the keyword engine BEFORE changing anything
1.  index               a persistent index that matches a live filesystem walk exactly
2.  chunking            split long files; must not lose or duplicate a single word
3.  keyize              query reduction; must not lose a probe the baseline could answer
4.  fusion (RRF)        merge two rankings; only meaningful once there are two
5.  outcome gate        strong / ambiguous / nothing — the three-outcome decision
--- everything below needs a model and breaks "no dependencies" ---
6.  SPLADE              sparse expansion -- the bridge you can READ
7.  embeddings          the dense semantic tier
8.  cross-encoder       rerank the shortlist
9.  fuzzy topic fallback  last resort when every engine returns nothing usable
--- and two that are not retrieval at all ---
10. lifecycle           supersede / reinforce / report stale. Handles memories that are WRONG.
11. candidate queue     the WRITE side: what is worth remembering. Ships working; classifier is weak.
```

> ⚠ **SIXTH stale count, and the first one found on purpose — 2026-08-29.** This listing stopped at
> 10 and the header said "and one that is not retrieval at all" while two now are. I found it by
> running the sibling grep I had written into this file twenty minutes earlier, after correcting the
> same claim twice in two places. **The rule worked on its first real use**, which is the only
> evidence that matters for a rule: *after correcting a claim, go looking for its copies.*

Stages 1–5 are pure Python, no dependencies, and they are most of the value. **Stop after 5 if you
like** — you will have a substantially better system and nothing to install.

---

# Stage 0 — Baseline (do not skip)

**✅ TESTED** — executed 2026-08-25; found 1 defect (it manufactured a red failure on a first-time user's first command).

**First, write ten questions of your own.** You cannot skip this and you should not delegate it. Pick
ten things you are certain are in your notes, and phrase each the way you would ask months later —
*not* using the words that are in the file. Save them in the shape of `sample/probes.json`.

Ten questions is about five minutes and it is the highest-value thing you contribute to this entire
process, because **if your agent writes the code and the exam, the exam is circular.**

> **Prompt:** Do not write any code. Run
> `python tools/benchmark.py --verify --root <my memory folder> --probes <my probes file>` and
> `python tools/benchmark.py --overlap`, and save both outputs verbatim to `baseline.txt`. Report the
> numbers to me without interpretation.

**Acceptance:** `baseline.txt` exists and contains a VERDICT line.

**Pass condition:** the file is non-empty and contains a VERDICT line. (Stated explicitly because
every other stage has one, and a stage whose success criterion is phrased differently from its
neighbours is a stage people skim.)

⚠ Later stages compare against this file. Compare **the verdict line and the numbers**, never the
whole file byte-for-byte — console encoding alone can make two identical results look different.

⚠ **If you run `--verify` on your own notes with the shipped example probes, it will refuse** — the
example questions name files in `sample/`, and scoring them against your corpus would print a red
`0 of 10` that means nothing. That refusal is the tool working. (This paragraph exists because the
first draft of this document told you to do exactly that, and produced a manufactured failure on a
first-time user's very first command.)

**Why it is stage 0.** Every later stage claims an improvement. Without a number from before, "it is
better now" is an opinion. This costs two minutes and is the only thing that makes every stage claiming
an improvement falsifiable. (Written without stage numbers on purpose — inserting SPLADE renumbered
four of them, and a cross-reference by number is a stale doc waiting to happen.)

---

# Stage 1 — A persistent index

**✅ TESTED** — built by an agent from this prompt 2026-08-25; the code was correct, the acceptance check had **3 defects**.

> **Prompt:** Build `tools/index.py`. It walks the memory folder and writes a single index file at
> **exactly `memory_index.json` in the repository root** — that literal name, not hidden, not inside
> the memory folder, because a person has to be able to see it and delete it. It contains, for every
> `.md` file: path, modification time, size, the parsed `name` and `description`, and a term→count
> map of the body. Provide `build`, `update` (only re-reads files whose mtime or size changed) and
> `stats` commands. Write the index atomically — to a temp file in the same directory, then
> `os.replace` — and never partially overwrite the live file.
>
> **Then modify `tools/recall.py` to use the index when it is present and fall back to walking the
> filesystem when it is absent.** The fallback must remain fully working; the index is an
> optimisation, not a dependency.
>
> Add a `--selftest` that proves the fallback still works by running a query with the index deleted.

**Acceptance — run this yourself:**

```bash
python tools/index.py build
python tools/benchmark.py --verify        # note the VERDICT and the numbers
mv memory_index.json memory_index.json.off      # rename it; on Windows: ren
python tools/benchmark.py --verify        # must give the SAME verdict and numbers
```

**Pass condition:** the **verdict line and the counts** are the same with the index and without it.
**An index that changes your results has a bug, not a feature** — it is supposed to make the same
answer faster, and any difference means the two paths disagree about your corpus.

⚠ **Compare the verdict and the numbers, NOT the two files byte-for-byte.** Every one of these
defects was found by running this stage rather than re-reading it:

* The first draft told you to `mv memory_index.json` — but the prompt never said where to put the
  index, so the agent that built it chose `memory/.memory-index.json`: different name, different
  folder, and **hidden**. You would have got "no such file" and had no way to know why. The prompt
  now names the path exactly, and forbids hiding it.
* A byte-for-byte file comparison **fails on text encoding alone**. Measured: the same output
  captured two different ways on Windows differed only in the em-dash and bullet characters —
  identical as ASCII, different as bytes. A pass condition that goes red because of a dash is a
  pass condition you will learn to ignore.

⚠ **The specific thing that will go wrong:** the index goes stale and nobody notices, because a stale
index returns *plausible* results. Ask for `update` to be run automatically at the start of every
query, and ask the agent to show you the timing. If it is slow enough to be annoying, that is a real
tradeoff to discuss — not a reason to skip freshness.

---

# Stage 2 — Chunking

**✅ TESTED** — code correct; **2 defects** in this stage's own wording.

> **Prompt:** Build `tools/chunk.py`, splitting **`.md` files only** — matching the rest of the
> system, which indexes `.md` and nothing else — at natural boundaries: headers first, then
> paragraphs, never mid-sentence, into chunks of roughly 400 words. Each chunk records its
> source path, its position, and the heading it fell under. Short files produce exactly one chunk.
>
> **Critical:** chunking must be lossless. Concatenating a file's chunks in order must reproduce its
> full text, ignoring whitespace differences. Write a `--selftest` that asserts exactly this over
> every file in `sample/`, and make the assertion compare word sequences rather than a checksum, so
> the failure message shows WHICH words were lost.

**Acceptance:**

```bash
python tools/chunk.py --selftest
python tools/chunk.py --stats <your memory folder>
```

**Pass condition:** the selftest passes, and **every file over ~400 words produced more than one
chunk, while every file under it produced exactly one.** Check that per file, not in aggregate.

⚠ **The first version of this pass condition was self-contradictory, and running the stage is what
exposed it.** It said the chunk count should be *"roughly (total words ÷ 400), and never fewer than
the number of files."* Measured on the shipped sample: 23 files, 4,331 words. Criterion one says
~11 chunks. Criterion two says at least 23. **Both cannot hold**, and a reader computing 11, seeing
25, has no way to tell a pass from a failure.

★ The mistake is worth naming because it is not arithmetic. **I wrote a check that assumed a corpus
of a few large documents, for a system whose entire format guidance is "one fact per file, short
precise notes, split when it grows past a screen."** My own rules guarantee many small files, and my
own check assumed the opposite. A per-file condition is correct at any corpus shape; an aggregate
one silently encodes an assumption about shape that nothing states.

If a 20,000-word journal produced 1 chunk, splitting failed silently and everything downstream
inherits it — which is what the per-file form actually catches.

⚠ **The specific thing that will go wrong:** losing text at boundaries. It is invisible in every
downstream test — retrieval still works, just slightly worse forever, and you would never trace it
back here. That is why the loss check is in this stage and not later.

---

# Stage 3 — Keyize (query reduction)

**✅ TESTED** — **2 defects, one of them in the prompt itself**, and the acceptance check passed a component that did not work.

> **Prompt:** Build `tools/keyize.py`, which strips a natural-language query down to its most
> distinctive terms. Rank terms by document frequency computed from my actual corpus — what is
> common depends on what I write about — but **combine that with a small universal stopword list as a
> FLOOR: a function word is never kept, however rare it happens to be in my corpus.**
>
> It must be **deterministic** (same query, same corpus, same output every time), must return the
> original query unchanged if reduction would leave fewer than two terms, and must **refuse to reduce
> at all if the corpus has fewer than ~200 documents**, printing why. Below that size document
> frequency is noise.
>
> Wire it in as an *additional* retrieval path, not a replacement: the original query is still run.

**Acceptance — look at what keyize OUTPUTS, then at the score:**

```bash
python tools/keyize.py "clients hammering a service while it was trying to come back up"
python tools/benchmark.py --verify
```

**Pass condition, and the first one is the one that matters:**

1. **The reduced query keeps the CONTENT words and drops the function words.** For the example
   above, something like `clients hammering service` — *not* `while it`. Read the output. If the
   words it kept are ones you would never search with, it is broken regardless of the score.
2. Section 1's verdict and counts have not regressed from the baseline.

⚠⚠ **BOTH OF THESE EXISTED BECAUSE RUNNING THE STAGE EXPOSED THEM, AND THE SECOND IS THE WORSE
ONE.**

**The prompt was wrong.** It said to use document frequency and *forbade* a stopword list, reasoning
that what is common depends on what you write about. That is true at eleven thousand documents and
actively harmful at twenty: measured on the shipped sample, `while` appears in **1 of 20** files and
`it` in **17 of 20**, so a pure-DF ranker keeps `while` and discards `it` — and the query *"clients
hammering a service while it was trying to come back up"* reduced to **`while it`**. Exactly
inverted. The instruction was correct for the corpus I was thinking of and wrong for the corpus this
template ships with.

**And the old pass condition could not see it.** It only asked that no question be *lost*. Keyize is
wired as an ADDITIONAL path, so the original query still runs and still carries the result — meaning
**a keyize that emits pure garbage scores identically to one that works.** The check passed a
component that was completely broken, because a no-op and a success are indistinguishable when the
thing you measure is downstream of both.

★ The general form is worth more than this stage: **a "did not get worse" condition cannot tell
working from not-running.** If a component is added alongside an existing path rather than replacing
it, the end-to-end number will not move when it fails. Check the component's own output.

⚠ **This is the stage most likely to quietly make things worse.** Discarding words is a lossy
operation, and a query reduced too aggressively stops matching the file it was about. The
never-fewer-than-two rule and the keep-the-original rule both exist for that; make sure both are
actually implemented and not just mentioned in a comment.

---

# Stage 4 — Fusion

**✅ TESTED** — code correct and arithmetic verified by hand; **1 defect** (an acceptance step that could not fail).

> **Prompt:** Build `tools/fuse.py` implementing Reciprocal Rank Fusion over two or more ranked
> result lists: `score(doc) = Σ 1/(k + rank(doc))` with `k=60`, summed across every list the document
> appears in. Documents absent from a list simply contribute nothing.
>
> Include a `--selftest` proving two properties: **(a)** a document ranked #1 by every engine stays
> #1 after fusion, and **(b)** a document ranked mid-table by *all* engines beats one ranked #1 by a
> single engine and absent from the rest. Property (b) is the entire point of fusion — if your
> implementation fails it, it is not doing anything.

**Acceptance:**

```bash
python tools/fuse.py --selftest
```

**Pass condition:** the selftest passes **both** properties — and check property (b) yourself rather
than trusting the message, because it is the whole point:

```
engine 1:  A  x  y  z  B          A is #1 in one list and absent from the others
engine 2:  p  q  r  s  B          B is 5th in all three
engine 3:  m  n  o  t  B
```

By hand: `A = 1/(60+1) = 0.0164`, `B = 3 × 1/(60+5) = 0.0462`. **B must come first.** If it does
not, the implementation is summing wrong or ignoring lists a document is absent from.

⚠ **The first version of this check also ran `benchmark.py --verify` — and that step could not fail
because of this stage.** Nothing here wires `fuse.py` into retrieval; it is a standalone module
until a second engine exists to fuse with. So the benchmark would have printed the same green
before and after, and a reader would have taken it as evidence about fusion.

★ That is a different defect from the one in stage 3, and worth separating. There, the useless step
*hid a genuinely broken component*. Here it hides nothing — it is padding that makes the check look
more thorough than it is. **Both are steps that cannot fail; only one of them was covering for
something.** A check made of two parts, one of which is inert, is a check you will trust more than
it deserves.

⚠ Property (b) is the one to check personally. A fusion that only satisfies (a) is an expensive
`max()`, and it will look completely fine in every end-to-end test.

---

# Stage 5 — The three-outcome gate

**✅ TESTED** — code correct; **1 defect** (the check demanded a corpus property the reader may not have).

> **Prompt:** Add a confidence gate to `recall.py` returning one of exactly three outcomes:
>
> * `STRONG` — one clear winner. The top result's score is at least twice the second's.
> * `AMBIGUOUS` — several plausible candidates with no clear leader.
> * `NOTHING` — no result shares even one content word with the query.
>
> The thresholds must be **constants at the top of the file with a comment recording what they were
> measured against**, not values buried in an expression.
>
> **And they must ship UNSET, with a fourth outcome: `UNCALIBRATED`.** Until someone has run the
> calibration on *their own* corpus, the gate must refuse to rule rather than rule with a borrowed
> number. A threshold is a measurement of one corpus; on a different one it is not a default, it is
> a wrong answer wearing a config value.

⚠ **This requirement was added 2026-08-29 because the author nearly shipped the opposite.** My gate
carries `MARGIN_MIN = 0.045` — a real figure, calibrated twice, on two different engines of *my*
system. It is meaningless on yours, and a fresh install would have inherited it silently and produced
confident verdicts from the first query. The failure would look exactly like a working gate.

★ The point is not caution about numbers. It is that a system which cannot tell must **say so**, and
`UNCALIBRATED` is a cheaper, truer output than a verdict computed from someone else's corpus. Every
other guard in this repo already works that way; the gate is the one where a borrowed constant is
invisible, because it produces a plausible answer instead of an error.

**Acceptance:**

**First make the ambiguous case exist**, because your corpus probably has no clear one and you
cannot test an outcome you cannot trigger:

```bash
mkdir amb_test
printf -- '---\nname: alpha\ndescription: connection pooling exhausted under load\n---\n\nconnection pooling exhausted under load\n' > amb_test/alpha.md
printf -- '---\nname: beta\ndescription: connection pooling exhausted under load\n---\n\nconnection pooling exhausted under load\n' > amb_test/beta.md
```

Then all three outcomes, each of which can actually be produced:

```bash
python tools/recall.py --root amb_test "connection pooling exhausted"   # expect AMBIGUOUS
python tools/recall.py "photolithography wafer yield"                   # expect NOTHING
python tools/recall.py "<a question you know your notes answer>"        # expect STRONG
```

**Pass condition:** AMBIGUOUS and NOTHING must appear exactly as above — those two are fully
determined by the commands given. STRONG needs one question of your own, because only you know what
your notes contain.

⚠ **The first version of this check could not be run, and running the stage is what showed it.** It
said *"a topic you have written about twice"* — a property of a corpus the reader may not have built
yet. Against the shipped examples it returns STRONG, and **there is no way to tell whether the gate
is broken or the corpus simply has no ambiguous pair.** That is the same disease this whole project
is about: cannot-tell presented as measured.

★ The gate itself was correct. Verified separately by constructing two identically-scoring files,
which produced AMBIGUOUS immediately. **The outcome was reachable; my instructions for reaching it
were not.**

**Why this stage matters more than it looks.** `NOTHING` is a real answer and most systems will not
say it. This is the stage that stops your agent inventing a plausible memory, and a confident false
recall is worse than no recall — it cannot be distinguished from a true one. Pair it with the
`AGENT_INSTRUCTIONS.md` rules about what to do with each outcome, or the gate computes a verdict that
nothing acts on.

## ★ Built this stage for real, 2026-08-29 — four findings that change how you should write it

The prompt above is sound. These are the things it does not warn you about, each of which cost a
rewrite.

**1. Do not gate on an absolute score. It cannot work, and you can measure that in ten minutes.**
On a real corpus a correct hit scored **0.727** while junk scored **0.693** and **0.719** — the
answer sat *inside* the noise band. Any `score > T` gate is a coin toss wearing a number. What
separates them is **rarity**: the same query's distinctive terms appear in 0.2% of files against
18.6% for the junk. Rarity is counting, not similarity, and it needs no model.

**2. The usable signal is the MARGIN between rank 1 and rank 2, because it is relative.**
An absolute cosine is uncalibrated across queries. The gap between two hits *of the same query* is
not — whatever offset makes one query score high cancels when you subtract two of its own results.
A margin is comparable within a query; a threshold is not.

**3. A FLAT MARGIN MEANS ABSENCE, NOT AMBIGUITY — and I shipped that branch backwards first.**
The obvious reading of "top two nearly tied" is *several plausible answers*. It is not. Measured over
60 real queries the median margin was 0.006, which would have called 38 of 43 "ambiguous". I checked
what those ties actually were: **unrelated documents**, tied because *nothing matched*. A reading
journal about Bacon and a memory-system writeup, 0.0013 apart. Genuine hits carried fat margins
(0.085, 0.027).
> So: near-tie → **ABSENT**. Reporting it as "several plausible" dresses a failed lookup as a rich
> one and asks the user to choose between two things, neither of which is the answer.

**4. CLARIFY must be a POSITIVE case, never the residual.**
Make it require *near-tied **and** both hits independently strong*. If it is simply "whatever was not
INJECT or ABSENT", it becomes a junk drawer that catches every failed lookup — measured, that was 38
of 43 messages. A middle outcome defined by exclusion will always be the most common one.

⚠ **Calibrate per PATH, not once.** The same gate ran on two engines here — a single-pass embedder
and a unioned+reranked list — and their margin distributions differ (median 0.006 vs 0.016). The
number transferred, but only because it was *checked* on both; assuming it would have been the same
mistake as shipping a threshold measured at five terms into code that queries seven.

---

# ⚠ Everything below requires a model

Stages 6–8 break the "plain Python, no dependencies" property. Before starting them, be clear that
you are accepting a model download (hundreds of MB), a slower first run, and a component that can
fail for reasons unrelated to your code.

**Every one of them must degrade gracefully.** If the model is missing or fails to load, the system
falls back to stages 1–5 and says so out loud. It must never fail closed, and it must never silently
return worse results while appearing to work.

## ★ A CHOICE FOR YOU, NOT A DECISION I MADE: should the gate and fallback ship as code?

Working implementations of Stage 5 and Stage 9 exist in the author's own system. They are not copied
into `tools/` **by default**, and here is the trade so you can decide rather than inherit my taste.

> ⚠ This section first read *"DECISION: they stay STAGES"*, with the reasoning below presented as
> settled. That was wrong for a template, and the repo's owner said so: it is a **choice**, and the
> right answer depends on hardware I do not have and cannot see. My reasoning is sound for someone
> with no GPU and wrong for someone with a spare card who would rather have the code.
> **A template that decides for you is a framework**, and frameworks are how you end up fighting
> somebody else's preferences. So the facts stay; the verdict is removed.

**Ask the user before building Stages 6-9. Suggested prompt for your agent:**

> *"Stages 6-9 add an embedding index and a model dependency: a few hundred MB of download, a slower
> first run, and components that can fail for reasons unrelated to your code. Stopping at Stage 5
> gives you plain Python, nothing installed, and most of the value. Which do you want? Both are
> supported and neither is the default."*

**The cost of building them:**

- They depend on a persistent embedding index and an inbound-consult layer — Stages 1 and 7 — which
  this repo does not ship. A copy would import modules that are not here.
- Porting them properly means porting a minimal embedder too, and then **`tools/` no longer runs on
  a laptop with no GPU.** The repo's whole first-page promise is that Stages 1–5 are plain Python
  with nothing to install. Trading that away to ship two more files is a bad exchange.
- What *does* travel is the part that is hard to rediscover: the four measured findings now attached
  to Stage 5, and the Stage 9 warning about firing at the moment confidence is lowest. Those are
  worth more than the code, because the code is fifty lines and the findings cost a day.

⚠ **The one exception is already portable and worth copying if you build Stage 5:** make the
*decision* a pure function taking a ranked list, separate from the *fetch*. The author's version
splits `gate()` (fetches, then decides) from `decide()` (rules on hits you already hold). That split
was made for cost — callers already holding results should not pay a second index pass — and it is
what let the decision survive a move between codebases at all. A gate welded to its own retrieval is
a gate nobody else can reuse.

# Stage 6 — SPLADE (learned sparse expansion)

**✅ TESTED 2026-08-25 — and the honest verdict is REJECT on the author's corpus.**

> ⚠⚠ **LICENSING, AND IT IS A SECOND INDEPENDENT REASON TO SKIP THIS STAGE.** The NAVER SPLADE
> project releases its work under **CC BY-NC-SA 4.0** — *non-commercial* and *share-alike*. That is
> not a detail: non-commercial rules it out of any commercial product regardless of how it benchmarks,
> and share-alike is viral in a way MIT and Apache are not. Verified upstream 2026-08-30.
>
> Every other optional model named in this repo is more permissive, and the two BGE models
> (`BAAI/bge-m3`, `BAAI/bge-reranker-base`) are MIT. **If you want a learned tier, start there.**
>
> The measured verdict below was reached before anyone looked at the licence. They agree, which is
> convenient — but they are separate findings and either alone is sufficient.

> ⚠ This line read *"NOT TESTED — cannot be, here. No SPLADE model exists on this machine or anywhere
> on the fleet"* until 2026-08-25. **That was false when it was written.**
> `naver/splade-cocondenser-ensembledistil` (876.9 MB) was already in the local HuggingFace cache, and
> a bakeoff harness had already been written against it. The only thing missing was an interpreter
> with `torch` — the voice virtualenv had one the whole time, because the local TTS model requires it.
> A failed `import` in one environment had been promoted into a claim about an entire fleet.

Measured against the same 14 probes as the other stages, over a 26,260-chunk corpus (3.6 min to build
the index on one consumer GPU):

| engine | found | vs baseline |
|---|---|---|
| keyword + fusion baseline | 7/14 | — |
| **SPLADE** | **10/14 (71.4%)** | **+3** |

**It still fails AS A FUSION MEMBER, and the failure is the point.** Gate (a) passes — 10 beats 7.
Gate (b) fails — SPLADE loses one probe the baseline answered. **A net gain is not a strict gain.**

> ★★★★★ **BUT THE VERDICT IS ABOUT PLACEMENT, NOT ABOUT SPLADE — added 2026-08-30 after someone
> asked why the author's own system runs the engine this stage rejects.** It does. The difference is
> where.
>
> Fused in as another ranked list, SPLADE can outrank a correct baseline hit and lose it. That is the
> measured failure above. **Used as an ESCALATION — run only when the base verdict comes back WEAK —
> it is structurally incapable of that failure**, because when the baseline already answered, SPLADE
> never executes. You keep the +3 on the queries that were failing and risk nothing on the queries
> that were not.
>
> Same model, same corpus, same 14 probes. Opposite verdict. The variable is pipeline position, and
> nothing in the original measurement distinguished the two — it tested one arrangement and I wrote
> the conclusion as though it were about the engine.
>
> ⚠ THIS DOES NOT SOFTEN THE LICENCE. CC BY-NC-SA 4.0 rules SPLADE out of commercial use no matter
> how well it places. Good numbers arriving after a hard blocker is exactly when a blocker gets
> quietly downgraded, so: the licence is a separate gate and it fails independently. An engine that
finds more on average while silently dropping a query you could previously answer will fail you on
the one that mattered, and you will discover this at the worst possible moment. Re-run it on your own
corpus if you like the numbers, but re-run it against *both* gates.

> **Prompt:** Add a sparse-expansion engine. For every chunk, run a SPLADE-style model to produce a
> weighted term vector that includes terms the chunk does NOT literally contain but is about, and
> store it beside the index. At query time expand the query the same way and score by weighted term
> overlap. Feed the result into the stage 4 fusion as an additional ranked list — **do not replace the
> keyword engine.** If the model cannot be loaded, log one line and continue with the lexical
> engines.

**Acceptance:** open `baseline.txt` and find the questions under *"Where does it stop"* — the ones
sharing no vocabulary with their answer.

**Pass condition: some of those specific questions now find their answer.** SPLADE's entire purpose is
bridging vocabulary gaps, so those are the only queries that can demonstrate it is doing anything. An
improved average with those unchanged means it is running and not working.

Then delete the model cache and re-run `--verify`: it must still pass on the lexical engines alone.

⚠ **Why this stage is separate from embeddings, and worth doing first.** Sparse expansion produces
terms you can READ. When it goes wrong you can see exactly which words it invented, which makes it
debuggable in a way a dense vector never is. Dense embeddings fail silently and opaquely — build the
tier you can inspect before the tier you cannot.

# Stage 7 — Embeddings

**✅ TESTED** — run against a live `nomic-embed-text`. Degradation verified; **rescued 1 of 3 boundary probes**, against 4 of 4 for the free description fix. See the measurement below before you install anything.

> **Prompt:** Add a semantic tier: embed every chunk with a local sentence-embedding model, store the
> vectors beside the index, and add cosine-similarity retrieval as an additional engine feeding the
> fusion from stage 4. Re-embed only chunks whose content hash changed. **If the model cannot be
> loaded, log one clear line and continue with the lexical engines** — never raise.

**Acceptance:** open `baseline.txt` and find the questions listed under *"Where does it stop"* — the
boundary cases that share no vocabulary with their answer.

**Pass condition: at least one of those questions now finds its answer, and none of them regress.**
Not "the average improved" — those exact ones. They are the only reason to add this tier.

⚠ **MEASURED HERE, so you can decide before paying for it.** Run against the shipped mixed corpus
with `nomic-embed-text`:

```
rescued 1 of 3 boundary probes

  HIT   "it wiped things it was told to leave alone and then signed off pleasantly"
        -> assistant-message-deleted-everything          (returned NOTHING lexically)
  miss  "buttering up the model before handing it a task"
        -> returned the wrong file, confidently
  miss  "it was built and working and still nobody reached for it"
        -> returned nothing
```

★★★ **Now compare that against the free fix.** Adding the searcher's vocabulary to those same
files' `description` lines — no model, no download, no runtime cost — rescued **4 of 4**
(`docs/FORMAT.md`). A few hundred megabytes and a network dependency rescued **1 of 3**.

**So do the free thing first, and only then decide whether this tier earns its place.** The one it
did rescue is the hardest case in the set — the query that returned literally nothing under lexical
search — which is exactly where a semantic tier should win. That is a real capability and it is a
narrower one than "embeddings fix retrieval".

⚠ The second miss is the one to look at closely: it returned the **wrong file with confidence**,
where the lexical engine returned nothing. **A semantic tier converts "no answer" into "a plausible
wrong answer,"** and those are not equally safe. Pair it with the stage 5 confidence gate or it will
quietly start inventing.

Then: `mv` the model cache aside and re-run `--verify`. It must still pass on the lexical engines
alone.

# Stage 8 — Cross-encoder rerank

**✅ TESTED 2026-08-25 — REJECT, and this is the single most important measurement in this file.**

> ⚠ This line read *"NOT TESTED — cannot be, here. No reranker model on the fleet."* until
> 2026-08-25. **Also false.** `BAAI/bge-reranker-base` (1,134.4 MB) was already cached locally.

Same 14 probes, same corpus, cross-encoder applied to the top candidates from stage 6:

| engine | found |
|---|---|
| keyword + fusion baseline | 7/14 |
| SPLADE alone | **10/14** |
| **SPLADE + cross-encoder rerank** | **6/14 (42.9%)** |

**Read that again. Adding the reranker took retrieval from 10/14 down to 6/14.** It is not neutral
and it is not a marginal loss — it destroyed four results the previous stage had already found
correctly, regressed five probes against the plain baseline, and finished *below the baseline it was
supposed to improve*.

### ★ Why this matters more than any passing stage here

A cross-encoder rerank is the standard final stage in essentially every retrieval write-up you will
read, and the published numbers are real. **They were measured on a different kind of corpus.**
`bge-reranker-base` is trained to judge whether a web passage answers a question. A personal memory
corpus is somebody writing about their own systems, decisions and mistakes — the relevance relation
is not the same one, and the model is confidently wrong rather than uncertain.

**Had this stage kept its NOT TESTED marker, it would have shipped on the strength of the literature**
— a recommended final stage that makes retrieval worse, with a citation attached. That is precisely
what an untested marker permits, which is why every stage in this file carries one.

**Do not adopt this stage because a paper says so. Run it against your own probes and both gates.**
If your corpus looks like web QA, it may well help you. If it looks like a memory, expect this.

> **Prompt:** Rerank only the top ~20 fused candidates with a cross-encoder, scoring each
> (query, chunk) pair jointly. Never run it over the whole corpus. Same graceful-degradation rule.

**Acceptance:** `--verify` before and after. **Pass condition:** section 1's hit@1 improves *or* stays
equal, and nothing that was found becomes unfound. Also time it — if reranking costs more than about
a second per query, you will stop using the system, and an unused system scores zero regardless of
its retrieval quality.

# Stage 9 — Fuzzy topic fallback

**✅ TESTED** — built 2026-08-25 by a **local 14B model** (codex was rate-limited), deliberately: a
weaker builder guesses more, and every defect found in this document has been ambiguity. It produced
**5 defects, 2 of them mine.** See below.

**⚠ REQUIRES STAGE 7.** This imports the semantic module stage 7 builds. Attempting it first gives
`ModuleNotFoundError` with nothing to explain it — which is exactly what happened when I ran it.

> **Prompt:** When every engine returns nothing usable, extract the *topic* of the query and run a
> broad semantic search on the topic instead of the literal question. Results from this path must be
> **labelled as low-confidence** everywhere they surface, and must never be presented as a direct
> answer.

**Acceptance — check the TOPIC EXTRACTION first, because that is the whole stage:**

```bash
python tools/fallback.py --show-topic "what did we decide about the retry backoff window"
```

**Pass condition, in this order:**

1. **It prints an extracted topic that differs from the query** — something like `retry backoff`.
   If the "topic" is just the query again, no topic extraction was built and the stage is not done,
   whatever else it returns.
2. Asking something *adjacent to your notes but not in them* gives clearly-labelled loose matches,
   **or nothing**.
3. It never returns a confident direct answer. If it does it has become a fabrication engine, which
   is the failure the rest of this document exists to prevent — turn it off rather than ship it.

⚠⚠ **THE FIRST CHECK EXISTS BECAUSE THE ORIGINAL PASS CONDITION COULD NOT FAIL.** It accepted
*"loose matches **or nothing**"* — so an implementation that does nothing at all passes. That is not
hypothetical: the 14B built a module with **no topic extraction whatsoever**, running semantic search
on the literal query, and my check would have waved it through on the "or nothing" branch.

★ Third instance of this exact shape in one document (stage 3's keyize, stage 4's inert benchmark
step, this). **A pass condition whose accepted outcomes include "nothing happened" cannot distinguish
working from not-running.** When a stage's whole value is a transformation, check the transformation,
not the downstream result.

★ The other defects the weaker builder surfaced, all worth knowing: it guarded `ImportError` when an
unreachable embedding host raises a **network** error, so "never raise" was unsatisfied; its selftest
printed and asserted nothing; and it used an import form that does not match this layout. **A 14B
guesses more than a frontier model, which is precisely why it is the better instrument for finding
ambiguity.**

---

---

# Stage 10 — Lifecycle: reinforce, supersede, archive

**✅ TESTED** — code correct; **2 defects**, and this stage's pass condition is the first one in the file that caught a real problem on its own.

Everything above makes memories findable. **Nothing above deals with memories that are WRONG**, and a
confidently-worded stale note is the most dangerous file in the system — retrieval works, the agent
trusts what it retrieves, and a wrong memory does not degrade gracefully. It *outranks* fresh
reasoning.

> **Prompt:** Add `tools/lifecycle.py` with three commands:
>
> * `supersede <old-name> <new-name>` — takes memory NAMES (the `name:` slug, not a path). Writes a
>   link into the old note marking it replaced, and a back-link in the new one. **Never deletes.**
>   The old note stays retrievable, and **the marker must appear in the note's `description`, not
>   only in an HTML comment** — a marker retrieval does not surface is a marker nobody reads.
> * `reinforce <name>` — records that a memory was retrieved AND used. Retrieval alone is not use;
>   the agent must say so explicitly.
> * `stale [--days N]` — lists notes never reinforced, oldest first. **Reports only. It must not
>   delete anything, ever.**

**Acceptance:**

```bash
python tools/lifecycle.py supersede example-empty-is-not-clean example-measure-before-optimising
python tools/recall.py --root memory "empty is not the same as clean"
```

**Pass condition:** the old note still appears in the results **and the result line itself says it
was superseded**, naming the replacement. If it vanished, the tool deleted history. If it appears
looking exactly as before, the supersession did nothing you will ever see.

⚠ **Both halves of this were caught by running it.**

* The command takes a **name**, not a path — and the first version of this check passed a path and
  got `memory note not found` for a file that plainly existed. The prompt had not said which, so the
  builder chose, and my check chose differently. (Same defect as stage 1's index path. Twice now:
  **if the prompt does not name the argument form, the check may not assume one.**)
* The marker was written as an HTML comment. The note still ranked first, with its original
  description, and **nothing in the retrieval output mentioned the supersession at all.** It passed
  "still appears" and failed "visibly announces" — which is why the pass condition names both. A
  status buried where the reader never looks is a guard parked off the path.

⚠⚠ **`stale` must never gain a `--delete` flag, and this is not squeamishness.** Any pruning rule
whose selector is "oldest" or "least used" is safe only while the folder stays homogeneous, and
nothing ever re-checks that. A rule like that, in a real memory folder, eventually selects the one
irreplaceable file that simply was not queried this month. **Report, and let a person choose.**

★ The `reinforce` half is what makes `stale` mean anything, and it is also the part that needs
`AGENT_INSTRUCTIONS.md`: an agent that never records a use makes every note look unused, and then
"stale" is just a list of everything you own.

---

# Stage 11 — The candidate queue, and a classifier that does NOT work well

**TESTED — AND IT UNDERPERFORMED. The numbers are below and they are the point of this stage.**

Two shipped tools cover this stage: `tools/memory_candidates.py` and `tools/candidate_classify.py`.
Both run standalone (6/6 and 4/4 selftests, no dependency on the rest of the stack). You do not need
the prompt to build them — you need this page to know what they are worth.

> **Prompt:** Add a write-side staging queue, `tools/memory_candidates.py`, with three functions:
> `capture(text, why, ...)` appending one JSON object per line; `touch(id)` incrementing a
> `retrieved` counter and rewriting the file atomically; `review()` returning two piles — candidates
> that have been retrieved at least once, and those that never have.
> `capture()` must **raise** if `why` is empty. Nothing in the module may import a memory writer:
> promotion from candidate to memory is a separate, human decision.
> Then add `tools/candidate_classify.py`, which classifies a message MEMORY_CANDIDATE or
> CURRENT_CONTEXT by embedding it and taking the **nearest of a handful of labelled example
> sentences** — not by prompting a chat model. The nearest example must be returned and used as the
> `why`.

**Pass condition:** all four must hold.

1. `python tools/memory_candidates.py --selftest` passes, and `capture("x", "")` raises.
2. Adding the same text twice yields one row, not two.
3. `python tools/candidate_classify.py --selftest` passes with the embedder **stubbed** — the suite
   must not need a model running, or it goes red for reasons unrelated to this stage.
4. With the embedder made to raise, `run()` returns `ERROR` rows. **A dead model must not be
   reported as CURRENT_CONTEXT** — that silently discards every memory-worthy line while looking
   like a working classifier. (This defect was real: the example-embedding call sat outside the
   guard, and the failure test caught it on first execution.)

⚠ **The tools ship, so you can skip the prompt.** They are in `tools/`. The pass condition is not
optional though — run it against whatever you have, because a file that copies is not a file that
works, and the two are indistinguishable until you execute one.

## The problem this solves, and why the obvious design is wrong

Everything before this stage is the READ side. The write side — deciding what is worth remembering —
is the half most projects skip, and for a defensible reason: **the write path is the only place where
a mistake is permanent.** A wrong classification becomes a memory file that is then retrieved and
believed for months.

The fix is not a better classifier. It is a **queue**:

    message -> classifier -> rolling candidate file -> (a human promotes, or nothing does)

A candidate is not a memory. Queues can be wrong cheaply. This does not make the classifier more
accurate; it makes being wrong **reversible**, which is a different and better property.

★ **And the queue updates on RETRIEVAL as well as write.** A candidate nobody ever pulls is evidence
it was not worth keeping. That is *usage* as the filter rather than confidence at write time — which
matters because on this corpus confidence provably cannot do the job: a real hit scored **0.727**
while junk scored **0.693** and **0.719**. The answer sat inside the noise band. Use is not a score,
and nothing has to be thresholded.

## What was measured, honestly

`candidate_classify.py` uses an embedder (`embeddinggemma:300m`) as a **kNN classifier** over eight
labelled sentences, not a chat model with a prompt. That choice was measured too: prompting a chat
model scored **0/8 zero-shot and 4/8 few-shot** on llama3.2, and gemma4:12b returned an **empty
string**. Both zeros were the harness, not the models — zero-shot was run where the spec said
few-shot, and an empty string was scored as a wrong answer rather than a broken call.

**The result on sentences that share no wording with the labelled set: 3 of 4.**

| input | expected | got |
|---|---|---|
| "My brother in law does the drywall on most of my jobs" | MEMORY_CANDIDATE | ✅ 0.472 |
| "hang on let me check that" | CURRENT_CONTEXT | ✅ 0.459 |
| "The inspector wants the panel schedule typed not handwritten" | MEMORY_CANDIDATE | ❌ 0.492 |
| "did it finish yet" | CURRENT_CONTEXT | ✅ 0.494 |

⚠ **Read the scores, not just the tally.** They cluster between 0.459 and 0.494, and **the one it got
right scored LOWER than two it got wrong.** So you cannot use the score to flag the shaky cases —
there is no confidence signal to threshold, only a ranking.

⚠⚠ **The miss is the expensive direction.** A durable fact about someone's trade was filed as
conversational and would have been dropped silently, forever. False negatives here are invisible;
false positives merely sit in a queue looking silly.

★ An earlier figure of **7/8** was measured on items close to the labelled examples and should not be
quoted. Verbatim overlap between probe and target makes hits meaningless and misses damning.

## What to do with it

- **Eight labelled examples is thin for kNN.** More examples is the obvious lever. Resist tuning
  until you have a held-out set of *your* real messages, labelled *before* you see the classifier's
  answers. Otherwise you are measuring agreement with yourself after the fact.
- **Keep the queue even if you drop the classifier.** `memory_candidates.py` is useful with a human,
  a regex, or nothing at all in front of it. The queue is the load-bearing idea; the classifier is
  one way to fill it.
- **`capture()` requires a `why` and raises without one.** A candidate without its reason is an
  orphan sentence in three weeks and promoting it becomes guesswork. kNN supplies this for free — the
  nearest labelled example *is* the explanation, which is one concrete advantage it has over a chat
  model that would hand you a number you have just seen cannot be trusted.
- **Nothing in these modules can promote a candidate to a memory.** That is asserted structurally:
  the selftest parses the module's own imports and fails if it can reach a memory writer. Promotion
  stays a separate human decision, because that is the one step that is not reversible.

---

## When you are done

Run the full acceptance check one more time and keep the output next to `baseline.txt`. Two files,
before and after, in plain English — that is the record of what was actually built, and it is
readable by someone who never opened the code.

**And if a stage will not pass, stop there and keep what works.** A verified system with five
components beats an unverified one with nine, and the second kind fails silently — which means you
will trust it right up until the day it matters.
