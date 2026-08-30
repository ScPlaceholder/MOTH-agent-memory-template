---
name: hello-world-in-the-build-image
description: The minimal program used to verify the toolchain before debugging anything else
metadata:
  type: reference
---

When a build fails in a strange way, compile and run the smallest possible program in the same image first.

It separates 'the toolchain is broken' from 'my code is broken', which otherwise look identical and get diagnosed as the second one for hours.
