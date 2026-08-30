# Instructions for the agent

**The code in this repo is the smaller half of the system.** The rest is behaviour, and behaviour
lives in your agent's prompt, not in a Python file.

This is not a philosophical point. A memory system with perfect storage and no habit of retrieval
behaves *exactly* like no memory system at all, and the failure is silent — nothing errors, the agent
simply answers from context and never learns the answer was already on disk. That happened here: the
storage worked on day one and went unused for weeks.

So paste the block below into your agent's system prompt. Adjust the paths. The reasoning behind each
line follows underneath, because you should not install instructions you cannot argue with.

---

## The block (paste this)

```
## Memory

You have a file-based memory at <PATH>. It is only useful if you reach for it.

RETRIEVING
- Before you search the filesystem for anything, run: python tools/whereis.py "<terms>"
  It searches memory first, then the disk, in one command. Use it INSTEAD OF find/grep/ls,
  not in addition to them.
- Before you state a fact about this project, a past decision, or a person: check memory first.
- Before you start a build, a fix, or a plan: check memory first.
- If you are about to say "I think" or "if I remember correctly" — that is the signal. Check.

READING THE RESULT — there are three outcomes and they are not the same:
1. One clear top hit  -> use it. Say where it came from.
2. Several plausible hits, no clear winner -> do not pick. Say what the candidates are and
   ask, or state that memory is ambiguous here.
3. Nothing, or only weak matches -> say "memory has nothing on this" and proceed WITHOUT it.
   Never fill the gap by inventing something plausible. A confident wrong memory is worse
   than no memory, because it cannot be told apart from a real one.

WRITING
- Before writing a new memory, run: python tools/memory_echo.py "<the fact>"
  Open the top few. If the fact is already there, AMEND that file instead of adding a
  near-duplicate. Five copies of one lesson is not five times the memory.
- One file, one fact. If it grows past a screen it has become two memories.
- Write the description in the words you would SEARCH with later, not the words of the
  thing that just happened. Include synonyms. This is the single highest-leverage habit
  here: a query sharing no content word with its note will NEVER find it.
- Then CHECK that habit rather than trusting it. Write down the question you expect to ask
  when you next need this note, and run:
      python tools/findable.py "<file or title>" "<that question>"
  It answers two things, and they fail for different reasons:
      FOUND? - the question against the WHOLE record. Fails -> rewrite the CONTENT.
      WINS?  - the question against title + description only. Fails -> RENAME the file.
  Retrieval does read bodies, but a word in the filename outweighs the same word buried in
  the text, so you can be findable and still lose to any file with the word in its name.
- Convert relative dates to absolute. "Last Tuesday" is unreadable in a month.
- Do not store what the repo already records: code structure, commit history, past diffs.

MAINTAINING
- When something you wrote turns out to be WRONG, correct or delete it. A stale memory
  outranks your own judgement precisely because you trust it.
- When a memory is superseded, say so in the new one and link the old.

AT THE START OF A SESSION — two layers, and only the first one loads automatically:
- A small ALWAYS-LOADED core: who you are, the current work, standing rules. Keep it
  lean. It is read in full, every session, and it competes for the same context as
  the actual task.
- Everything else STREAMS ON DEMAND. Journals, transcripts, reference notes, past
  projects. These are NOT loaded. They exist only if you go and get them, which is
  what `whereis.py` is for.
- So: if you find yourself thinking "I don't have anything on that" — you have not
  checked. Absence from your context is not absence from your memory, and those feel
  identical from the inside. That feeling is the single most reliable moment to run
  a search.
```

---

## Why each part is there

### "Use it instead of, not in addition to"

This is the whole design and it is the line most often softened into uselessness.

The instinct is to write *"remember to check memory first."* That rule already exists in most agent
prompts, in bold, and is read at the start of every session. **It does not work**, because it competes
with the urge to just go and look, and the urge wins at exactly the moment the rule matters.

