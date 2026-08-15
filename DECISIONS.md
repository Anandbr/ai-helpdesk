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

  
## Gap approval title collision

When operator approves a gap and types a title that slugifies to an existing policy id, we return a 409 error.

Assumption:
  We tell the operator the policy exists and ask them to edit it instead.

Production improvement:
  Before showing the approval form, check for similar existing policies and surface them to the operator.
  Prevent the collision before it happens rather than erroring after.

  ## Weekend closure hardcoded in check_calendar

We assume the school is always closed on Saturdays and Sundays.

This is hardcoded in tools.py:
  if d.weekday() >= 5: return closed

Not configurable by the operator.

Assumption:
  Standard daycare is Mon-Fri only.
  
Production improvement:
  Add operating_days field to school configuration table.
  check_calendar reads operating days from DB instead of hardcoding weekdays.
  Schools with Saturday programs could configure this themselves.

## Authentication — PIN vs Login

Current: single PIN stored in sessionStorage. Clears when browser tab closes.
Operator must re-enter PIN each new session.

Assumption:
  PIN is for a prototype demo. Simple to implement and explain.

Production:
  Replace PIN with proper authentication:
  - Email/password login
  - JWT tokens with expiry
  - Role-based access control (admin vs teacher vs owner)
  - Audit log of who changed what policy
  - Multi-factor authentication for sensitive operations like custody policies

## Hand-rolled routing vs React Router

We have exactly 2 routes: / and /operator.
React Router earns its keep at 3+ routes or nested navigation.

For 2 routes: window.location.pathname check + history.pushState + popstate listener = ~20 lines, zero dependencies.

Upgrade path: adding a third route (teacher view, analytics, etc.) is the threshold to add
React Router. Refactor is straightforward — wrap in BrowserRouter, replace pathname checks with Route components.

## No policy deletion

Intentional omission.
Deletion risks:
  - Breaking citation links in question logs
  - Accidental removal with no undo
  - Especially dangerous for safety policies

Production approach:
  - Soft delete — mark policy as inactive
  - Policy stays in DB, not shown to AI or parents
  - Can be restored if needed
  - Or archive flow with confirmation step