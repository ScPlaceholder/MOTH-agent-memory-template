---
name: example-empty-is-not-clean
description: A check that returns nothing may mean "all clear" or "never ran" - and those need opposite responses
metadata:
  type: feedback
---

A nightly job wrote its findings to a report file. An empty report was read as "no problems found".
The job had been failing to start for nine days; the file was empty because nothing wrote to it.

**Why:** absence of output and absence of problems are indistinguishable from the output alone, and
the reassuring reading requires no further work — so it wins by default.

**How to apply:** make checks say which case they are in. "0 issues found in 412 files" and
"could not run" are different sentences. Never let a tool print nothing and mean success.

Related: [[example-measure-before-optimising]]
