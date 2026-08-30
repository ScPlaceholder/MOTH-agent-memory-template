---
name: example-measure-before-optimising
description: Profiling showed the cost was in a function nobody suspected, after an afternoon spent tuning the wrong one
metadata:
  type: feedback
---

An endpoint was slow. The obvious suspect was a nested loop, so that got rewritten. No change.
Profiling afterwards put 80% of the time in a logging call inside the retry wrapper.

**Why:** the guess felt informed — the loop *looked* expensive — and looking informed is exactly
what stops you measuring.

**How to apply:** profile first even when the cause seems obvious, and especially then. If the fix
does not move the number, the diagnosis was wrong; do not tune the same guess harder.

Related: [[example-empty-is-not-clean]]
