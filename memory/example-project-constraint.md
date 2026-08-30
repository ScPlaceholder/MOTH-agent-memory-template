---
name: example-project-constraint
description: The importer must stay single-threaded until the upstream API's rate limiter is fixed (as of 2026-03-14)
metadata:
  type: project
---

Parallelising the importer looks like an easy win and has been proposed twice. The upstream API
returns 200 OK while silently dropping records above ~4 requests/second, so concurrency causes
missing data with no error anywhere.

**Why:** the failure is invisible on our side — nothing throws, and the record count is only wrong
if you go and count it.

**How to apply:** leave it serial. Revisit when upstream ships the fixed limiter; the ticket to
watch is named in the team's tracker.
