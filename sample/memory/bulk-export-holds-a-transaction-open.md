---
name: bulk-export-holds-a-transaction-open
description: A read-only report caused write timeouts across the application
metadata:
  type: feedback
---

The nightly export ran one long SELECT inside a transaction. It took eleven minutes, held a snapshot, and caused vacuum to stall, which caused writes elsewhere to slow to a crawl.

**Why:** read-only is not the same as harmless. The cost was the duration, not the operation.

**How to apply:** batch large reads by primary key range, committing between batches.
