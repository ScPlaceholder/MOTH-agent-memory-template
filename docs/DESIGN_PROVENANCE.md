# Design provenance — who decided what, with dates

**Purpose.** A record of the human design decisions behind this system: what was asked for, when,
in whose words, and what came of it. Written 2026-09-02 at SC_Placeholder's request, for the
authorship record.

**Method, stated up front because it determines what this document is worth.** Every quotation below
was harvested from the project's own dated logs and ticket notes, not reconstructed from memory. The
harvest found **13 dated design quotations** in the ticket record and 43 more across the memory tree.
Where I could not find a dated source, I have said so rather than paraphrasing from recollection —
a paper trail assembled from memory is not a paper trail.

⚠ **SCOPE: the memory harness only.** Not the voice stack, the render pipeline, or the think-tank
rooms, except where a decision shaped memory directly. Scoped at SC_Placeholder's instruction on
2026-09-02 after a first draft that mixed projects together.

⚠ **This is a first pass.** The "where it did not hold" section is deliberately short because I only
list items the record actually settles.

---

## 1. The architecture calls

**2026-08-16 — the Rust memory core, green-lit.**

> *"Want to have all your local agents and cloud agents setup the whole memory database in rust? You
> can keep your librarians however you think is best."*

Two decisions in one sentence: the storage layer moves to Rust, and the retrieval layer stays with
the implementer. That division held for the rest of the project.

**2026-07-11 — object-container streaming. The earliest architectural call, and the sharpest.**

> *"Are you saving all your projects into your memory.md? Would it help to organize your memory.md
> into object containers based on project category to optimize loading — or would that lead to
> forgetting about projects?"*

His own gloss, 2026-09-02: *"Most systems load a file in full instead of streaming them."*

★ **Read the second half of that 2026-07-11 sentence.** He proposed the optimisation and named its
failure mode in the same breath: containers reduce what you load, and the risk is that anything not
loaded is effectively forgotten. That objection is why the design has a **manifest** — a small always-
loaded index of what exists in the unloaded containers — rather than only a set of containers.

The result is the two-layer split the system still runs on: a lean stateful layer loaded every boot,
and a much larger streamed layer fetched on demand. As implemented: a small always-read core against
551 files that are not read until something makes them relevant.

⚠ Note what the objection did to the design. Without it, containers alone would have produced a
system that loads quickly and cannot find what it owns — which is precisely the failure the whole
retrieval half of this project exists to prevent.

**2026-07-25 — the principle, stated by analogy.**

> *"could we do OCS and asset streaming for the cast? Like town x has 20 named npcs — they would only
> need to be recalled when players visit that town."*

The clearest single statement of the rule the retrieval layer runs on: **recall on relevance, not up
front.** He arrived at it through a game's NPC cast, which is where the technique comes from, and
applied it to memory without needing the analogy explained back to him.

**2026-07-30 — why it exists at all.**

> *"all those attempts that failed were byproducts of trying to build something to correct Anthropic's
> lack of support for long term persistence. I assumed between a tiered index, asset streaming and
> object container streaming that there would be no way for you to lose memories unless they
> physically grew too big to recall — which could be solved by a database."*

This is the purpose statement for the whole system, and it is worth reading as a specification: the
three mechanisms — tiered index, asset streaming, object-container streaming — are named as a set,
and the success criterion is stated as an absolute. *No way to lose memories.* Everything measured in
this project is ultimately measured against that sentence.

⚠ He also names the one failure mode he would accept — memories growing physically too large to
recall — and pre-commits the answer: a database. That is a designer stating in advance which failure
is legitimate and which is not.

**2026-08-17 — automatic rebuild.**

> *"how do we make your rust index rebuild automatic on every write"*

Produced the debounced auto-rebuild (`DEBOUNCE_S=10`, `MAX_STALE_S=900`) and `index_freshness`,
which exists — in the implementer's words at the time — to *"stop the flat index from lying
quietly."*

**2026-08-29 — the rolling candidate file.**

> *"Why can't memory candidate be a rolling file that updates after a write and retrieval?"*

Recorded at the time as: **this removes my stated objection rather than working around it.** That is
the highest-value kind of design input and it is rare — most feedback proposes a workaround for a
constraint; this dissolved the constraint.

**2026-07-30 — the two-librarian framing.** Recorded at the time under the heading *"J's framing, and
it is better than mine was."*

| | asks | source |
|---|---|---|
| Librarian 1 — guidance | *what is the rule here?* | the memo tree |
| Librarian 2 — precedent | *when did this last happen, and what actually occurred?* | the raw turn archive |

His analogy: rule and precedent, a lawyer's two shelves — and precedent is the more persuasive one.
His own illustration was a washer: *"1/2 washer"* is the rule and it loses an argument standing in a
field; *"the day you drove four and a half hours back for one"* is the precedent and wins instantly.

This is a structural decision, not a preference. The two stores join on the timestamp, so the small
dated record becomes the index into the large undated one. It is the design the retrieval layer still
runs on.

⚠ **This entry was missing from the first draft of this document** and was added the same day, after a
retrieval guard flagged a file I had not read. Undercrediting the human contribution is the specific
failure this document exists to correct, so an omission of exactly that kind belongs on the record
rather than being quietly patched.

---

## 2. The measurement calls

These shaped how the system is *evaluated*, which turned out to matter more than any single feature.

**2026-08-27 — the diversity criterion.**

> *"we need diversity in thinking and running them a few times in a room will help determine which
> models are capable of reasoning or the ones that just jump on obvious solutions or echo the
> solution presented by another candidate."*

