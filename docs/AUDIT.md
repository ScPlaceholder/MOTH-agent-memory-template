# What "audited" means here

This file exists so that **"audited" is a claim you can check rather than one you have to trust.**
It records what was actually verified, what was not, and what was found — including the parts where
the audit found nothing, which is the most misreadable result of all.

Date: 2026-08-25. Everything below is reproducible from a clean checkout.

---

## 1. Mechanical checks (exact answers, no judgement required)

These were run first, deliberately, because a question with an exact answer should never be sent to
a model.

| check | why it matters | result |
|---|---|---|
| All three `--selftest` runs, **from a foreign working directory** | The classic first-run failure for a downloaded tool: anything depending on the current directory dies the moment a user runs it from somewhere else | **PASS** — and a real query still returned hits |
| `whereis` genuinely calls `recall` — verified by parsing the **AST**, not by grepping for a string | "It delegates" should be a fact about the syntax tree, not about a word appearing in a comment | **PASS** — calls `_recall.recall` |
| `memory_echo` reuses `recall`'s parser and walker | Same reason | **PASS** — reuses `split_front`, `terms`, `walk` |
| `whereis` contains **no private copy** of `BODY_CAP`, `DESC_WEIGHT`, `score_file`, `terms` | A shadow copy would let the two files' ranking drift apart **while every test still passed**, making the README true of one file and false of the other | **PASS** — none present |
| Every path named in the README exists; every constant it cites is in the code | A README that describes code that is not there is the most common defect in a template repo | **PASS** |

## 2. Model reviews — three of them, with wildly different value

| reviewer | claimed | reproducible | note |
|---|---|---|---|
| local model (deepseek) | 12 | **0** | consistent with its measured ~1-useful-in-5, below it here |
| **codex** | 5 | **5** | every one real, every one fixed, each now regression-tested |
| copilot (comments intact) | 0 | — | **not counted — see §2c** |

### 2a. The local model: 12 claimed, 0 reproducible

Every claim with a concrete trigger was **executed**, not argued about:

* `echoes("")` → returns `[]`. Correct; an empty draft must not match everything.
* `main` with an empty or whitespace-only draft → clean `argparse` error with a usage message.
  Correct; that is the designed refusal.
* File-handling claims → tested with a hostile corpus (binary content in a `.md` file, missing
  frontmatter, truncated frontmatter, an empty file, and **a directory named `notes.md`**). All
  handled: score 0, no exception.

That hit rate is consistent with this reviewer's measured historical rate of roughly **one useful
finding in five**, and below it on this occasion.

> **The review was still worth running, and not for its findings.** Checking its claims forced edge
> cases that would not otherwise have been written. That is a real return, and it is a different
> return from the one the tool advertises.

### 2b. Codex: 5 claimed, 5 reproduced, 5 fixed

Every one was real. Reproduced before touching anything, fixed, and each now has a regression test
verified by re-introducing the bug:

1. **`whereis` searched the disk using the first RAW word.** `"the widget index"` searched the
   filesystem for **`the`** — in the tool whose entire purpose is putting memory in front of a file
   search. Every selftest passed throughout, because they asserted the *order* of the two calls and
   never the *quality* of either.
2. **Term matching was substring-based**, so `"bug"` matched `"debug"` and **counted toward
   coverage** — the headline ranking claim. Note what this means: the coverage multiplier *was*
   mutation-tested. The test verified the formula was applied and never that its inputs were
   correct. **A verified formula over wrong operands is still wrong.**
3. **`similarity()` could return 2.0.** The description bonus went into the numerator alone. A
   "similarity" above 1 is not one, and the docstring had promised Jaccard.
4. **`memory_echo` reopened files at display time** without the `OSError` guard that already existed
   in `recall.score_file` — the same case, unfixed in its sibling.
5. **Selftests leaked a temp directory per run**; 15 had accumulated.

### 2c. Copilot: excluded from the count, and why

