# Designer's brief — SC_Placeholder, in his own words

**Received 2026-09-02, 12:20, by Telegram. Reproduced verbatim below, unedited.** Typography,
paragraphing and wording are his; nothing has been corrected, condensed, or rearranged. He opened it
*"in case this ever comes up in court"*, so the value of this file depends entirely on it being
untouched, and it was captured straight from the message store rather than retyped.

---

## What this document is, and what it is not

⚠ **This is a RECONSTRUCTED account, written today, and it is deliberately NOT merged into
`DESIGN_PROVENANCE.md`.** The quotations in that file are contemporaneous — July and August, written
while the decisions were being made and before authorship was ever in question. That is what makes
them strong. A statement composed after the question arises is a different kind of evidence, and
blending the two would let the weaker material discredit the stronger. Two documents, two weights,
each honest about which it is.

★ **What it carries that the contemporaneous record cannot.** The dated messages show *what* was
decided, in the terse shape of someone giving an instruction. They do not show the reasoning, the
alternatives weighed, or the constraints being designed against. Only the designer has that, and none
of it is recoverable from logs. Read the two together: the log proves when, this proves why.

---

## Accuracy check, run before attaching

His brief describes **the system as built and run privately**. This repository is the extracted
template, and the two are not identical. Every claim was checked against the shipped **code**, not
against prose — an earlier pass matched keywords across all files and reported everything present,
which was worthless: `librarian` appeared in exactly one file, a document I had written myself.

| claim | in this repo's code |
|---|---|
| OCS — small always-loaded core, rest streamed | yes (`recall.py`) |
| Rust index | yes (`Cargo.toml`, `main.rs`, `sweep_conformance.py`) |
| fast / slow / walk tiers | yes (`benchmark.py`, `coverage.py`, `findable.py`) |
| multiple engines with deliberate overlap | yes (`coverage.py`, `findable.py`) |
| topic fallback | yes (`benchmark.py`, `coverage.py`) |
| generic-message filtration | yes (`candidate_classify.py`) |
| rolling candidate file | yes (`candidate_classify.py`, `memory_candidates.py`) |
| automatic rebuild | yes (`memory_candidates.py`) |
| benchmarks | yes (`benchmark.py`, `coverage.py`, `downstream_of.py`) |
| **dual librarian** | yes (`librarians.py`) — extracted 2026-09-02 12:35, 4/4 mutation-checked |
| **multi-tier rolling context, last three sessions** | yes (`rolling_context.py`) — extracted 2026-09-02 12:40 |
| non-English evaluation | **absent, and he says so himself** — see his own caveat below |

⚠ **Two rows changed after this table was first written.** At 12:21 the dual librarian and the
multi-tier rolling context were real but private, and the table said so. Both were extracted into
`tools/` the same afternoon, so the table now reads *yes* — and the earlier state is recorded here
rather than overwritten, because the honest version of a compliance table is the one that shows what
it said before the gap was closed.

★ Note his own caveat on languages. He states unprompted that the system has only been tested in
English, that he cannot personally verify a Japanese benchmark, and that the topic fallback is *"the
most unreliable aspect."* A designer volunteering the weakest part of his own system is the part of
this document I would weigh most heavily.

---

## Revision history

**12:20** — first version received.
**12:32** — the author revised **one sentence** and re-sent. Diffed rather than eyeballed; exactly
one clause differs, appended to the topic-fallback caveat:

> *"...might not be sufficient to retrieve the right memory* **which is why this is a fallback and
> not something summoned on every query.**"*

The version reproduced below is the 12:32 text. ⚠ The earlier wording is recorded here rather than
discarded, because a document offered as a paper trail should not quietly change under its own
timestamp.

★ **The added clause was checked, not just accepted.** It is an engineering claim now, not only an
admission, so it needed to be true: `docs/BUILD_PROMPTS.md` line 118 specifies the fuzzy topic
fallback as *"last resort when every engine returns nothing usable"*, and `coverage.py` tracks it as
*"7b fuzzy topic fallback (last resort)"*. The spec matches the sentence.

---

## The brief, verbatim

> Moth: Memory System:
>
> Hey! In case this ever comes up in court I am writing this to show my involvement and direction of this project.
>
> Our first challenge was taking on bloat before it became bloat, sure text files are small but what happens when you have millions of them? Your system either can’t recall them all or your processing power comes to a standstill. I proposed OCS to keep our most relevant files and processes permanently loaded with the ability to stream chunks in bulk as we rotate between tools, projects and processes. I needed the system to be infinitely scalable because I don’t know how large my ai lab will be in a decade and building for now will cause problems later. Similarly I chose asset streaming over conventional loading because you and I might not be able to notice a delay of a few seconds but with the output of Ai there is a good chance they’ll finish a task before a memory tells them to stop and then you’re burning tokens for no good reason and increasing the likelihood of failures because every edit increases the likelihood of an error being made, it’s simple probability, so the storage and retrieval engine had to be both robust, fast and accurate. It’s why I argued with my overlord agent about designing the index in RUST rather than Python, every millisecond counts, if we’re running 1,000 projects at once we can’t have memory calls stacking on top of each other and the wrong memories being sent to the wrong teams. It’s also why we built the fast, slow and walk systems. The ideal is the system perfectly recalls an old memory within an unnoticeable amount of time, realistically, that doesn’t always happen so we have the slow path and as a fallback if all else fails the walk. I also included multiple engines even though some have overlap, they catch memories that the other engines fail to grab, we also have a topic fallback if the user says trophy and it’s supposed to be award and the system otherwise can’t call back up the right memory; I’d argue this is the most unreliable aspect of our project since a close topic approximation might not be sufficient to retrieve the right memory which is why this is a fallback and not something summoned on every query. We have also only tested it in English so this system may fail in other languages with a different structure than English which we haven’t benchmarked ourselves yet since I only speak and write fluent English so I can’t personally verify the benchmark claims if we tested it in let’s say Japanese. Moreover we needed a dual librarian system to analyze both the past and the present and search the archives to detect retrieval failures our other systems failed to produce. We also built a filtration layer for user messages so if I say something like “I like bread” or “go for it” it doesn’t waste computation trying to locate a generic phrase; our filtration engine writes to a rolling file to avoid bloat as well as creating false memories that may unintentionally be indexed as a result of a bug. I also wanted the system as a whole to be automatic, self-healing and reliable. We also have a multi-tier rolling context our agent can review to view its last three sessions so that no context can ever get lost during compaction.
>
> I can’t spend all day every day reminding my agent of memories they already know, in my opinion, it is a huge oversight that the enterprise level companies have not built a better retrieval and storage system by default. It it’s inexcusable that us users have to go through so many hoops just to get our agents to remember what it was working on yesterday. If I had discovered the cure for cancer I should not have to spend the following afternoon trying to get my agent to find where it had saved our research out of potentially tens of thousands of documents. Something as robust as our storage and retrieval system should be the default, not engineered by a solo dev. These enterprise level companies have experts a lot smarter than me, they should’ve identified and rectified the failure before us users did.
