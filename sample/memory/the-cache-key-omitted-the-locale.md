---
name: the-cache-key-omitted-the-locale
description: Users in one region saw another region's prices for eleven minutes
metadata:
  type: feedback
---

The pricing cache keyed on product id and currency but not locale. Two locales share a currency, and one of them has different tax handling.

**Why:** the key encoded what the developer was thinking about, not what the value depends on.

**How to apply:** derive cache keys from the full input set of the function being cached. If an argument can change the result, it belongs in the key.
