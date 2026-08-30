---
name: the-linter-was-disabled-in-ci
description: A quality gate that had been silently skipping for four months
metadata:
  type: feedback
---

The lint step ran with a flag that made it exit 0 on findings. Nobody noticed because the job was green and the findings scrolled past in a collapsed log section.

**Why:** a check that cannot fail looks identical to a check that passes.

**How to apply:** assert that the gate CAN fail. Commit a deliberate violation once, confirm red, revert. A gate nobody has ever seen fail is not known to work.
