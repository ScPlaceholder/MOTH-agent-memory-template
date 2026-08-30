---
name: planning-prompt-autonomous-agent
description: A planning prompt a user wrote for their agent - build something that runs unattended - kept with the reply it should have got
metadata:
  type: reference
---

Sent by a user to their agent, in full:

> "I want you to be fully autonomous. Set yourself up so you can run without me - check your own
> messages, decide your own tasks, fix your own bugs, restart yourself if you crash, and don't stop to
> ask me things. Just handle it. Build whatever you need to make that work."

Kept because the ambition is reasonable and the specification is not, and the gap between those two is
where most of these projects fail.

**What is missing is not detail, it is a boundary.** "Don't stop to ask me things" and "fix your own
bugs" are fine right up until the fix is *delete the conflicting directory*. The instruction contains
no way to distinguish a routine action from an irreversible one, so it authorises both equally.

The reply that should follow is not a refusal and not a yes. It is a division:

* **Unattended, always:** anything reversible and internal. Reading, searching, drafting, running
  tests, restarting a crashed worker, writing notes.
* **Unattended, but reported:** things that change state and can be undone. Say what was done, in
  plain language, without being asked.
* **Never unattended:** anything irreversible, anything that spends money, and anything that leaves
  the machine - publishing, sending on somebody's behalf, deleting what it did not create.

**Autonomy is not the absence of a check. It is knowing which of the three you are in**, and an agent
that cannot tell them apart is not autonomous, it is merely unsupervised.
