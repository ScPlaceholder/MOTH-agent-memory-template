# The memory file format

Every memory is **one file holding one fact**. That constraint is not stylistic — it is what makes
retrieval work, and it is the first thing to get right because every tool here depends on it.

## Structure

```markdown
---
name: <short-kebab-case-slug>
description: <one line, used to decide relevance during recall>
metadata:
  type: user | feedback | project | reference
---

<the fact, stated plainly>

**Why:** <for feedback/project — the reason it matters>
**How to apply:** <for feedback/project — what to do differently>

Links to related memories use [[their-name]].
```

`name` must equal the filename without `.md`. The tools rely on it and the validator enforces it.

## The four types

| type | holds | example shape |
|---|---|---|
| `user` | who the person is — role, expertise, preferences | "Prefers being shown the failing case, not a summary of it" |
| `feedback` | guidance on how to work, including corrections | "Measure before optimising — includes the why" |
| `project` | ongoing work, goals, constraints not derivable from the repo | "The migration is blocked on X until Y ships" |
| `reference` | pointers to external resources | dashboards, tickets, URLs |

## Rules that earned their place

**One fact per file.** A file holding three facts matches three different queries and answers none of
them well. Splitting is cheap; a bloated file silently degrades every future search.

**Write the description for a stranger.** It is what a search shows first. If it needs the body to be
understood, it is a title, not a description.

**Convert relative dates to absolute.** "Last Tuesday" is unreadable in three weeks. Write the date.

**Link liberally with `[[name]]`.** A link to a memory that does not exist yet is not an error — it
marks something worth writing.

**Do not store what the repository already records.** Code structure, past fixes, and commit history
are already retrievable. A memory that duplicates them adds search noise and nothing else.

**Only `.md` files are indexed.** A `.py`, `.pdf` or `.txt` in the memory folder is not in your
memory — it produces no error and never appears in a result. If an artifact matters, write a note
that names it. **The note is what makes the artifact findable**; without one it is not in the corpus,
it is merely in the folder. (`sample/mixed/hello.py` is in there to demonstrate exactly this.)

## ★ Write the description in the words you will SEARCH with

This is the highest-leverage rule on the page, and it is the one nobody follows — because when you
write a note you are thinking in the vocabulary of the thing that just happened, and months later you
search in the vocabulary of the problem you now have. Those are different languages.

Measured across 24 probes and two corpora: a query sharing **one** content word with its answer file
found it in the top three **20 times out of 20**. A query sharing **none** found it **0 times out of
4** — no near misses, no partial credit. This is a string matcher. It does not know that *region* and
*country* are related, or that *flattery* is what you meant by *buttering up*.

So spend the description on reachability rather than precision. A note about *"the cache key omitted
the locale"* should carry **region, country, currency, money, wrong prices** somewhere in its
description, even though the original sentence is the more accurate one. **Accuracy you already have
— the body holds it. The description's job is to be findable from outside**, and one extra synonym is
the whole difference between finding it and not.

```bash
python tools/benchmark.py --overlap    # see the boundary on the shipped corpora
```

## Why short files beat long journals

Measured on a corpus of ~11,000 files: **short precise notes outrank long journals** for the same
query, because a long file dilutes every term it contains. A 4,000-word journal mentioning a topic
once scores worse than a 200-word note about that topic — correctly, because the note *is* the answer
and the journal merely touches it.

The practical consequence: when a memory grows past roughly a screen, it has usually become two
memories.