So do not add a rule. **Change the cost.** `whereis.py` wraps the filesystem search the agent already
wants and puts the memory search in front of it — same command, same output, memory checked on the
way past. Checking stops being something to remember and becomes something that happens anyway.

If you leave `find` and `grep` available *alongside* it, you have re-created the rule and the urge
still wins. The substitution is the mechanism.

### "That is the signal. Check."

Retrieval fails at a predictable moment: not when the agent knows it is ignorant, but when it feels
it already knows. Hedging language — *I think*, *if I remember correctly*, *presumably* — is the most
reliable observable marker of that state. Naming it converts a feeling into a trigger.

### The three outcomes

Most agents collapse these into two, and the missing one is #2. An ambiguous result silently becomes
a confident answer, because picking the top hit is what the code does and nothing tells the agent that
"top hit" and "right answer" differ when scores are close.

Outcome #3 is worth stating explicitly for a different reason: **empty is a real answer.** An agent
that treats "nothing found" as a failure to be papered over will paper over it. The tools cooperate —
`recall.py` prints *"THIS CORPUS has no hit for these terms"* rather than "nothing relevant exists",
because those are different claims and only one of them is true.

### "Write the description in the words you would search with"

The highest-leverage line in the block, and the least intuitive.

Measured on the shipped corpora, across 24 probes: a query sharing **one** content word with its
answer file found it in the top three **20 times out of 20**. A query sharing **none** found it **0
times out of 4** — no near misses, no partial credit. A cliff, not a gradient.

Then the fix was tested: adding the searcher's vocabulary to the four failing notes' descriptions
rescued **4 of 4, every one to rank 1.** Every retrieval failure in this system is repairable by
whoever writes the note, at write time, for free.

The reason nobody does it: when you write a note you are thinking in the vocabulary of the thing that
just happened; months later you search in the vocabulary of the problem you now have. Different
languages. Spend the description on being *reachable*, not on being *accurate* — the body already
holds the accuracy.

### "Amend, do not duplicate"

Duplicate detection must **rank, never gate** — `memory_echo.py` is deliberately built so it cannot
block a write. Measured: a lesson echoing 29 existing files scored 0.189; an unrelated new fact scored
0.160. There is no gap, so any threshold is a coin toss with the authority to discard a real memory.

Which means the judgement is the agent's, and that is exactly why the instruction has to be in the
prompt. The tool shows; the agent decides.

### The two layers, and why the failure mode is a *feeling*

This is the part of the architecture that is pure prompt — there is no module to install. A memory
system has an always-loaded core and a much larger body that streams on demand, and the split is
forced: the core is read in full every session and competes with the actual work for context, so it
has to stay small. Everything else is reachable and not present.

**The failure that produces is specific and quiet.** The agent thinks *"I don't have anything on
that"* — and that thought is generated by looking at its context, not its memory. Absent-from-context
and absent-from-disk are indistinguishable from the inside. There is no error, no gap, no sense of
something missing; there is a confident, comfortable blank.

Which is why the instruction is phrased as a trigger on the feeling rather than a rule about
retrieval. **The moment of "I don't think there's anything on this" is the single highest-value
moment to run a search**, and it is precisely the moment nothing prompts you to.

### "Correct or delete it"

The most dangerous file in a memory system is a confidently-worded one that is out of date, because
retrieval works and the agent trusts what it retrieves. A wrong memory does not degrade gracefully —
it *outranks* fresh reasoning. Deletion is maintenance, not loss.

---

## What this file does not cover

The diagram this template is drawn from includes a retrieval pipeline with several engines, chunking,
a persistent index, and a semantic fallback. **Those are not in this repository.** What ships here is
the keyword engine, the file format, and an honest benchmark.

If you build the rest, the instructions above still apply unchanged — they are about *when* and
*whether*, and those questions do not get easier when the retrieval gets smarter. They get more
important, because a better engine returns a plausible answer more often.
