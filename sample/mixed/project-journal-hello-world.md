---
name: project-journal-hello-world
description: Project journal - why the first file committed was a program that does nothing, and why it cannot be found
metadata:
  type: project
---

First commit was the tiny program, before any real code, and the reviewer asked why the repository
opens with something that does nothing.

Because it is not a program, it is an **instrument**. It measures one thing: whether the environment
can run anything at all. When the real build fails at 2am, it separates *the toolchain is broken*
from *my code is broken* - two failures that look identical from outside and are almost always
diagnosed as the second one, expensively.

**What this journal actually exists to record is that the program cannot be found.**

The retrieval tools index markdown only. The program sits in the same folder as every note and is
invisible to every query. No error, no warning; it simply never appears. That is not a bug - the
index is a notes index, not a code search - but it is a **silent** limit, and silent limits get
discovered by someone concluding the search is broken.

So: **a note is how a non-markdown artifact becomes findable.** This file is the handle for that
program. Anything in a corpus that is not markdown needs one, or it is not in the corpus at all. It
is merely in the folder.