Run with all source comments intact, it returned *"these three files are defect-free... a
well-reviewed, battle-tested template"* — and then **re-listed the five bugs above**, which the
prompt had explicitly told it not to re-report, reframed as evidence of quality and citing this
repo's own comments back at it.

**It read the commentary and agreed with it.** That is not an independent pass and is not recorded
as one. The lesson generalises: heavy explanatory comments make code *read* as verified. If you
review this template with a model, **strip the comments first**.

## 2d. SECOND CODEX PASS — pre-publication, 2026-08-25

Run again on the finished repo, in a **filesystem-isolated directory with a clean parent** and with
**all comments and docstrings stripped** (43% of the source by volume). Both precautions were paid
for: a flag does not confine a tool, and heavy commentary makes code *read* as verified.

**10 findings. 10 reproduced. 10 fixed.** And they clustered:

**Three were the same disease, and it is this repository's own headline lesson:**

| input | old behaviour |
|---|---|
| corpus folder exists but is **empty** | scored `0/10` — reads as "retrieval is broken" |
| probes file missing or corrupt | raw Python traceback, at a non-programmer |
| probes file parses but contains **no probes** | **`VERDICT: WORKING`** |

That last one is the worst thing this project produced. A malformed probes file — precisely what an
agent generating probes for a user will sometimes emit — made the acceptance check **report success
over zero tests.** A benchmark that cannot fail, shipped inside the document arguing against
benchmarks that cannot fail. All three now refuse and say why.

**The rest:**

* **You could not find a memory by its own filename.** Names are kebab-case; the query kept the
  hyphenated form as one unmatchable term. `recall.py "feature-flag-defaults-differ-by-environment"`
  returned nothing.
* **`--top -1` silently dropped a result** instead of erroring, because `hits[:-1]` is valid Python.
  In `benchmark.py` it printed `hit@-1` beside a wrong score. A wrong number that looks like a number
  is worse than a crash.
* **A nonexistent `--root` was skipped silently**, so a typo produced a confident "no match"
  indistinguishable from a real absence.
* **`whereis` filesystem results depended on WORD ORDER** — "deployment migration" found nothing;
  "migration deployment" found the file. This was the *second* defect in that one line: the first was
  searching the first RAW word ("the widget index" → `the`), and that fix moved to the first
  *meaningful* word and stopped. **A repair aimed at the instance leaves the shape behind.**

### The copilot pass, again: 2 claimed, 0 reproducible

Containment held this time. Its two findings were tested and both failed: `score_file(path, [])`
returns `0.0` rather than dividing by zero (its own write-up contradicted itself on this), and the
"incomplete sentence" it flagged is a wrapped `print` that renders correctly.

★ **But testing its claims found a real defect it did not report** — a query of nothing but stopwords
printed `no file matched any of: ` with an empty list: a confident report of absence over a search
that never had a term. **Fourth instance of the same disease, and the review's value was again the
edge cases it forced rather than the findings it made.**

## 2e. THE THREE-WAY AUDIT — 15 claims, 0 reproducible

Run on the hardened repo, in a filesystem-isolated directory, comments stripped (44% of the source).

| reviewer | claimed | reproducible | note |
|---|---|---|---|
| GPT (copilot) | 2 | **0** | both refuted by running them |
| deepseek-coder-v2:16b | ~9 | **0** | one file **timed out**; 84% of its output was a repetition loop |
| qwen2.5-coder:14b | ~4 | **0** | completed all 4 files; every claim refuted |

**Fifteen claims, none reproducible** — from three reviewers, on code where **codex found ten real
defects the same day**. So the target was not un-findable; those ten were fixed.

★★★ **BUT THE INTERESTING PART IS *WHAT* THEY CLAIMED.** Nearly every finding was of one shape:

> *"If X is empty/malformed, this returns nothing / raises."*

Which describes **the guards**. `--top 0` refusing, an empty query refusing, a malformed probes file
refusing, `score_file` returning `0.0` on an unreadable path — these are not gaps, they are the
repairs made earlier the same day, and several were **genuinely true that morning and false by the
afternoon**.

