# Sunshine Early Learning Center — AI Front Desk

AI-powered front desk for daycare centers.
Built for the Brightwheel take-home assignment.

**Live demo:** https://brightwheel-takehome-production.up.railway.app
**Operator PIN:** 1234

---

## What It Does

**Parent view** (`/`)
Chat interface where parents ask questions and get trusted answers grounded in the school's knowledge base.

**Operator view** (`/operator`)
Staff control panel with three tabs:
- All Questions — full log sorted by urgency
- Improvement Queue — gaps the AI couldn't answer
- Knowledge Base — edit policies, add new ones

---

## Tech Stack
Backend: FastAPI + Python
AI: Claude claude-sonnet-4-6 (Anthropic)
Database: SQLite
Frontend: React + Vite
Deploy: Railway (Dockerfile)

---

## Running Locally

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt
cp ../.env.example .env
# Add your ANTHROPIC_API_KEY to .env
python seed.py
uvicorn main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Running Tests

**Deterministic tests (fast, no API calls):**
```bash
python evals/test_deterministic.py
```

**Eval suite (hits real Claude, ~1 min):**
```bash
python evals/run_evals.py
```

---

## Project Structure
backend/
main.py # FastAPI routes
harness.py # Agent loop, tool execution
prompts.py # System prompt
tools.py # check_calendar, escalate, log_gap
db.py # SQLite queries
models.py # Pydantic models
seed.py # Data loader
data/
seed_kb.json # 16 policies, 6 closures

frontend/
src/
App.jsx # Routing + PIN gate
ParentView.jsx # Chat interface
OperatorView.jsx # Staff dashboard
components/
Message.jsx # Chat bubbles + citations

evals/
test_deterministic.py # Unit tests, 31 cases
run_evals.py # Integration tests, 17 cases
golden_set.jsonl # Expected behaviors

DECISIONS.md # Architecture decisions + submission doc
Dockerfile # Multi-stage build

---

## Key Decisions

See `DECISIONS.md` for full reasoning.

- **Thin harness, fat skills** 
  AI handles natural language only. All deterministic work done in code.
  
- **Tools as markers** 
  escalate() and log_gap() signal intent to the harness. Side effects
  happen post-validation, never during tool calls.
  
- **_enforce_flag in code** 
  policy action → action_taken mapping is deterministic.
  Prompt instructions for this failed nondeterministically. Code owns the enum.
  
- **Every exit through _finalize** 
  every question produces exactly one log row regardless of
  what path was taken. Fallbacks are visible.