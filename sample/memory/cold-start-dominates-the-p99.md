---
name: cold-start-dominates-the-p99
description: The p99 latency is container startup, not request handling (measured 2024-11-03)
metadata:
  type: project
---

Profiling showed request handling at 40ms median and 55ms p99. The service-level p99 was 2.1s.

The gap is cold starts: the autoscaler scales to zero after five idle minutes, and traffic is bursty enough that a meaningful fraction of requests hit a cold container.

Optimising the handler cannot move this number. Either keep one warm instance or accept it.
