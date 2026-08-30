# Contributing

Thanks for looking. This is a small, opinionated repository and the bar for changes is "show the
measurement," not "match the style guide."

## Licensing: there is no CLA, and you do not need to sign anything

The project is Apache License 2.0, and **Section 5 of that licence already settles the question a
CLA usually exists to answer**:

> Unless You explicitly state otherwise, any Contribution intentionally submitted for inclusion in
> the Work by You to the Licensor shall be under the terms and conditions of this License, without
> any additional terms or conditions.

So opening a pull request licenses that contribution under Apache 2.0 automatically. Inbound matches
outbound. Nothing to sign, no separate agreement, no email.

Two consequences worth stating plainly:

- **Only submit work you have the right to submit.** If your employer owns your output, that is
  between you and them, and §5 does not fix it.
- **Do not paste in third-party code.** See *Two hard rules* below.

## Before you open a pull request

Every tool in `tools/` carries its own `--selftest`. They are stdlib-only and take seconds:

```
python tools/recall.py --selftest        # ...and the same for every other tool you touched
python tools/lint_prompts.py             # checks the build prompts for known-shape defects
python tools/coverage.py                 # checks every architecture box is addressed
```

If you change retrieval behaviour, run the benchmark and **put the numbers in the PR description**:

```
python tools/benchmark.py --top 7
```

A claim like "this improves recall" without a before and after is not reviewable. A regression you
report yourself is far more useful than one a reviewer finds.

## Two hard rules

**1. No real identifiers in examples, ever.**

The sample corpus and the labelled examples in `tools/candidate_classify.py` must be synthetic. This
is not hypothetical caution: an earlier version of that file carried a real person's forum handle as
a training example, and it was found by a scan run for an unrelated reason, days before publication.
The example was doing a legitimate job — teaching the classifier that a bare identifier-fact is
durable — and it did not need to be a real one to do it. `riverbend_ok` works exactly as well.

Names, handles, account IDs, email addresses, chat IDs, absolute paths containing a username. If a
worked example needs one, invent it.

**2. No model weights, and no vendored third-party source.**

This repository contains original work only, which is what lets `THIRD_PARTY.md` be a short warning
list instead of a licensing inventory. Naming a model and telling someone how to install it creates
no obligation; shipping it creates several, and they are not all compatible with each other. The
default embedder, for instance, is under Google's Gemma Terms rather than Apache — which is why
`MEMORY_EMBED_MODEL` is overridable rather than hardcoded.

If your change needs a new optional model, add it to `THIRD_PARTY.md` with its actual licence and
the date you checked, and leave it optional.

## What a good contribution looks like

- **A new example memory** in `memory/` that teaches something the existing nine do not. Follow
  `docs/FORMAT.md`. The best ones record a specific failure and what it cost, because a rule with a
  story attached survives contact with a real session and an abstract one does not.
- **A retrieval improvement** with benchmark numbers on both sides, including whatever it made worse.
  Everything trades against something; the PRs that get merged are the ones that say what.
- **A hook** that makes a memory get *retrieved* at the right moment. This is the load-bearing part
  of the system and the least finished — storage was never the hard problem.
- **A correction.** If something here is wrong, say so with the evidence. Documented reasoning that
  turns out to be mistaken is worse than no reasoning, because it is more convincing.

## Style

Match the surrounding code: standard library only, no dependencies, comments that explain *why* a
choice was made rather than restating what the line does. Several comments in this repository are
long because they record a measurement or a defect that argues for the current design. That is
deliberate. If you remove one, replace the reasoning rather than just the text.

## Reporting a problem

Open an issue with what you ran, what you expected, and what happened. If it is a retrieval quality
issue, include the query and the ranked results — "it did not find the right thing" is not
reproducible, and retrieval failures are usually specific to a corpus.
