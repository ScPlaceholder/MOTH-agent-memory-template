---
name: backups-were-never-restored
description: Nine months of backups that had never once been read back
metadata:
  type: feedback
---

The backup job ran nightly and reported success. The first restore attempt failed: the archives were valid but the schema dump excluded sequences, so the restored database could not accept writes.

**Why:** the backup job verified that it had WRITTEN a file, which is not the same as verifying that the file can bring a system back.

**How to apply:** restore into a scratch environment on a schedule. An untested backup is a hypothesis.
