---
name: feature-flag-defaults-differ-by-environment
description: Flags default OFF in production and ON in staging, which inverts what staging tests
metadata:
  type: reference
---

The flag service falls back to the compiled-in default when it cannot reach the config store. That default was set per-environment, so staging exercises the new path and production exercises the old one.

This means a staging soak test proves nothing about the production code path during an outage of the config store, which is exactly when the fallback matters.
