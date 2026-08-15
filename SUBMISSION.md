# AI Front Desk — Sunshine Early Learning Center

**Live URL:** https://brightwheel-takehome-production.up.railway.app
**Operator PIN:** 1234

---

## What I Built

An AI front desk for daycare centers with two views:

**Parent view** — chat interface where parents ask questions and get answers grounded in the
school's knowledge base. Citations show which policy was used. 
Escalations name the specific staff contact. Emergencies lead with 911.

**Operator view** — staff dashboard with three tabs: 
- all questions sorted by urgency, 
- an improvement queue of questions the AI couldn't answer, and 
- a knowledge base editor.

---

## How It Works

The system has three layers:

**Prompt** owns tone and phrasing.
**Harness** owns deterministic guarantees —
if a cited policy requires escalation, code enforces it regardless of what the
model returned. Emergency 911 prepend happens in code not the prompt.
**Evals** — 17 golden-set cases hit real Claude. Two clean passes required to ship.

The key feature is the gap-to-policy loop: 
when a parent asks something the AI can'tb answer, it logs a gap. 
The operator sees it, writes an answer, and the next parent gets a cited response. 
The system gets smarter from real questions.

---

## Key Decisions

**Why full policy load not RAG:**
16 policies fit in context. RAG would miss sensitive escalation rules if wrong chunks were retrieved. 
One anxious parent getting wrong custody advice is worse than slightly higher token cost.

**Why tools are markers:**
escalate() and log_gap() do nothing themselves.
The harness reads which tools fired after validating the full response. 
Prevents duplicate side effects on retry.

**Why _enforce_flag is in code:**
Prompt instructions for action mapping failed nondeterministically. 
Mechanical guarantees belong in code not prompts.

---

## What I'd Add With More Time

1. Handbook upload and parsing pipeline (seed_kb.json is a prototype stand-in)
2. Vector embeddings for semantic gap dedup (basic normalization misses synonyms)
3. Real authentication (JWT, RBAC, audit log)
4. Voice input for parents calling by phone
5. WhatsApp/SMS integration
6. Soft delete for policies
7. Multi-language support (many parents speak Spanish)