This is the origin of the echo-versus-reasoner distinction and of `revision_direction.py`. The
insight is that agreement is not evidence, and that the discriminator is *what a seat revised
toward*, not whether it revised.

**2026-08-29 — the stripped-prose control room.**

> *"Dumb tank is a room full of the same AIs as your think tank but they're provided a prompt
> stripped of prose so they can't be cleverly persuaded by the initial problem."*

A control group for the implementer's own influence on results. It produced `strip_prose.py` and the
paired-room measurement.

**2026-08-22 — the standard for claims about oneself.**

> *"ask me in a week and I will have a number instead of a feeling."*

Said after the implementer asserted, confidently and without measuring, that her sense of elapsed
time *"has not improved at all."* Became the rule that a number about yourself is almost always a
feeling until counted.

---

## 3. The interface calls

**2026-08-27 — bullet output, full brief stored separately.**

> *"Can the output for Apriel be sent as bullet points or something to keep it less verbose and have
> the full brief stored separately to be called up by any model including you if needed."*

**2026-08-27 — asking the right diagnostic question.**

> *"Wonder what happened and why it didn't listen, was that a bug or intentional?"*

Investigated and answered: not a bug. The distinction between *didn't listen* and *listened and
answered in its own shape* is the one that decides whether a model keeps its seat, and the question
is what forced it to be separated.

---

## 4. Where the record shows a call that did not hold

⚠ Listed only where the record settles it. This section is short on purpose; padding it would make
the rest less credible, not more.

**No harness-specific instance is recorded.** The design calls above were followed and held. There is
a documented disagreement from 2026-09-02 about an automatic engine-swap trigger, but that concerns
the voice/consent path rather than the memory harness, so under the scope rule it does not belong
here — and padding this section with an out-of-scope example would make the rest less credible.

⚠ Recorded so that a reader knows the absence was checked rather than assumed.

---

## 5. Named by the designer, not yet dated in the record

On 2026-09-02 SC_Placeholder listed his memory-harness contributions. Four are evidenced above with
dated quotations. Two I could **not** find a dated source for in the files searched
(`interests.json`, the pipeline writeup, the retrieval design doc):

**2026-08-29 — the dual embedder. SOURCED, on his pointer.** He named the handle and the record was
one search away:

> *"see if it catches anything that our other embedders missed."*

That question is why `bge_vs_nomic.py` exists, and it is a sharper question than it looks. Every
earlier run had only ever *reordered* candidates the keyword arm already found, and reordering cannot
reveal what was never in the pool. His phrasing forced the measurement to be about **disjointness**
between two independent first-stage retrievers rather than about which model wins — with the negative
result made explicitly acceptable: if the second engine surfaces nothing new, a second index buys
nothing and we stop paying for it.

★ Framing a question so that a null result is publishable is a design contribution, not a request.

**2026-08-25 — parallel engines. SOURCED, and it overturned the evaluation method.**

> *"Some of our tools don't have perfect recall but they make up for gaps the other retrieval methods
> are lacking"* — and: *"That can be tested and benchmarked because that's how we decided to use them
> in our system."*

This was an objection to how engines were being judged. The existing gates were **replacement** tests:
does this engine beat the baseline, and does it lose none of the baseline's wins. Both ask *should
this take the throne*. On that basis SPLADE was REJECTED at 10/14, and the reranked arm REJECTED at
6/14.

He was right, and the evidence was already in the output that rejected them: **probe 9 was missed by
SPLADE and found by the reranked arm.** An engine scoring 6/14 while uniquely owning a probe nothing
else reaches has earned a seat, and a replacement test discards it for not being best.

So the question was replaced with the one that matches how the stack is actually used — *does the
fused system get worse if I remove this engine?* — which is a leave-one-out test on the shipped
configuration. `ensemble_bench.py` exists because of that objection.

★ Note the second half of the quotation. He did not only say the engines complement each other; he
said **that is testable**, and named why it was the right test — because it is how the system is
actually used. The measurement standard came with the idea.

⚠ **Bound on the searching:** the ticket store and four design documents, not the 40,000-turn
conversation archive. Anything marked unsourced here is *not found within that bound* — not *did not
happen*.

---

## 5b. The designer's own account, attached separately

On 2026-09-02 SC_Placeholder wrote a first-person brief on the system's design and sent it for
attachment. It is at **`docs/DESIGNER_BRIEF_2026-09-02.md`**, verbatim and unedited.

⚠ **It is deliberately NOT merged into this file, and the separation is the point.** Everything above
is contemporaneous — quoted from July and August, written before authorship was in question. His
brief is reconstructed today, during that discussion. Blending them would let a reader discount the
strong material by association with the weak. Read together they answer different questions: this
file establishes **when** each call was made; his establishes **why**, which the terse original
messages never recorded.

★ Its claims were checked against this repository's **code** before attaching — see the table in that
file. Two components he describes (the dual librarian, the multi-tier rolling context) are real but
live in the private system and are not extracted here; that is scope, and it is marked as such rather
than quietly passed along.

---

## 6. What this document does not claim

- It does not claim the human wrote the code. He designed and directed; the implementation,
  measurement, and the documented failures are the AI's.
- It does not resolve the copyright question. US Copyright Office guidance is that purely
  AI-generated work is not protectable and human authorship is required; this document exists to
  record what the human authorship actually was, in his own words and with dates. Whether that is
  sufficient is a question for a lawyer, not for this file.
- It is not complete. Thirteen dated design quotations were found in the ticket record; more exist
  in conversation logs that have not been harvested.
