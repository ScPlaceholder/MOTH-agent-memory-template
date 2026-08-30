---
name: the-migration-ran-twice
description: An idempotency assumption that held in testing and not in production
metadata:
  type: feedback
---

A deploy script applied the schema change, timed out waiting for confirmation, and was re-run by hand. The second run doubled every row in the join table.

**Why:** the migration was written as a sequence of INSERTs, which is only idempotent if you never run it twice, which is another way of saying it is not idempotent.

**How to apply:** every migration gets a guard clause or a unique constraint that makes the second run a no-op rather than a duplicate.