**The reviewers were reasoning from the code's shape rather than running it.** A guard that refuses
bad input is, to a model reading statically, indistinguishable from a function that fails to handle
it. Only execution separates those, which is the same lesson the rest of this document keeps
arriving at from other directions.

★ **The run was still worth its cost, and not for its findings.** Checking fifteen wrong claims meant
executing fifteen paths — `--top 0`, empty queries, unmatchable drafts, empty probes files,
`_rank` on a miss. **All of those are now verified behaviour rather than assumed behaviour.** That is
a real return, and it is a different return from the one a code review advertises.

⚠ And one methodological failure, mine: I launched two 14B+ models concurrently against a single GPU.
They serialised, each handover costing a ~80-second model swap, and my diagnostic probe added a
further request and made it worse. **Contended-parallel was strictly slower than serial.** Re-run one
at a time, qwen completed all four files without difficulty.

## 3. What the review caused, which is the actual result

The hostile corpus above began as a one-off check. It is now **in the suite** — because a check run
once is a measurement, and only a check in the suite is a guarantee.

**And that promoted test was wrong on the first attempt.** Deleting the `OSError` guard it claimed
to protect left the test **passing**: it reached the code through `recall()`, which walks with
`os.walk` and therefore only ever yields *files*, so the unreadable-path branch was unreachable from
it. The assertion could not touch the thing it was defending. Fixed by calling `score_file`
directly; re-verified by deleting the guard again, which now fails with `PermissionError`.

## 4. Mutation verification

Every headline claim in the README is protected by an assertion that was checked **by deleting the
feature and confirming the test fails.** An assertion that passes with the feature removed is
decoration, and two of these were decoration on their first draft.

| claim | mutation applied | result |
|---|---|---|
| Coverage beats depth (`recall`) | Remove the coverage multiplier | **CAUGHT** (survived on the first fixture — rebuilt so coverage is the deciding factor) |
| Memory is searched before disk (`whereis`) | Swap the two calls | **CAUGHT** (and proven necessary: the swapped version returns *byte-identical output*, so no output test could ever see it) |
| Duplicate detection ranks but never gates (`memory_echo`) | Add a similarity threshold that blocks | **CAUGHT** |
| Malformed files score 0 rather than crashing (`recall`) | Remove the `OSError` guard | **CAUGHT** (survived on the first attempt — see §3) |

## 4b. Retrieval is measured — and the first measurement was misread

`tools/benchmark.py` is the only check here that has ever come back red, and it did so on its first
run (6/10), which is how the stopword defect was found. Two corpora now ship:

```
sample/memory   (10 same-genre notes)   [1] hit@1 9/10  hit@3 10/10   [2] 1 as documented
sample/mixed    (11 different KINDS)    [1] hit@1 9/10  hit@3 10/10   [2] 3 as documented
```

**Those numbers are the SECOND version, and the first version was wrong twice over.** Both errors are
recorded here because an audit that only shows the final state is a brochure.

**Error one — a confounded comparison.** The corpora first reported 8/10 and 5/10, and the conclusion
was immediate: *heterogeneous corpora are harder.* Tidy, arrived within a minute, and it confirmed the
hypothesis that had motivated building the second corpus. It was also confounded — the genre mix
changed **and** so did probe strictness (mean query/answer word overlap 33% vs 25%). Two variables
moved; the effect was credited to one.

Resolved by **re-analysis, not a re-run**: sorting all 24 probes by a third variable — content words
shared between question and answer — explains everything with no exceptions in either direction.

| shared words | probes | found in top 3 |
|---|---|---|
| none | 4 | **0** |
| one or more | 20 | **20** (18 at rank 1) |

**Error two — the benchmark was reporting a defect that did not exist.** Zero-overlap probes sat in
the same table as ordinary ones, so a question *deliberately written* to share no vocabulary with its
answer appeared as a headline `MISS`, and the summary read `hit@1: 5/10`. A stranger reads that as
mediocrity. It was not measuring retrieval; it was measuring how adversarially the probe author had
written the questions — and the same corpus answered the natural phrasing of those same questions at
rank 1.

