---
name: timezone-stored-as-local
description: Timestamps in the events table are local time with no offset, before 2024-06
metadata:
  type: reference
---

Rows written before the 2024-06 cutover have no timezone information. They are local to whichever server wrote them, and two of those servers were in different regions.

Anything aggregating across that boundary needs the server_id to disambiguate. There is no way to recover the offset from the row alone.
