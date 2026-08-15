# AI Front Desk — Submission Doc

**Live URL:** https://brightwheel-takehome-production.up.railway.app
**Operator PIN:** 1234
**Repo:** https://github.com/Anandbr/brightwheel-ai-helpdesk.git

---

## Problem

Daycare administrators spend hours answering the same parent questions every day.
Parents are anxious and want instant answers. Operators are busy and can't always respond.

We built an AI front desk that answers routine questions instantly, escalates sensitive ones
to staff, and logs everything so operators can see what parents are asking and improve the
system over time.

---

## What I Built

Two views. Two users.

Parent view: chat interface where parents ask questions and get trusted answers grounded in the school's knowledge base. 
Citation chips show which policy was used. Escalation bannersshow who to contact. Emergency responses lead with 911.

Operator view: staff control panel with three tabs — 
All Questions (sortable by urgency),
Improvement Queue (gaps the AI couldn't answer, sorted by how many parents asked), 
and KnowledgeBase (edit policies, add new ones, see expiring ones).

---

## Three-Layer Trust Architecture

The system has three layers working together:

Layer 1 — Prompt:
  Teaches Claude the mechanism.
  When to escalate, how to flag,
  what off-topic means.
  Owns phrasing and tone.

Layer 2 — Harness:
  Mechanical guarantees in code.
  _enforce_flag upgrades answer →
  answer_then_flag when cited policy requires it. Deterministic. Never flakes.
  _enforce_sensitivity overrides to escalate hen a sensitive policy is cited.
  Emergency prepend adds 911 banner in code ot in the prompt.

Layer 3 — Evals:
  17 golden-set cases hit real Claude.
  Two clean passes = freeze criterion.
  Global assertions on every response:
  no external URLs, 911 in emergencies.

---

## The Gap-to-Policy Loop

This is the flywheel that makes the system improve over time:

1. Parent asks "Do you offer swim classes?"
2. AI can't answer → calls log_gap tool
3. Gap appears in operator Improvement Queue
4. Operator clicks Approve, writes the answer
5. New policy created in knowledge base
6. Next parent asks same question
7. AI answers correctly with citation

Without this loop the AI keeps failing on the same questions forever.
With it, the system gets smarter from real parent questions.

---

## Key Decisions

Why RAG not vector search:
  16 policies fit in context window.
  Full load gives Claude access to all action fields needed for correct routing.
  RAG would miss sensitive policy escalation rules if the wrong chunks were retrieved.

Why SQLite not Postgres:
  Right-sized for prototype. Same SQL queries map directly to Postgres.
  Would change only the connection string.

Why tools are markers not side effects:
  escalate() and log_gap() return dicts but do nothing. 
  Harness reads which tools fired after full response validation.
  Prevents duplicate side effects on retry.

Why _enforce_flag is in code not prompt:
  Prompt instructions for action mapping fail nondeterministically. 
  Proven by tuition question flipping between runs.
  Mechanical guarantees belong in code.

Why every exit goes through _finalize:
  Invariant: every question = exactly one
  log row no matter what path was taken.
  Fallbacks are visible to operators.
  A parent told "staff will follow up" must produce a record staff can act on.

---

## What I'd Add With More Time

1. Handbook upload and parsing pipeline (seed_kb.json is a prototype stand-in)
2. Vector embeddings for semantic gap dedup (basic normalization misses synonyms)
3. Real authentication (JWT, RBAC, audit log)
4. Voice input for parents calling by phone
5. WhatsApp/SMS integration
6. Soft delete for policies
7. Multi-language support (many parents speak Spanish)

---

## Eval Discipline

Single-run evals on a stochastic system produce samples not verdicts.

Triage rule:
  Deterministic failures (2/2 runs) = bug in prompt or harness. Fix the system.
  
  Intermittent failures (1/2 runs) = either real-but-flaky behavior(patch the prompt, keep the assertion)
  or brittle assertion (fix the eval).

We hit all three species in the first two eval runs.

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