Probes are now split into **works / boundary / absent**, reported separately and never summed. Only
`works` is scored. The split is enforced by the selftest in both directions (a zero-overlap probe in
`works` is rejected; so is a vocabulary-sharing probe hiding in `boundary`), and both directions were
mutation-verified — a category system polices nothing if membership is decided by whoever last edited
the JSON.

A cliff, not a gradient, and it sits at one word. Which means **both hit@1 figures are largely
reporting how many zero-overlap probes the author happened to write** — a property of the probe set,
not of the retrieval. `benchmark.py --overlap` reproduces this, so the finding is executable rather
than asserted.

★ **The lesson worth carrying off this page:** a confounded result does not look broken, it looks
*explicable*. The speed and neatness of the available explanation is the warning sign, not the
reassurance.

⚠ **This section went stale within an hour of being written.** §2–§4 were brought up to date, and the
work done immediately afterwards changed their conclusions. That is not carelessness about docs; it
is the normal rate at which an audit decays while the thing it audits is still moving. **Treat the
date at the top as load-bearing.**

## 4c. `wired.py` — a tool whose errors all run one direction, and the author who forgot

`wired.py` answers "is component X actually called by module Y" from the AST rather than by grepping.
It is here because the two obvious approaches are both wrong in opposite ways: **grep OVER-reports**
(it matches comments enthusiastically describing a component that was never wired in), and **naive
import analysis UNDER-reports**.

It has now had **three separate false-negative classes**, each found by running it and each reporting
a live connection as dead:

| missed | because |
|---|---|
| subprocess dispatch | the callee is named in a string, not an import |
| dispatch by filename | same, via a `.py` literal handed to a runner |
| aliased lazy import | `import keyize as _keyize` inside a function, then `_keyize.keyize(q)` — the call was recorded under the alias and never matched the real name |

All three are fixed. The asymmetry is not:

> ★ **"Wired" is a strong claim from this tool. "Not wired" is a weak one.** It can only fail to see
> a connection; it cannot invent one. So a positive result stands on its own, and a negative result
> is a prompt to go and look.

⚠ **The author repeatedly mistook the weak claim for a finding.** On 2026-08-25, reasoning about this
system's own architecture, he asserted five times that a component was not wired in — models absent
from the machine, a query normaliser never called, a preserved sentence discarded, fusion throwing
away provenance, supersession never reaching retrieval. **All five were wrong, and all five were
wrong in the same direction.** Not once was a capability claimed that turned out to be missing.

The mechanism, stated because it will apply to whoever uses this next: you remember **building**
components — each was a session with a story — and you do not remember **connecting** them, because
a connection is one line in the middle of a file that takes ten seconds and has no narrative. So a
system reconstructed from memory comes back as a bag of parts, and the honest-feeling conclusion from
a bag of parts is *"these aren't hooked up."*

**A wrong fact is a wrong fact. A wrong absence is a proposal** — it arrives as "here is a gap, here
is what we should build," in the register that sounds most like competence. One of those proposals
nearly went into a diagram revision. Another was worse: a benchmark written that evening used RRF
fusion, a mode this system had already measured and *demoted* eight days earlier, and the resulting
weakness was reported as a discovery about the architecture.

**Before proposing a fix, grep for the fix.** Thirty seconds, against a proposal someone might act on.

## 5. What was NOT verified

State this plainly, because an audit that lists only successes is an advertisement.

* **Retrieval quality is not audited and cannot be, by us.** Nothing here establishes that the
  ranking returns the *right* memory for *your* corpus. See the README's benchmarking section: an
  agent cannot benchmark its own memory, because it chooses the probes.
* **No performance testing.** These tools walk the filesystem on every query. That is fine at
  thousands of files and untested beyond it.
* **No concurrency testing.** Two agents writing memories simultaneously is not covered.
* **Windows only.** All checks ran on Windows with CPython 3.10. The code has no platform-specific
  calls, but "should work" is not "was tested".
* **The example memories are invented.** They demonstrate the format. They are not evidence about
  real-corpus behaviour.
