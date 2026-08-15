# DECISIONS.md

This document captures design decisions, tradeoffs, and assumptions made during the prototype. Each entry explains what
we chose, why, and what we'd do differently in production.

---

## Gap Dedup — Normalized Question

**What we do:**
Normalize question text with basic Python:
lowercase, strip punctuation, collapse whitespace.

**Why:**
Simple, fast, no API cost, no latency.
Sufficient for a prototype demo.

**Assumption:**
Parents asking the same question will use similar enough wording that basic normalization catches the duplicate.

**Production reality:**
"Do you offer swim classes?" and "When do summer swimming sessions start?"
are semantically the same gap but basic normalization won't catch it.

**In production:**
Use an embedding model to convert questions to vectors. Cluster similar vectors.
One cluster = one gap regardless of wording.
Or use Claude to classify incoming questions against existing gap categories before deciding to create a new one.

---
## PolicyUpdate omits sensitivity field

Operators cannot change a policy's sensitivity via the PATCH endpoint.

Why:
  Demoting a policy from sensitive to normal means a custody or safety policy could stop escalating automatically.
  Too consequential for a casual UI edit.

Assumption:
  We assume sensitivity is set correctly at policy creation and rarely needs changing.
  
In production:
  Sensitivity changes require a code change and deliberate review by an admin.
  Could add a separate admin-only endpoint with additional confirmation step.