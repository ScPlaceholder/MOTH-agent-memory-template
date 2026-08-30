---
name: retry-storm-took-down-the-queue
description: A client retrying on failure amplified a brief outage into a two-hour one
metadata:
  type: feedback
---

The upstream service returned 503 for ninety seconds. Every client retried immediately, three times, so the recovering service met four times its normal load and fell over again.

**Why:** each client behaved reasonably in isolation. The failure only exists in aggregate.

**How to apply:** exponential backoff with jitter, and a cap on total attempts. A retry policy that is correct for one caller can still be a denial-of-service attack from a thousand.
