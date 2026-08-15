import os
import re
from contextlib import asynccontextmanager
from datetime import date as date_type
from fastapi import FastAPI, Header, HTTPException, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import db
import seed
import harness
from models import (
    ChatRequest, PolicyUpdate, PolicyCreate,
    GapStatusUpdate, Policy
)

# ─────────────────────────────────────────
# Startup
# ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed.seed()
    yield

app = FastAPI(lifespan=lifespan)


# ─────────────────────────────────────────
# Operator auth
# PIN as header not query param —
# params leak into logs and browser history
# ─────────────────────────────────────────
OPERATOR_PIN = os.getenv("OPERATOR_PIN", "1234")

def require_operator(x_operator_pin: str = Header(None)):
    if x_operator_pin != OPERATOR_PIN:
        raise HTTPException(401, "operator PIN required")

# ─────────────────────────────────────────
# Public routes
# ─────────────────────────────────────────
@app.post("/api/ask")
def ask(req: ChatRequest):
    return harness.ask(req.question)

@app.get("/api/policies")
def get_policies_public():
    """
    Public endpoint — returns only display fields.
    Parents see policy content (that's the point
    of citations) but not action/sensitivity/contacts
    which are operator configuration surface.
    """
    policies = db.get_all_policies()
    return [
        {
            "id": p["id"],
            "title": p["title"],
            "content": p["content"],
            "topic": p["topic"],
        }
        for p in policies
    ]

# ─────────────────────────────────────────
# Operator routes
# APIRouter with shared dependency —
# boundary declared once, structurally
# impossible to forget on a new endpoint
# ─────────────────────────────────────────

operator = APIRouter(
    prefix="/api/operator",
    dependencies=[__import__("fastapi").Depends(require_operator)]
)

def _slugify(title: str) -> str:
    slug = title.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug

@operator.get("/policies")
def get_policies():
    return db.get_all_policies()


@operator.post("/policies")
def create_policy(body: PolicyCreate):
    """
    Create new policy from approve-gap flow.
    id slugified server-side from title.
    Validated through full Policy model
    before insert — same validate-at-boundary
    pattern as PATCH.
    """
    policy_id = body.id or _slugify(body.title)
    last_verified = body.last_verified or date_type.today()

    existing = db.get_policy(policy_id)
    if existing:
        raise HTTPException(
            409,
            f"Policy '{policy_id}' already exists. "
            f"Edit the existing policy instead."
        )

    try:
        full_policy = Policy(
            id=policy_id,
            topic=body.topic,
            title=body.title,
            content=body.content,
            action=body.action,
            sensitivity=body.sensitivity,
            escalation_contact=body.escalation_contact,
            last_verified=last_verified,
            expires=body.expires,
        )
    except Exception as e:
        raise HTTPException(422, str(e))

    db.create_policy(full_policy)
    return db.get_policy(policy_id)

@operator.patch("/policies/{policy_id}")
def patch_policy(policy_id: str, update: PolicyUpdate):
    current = db.get_policy(policy_id)
    if not current:
        raise HTTPException(404, "policy not found")

    merged = {
        **current,
        **update.model_dump(exclude_unset=True)
    }

    try:
        Policy(**merged)
    except Exception as e:
        raise HTTPException(422, str(e))

    db.update_policy(
        policy_id,
        update.model_dump(exclude_unset=True)
    )
    return db.get_policy(policy_id)

@operator.get("/questions")
def get_questions():
    return db.get_all_questions()

@operator.get("/flagged")
def get_flagged():
    return db.get_flagged_questions()

@operator.get("/gaps")
def get_gaps():
    return db.get_all_gaps()

@operator.patch("/gaps/{gap_id}")
def patch_gap(gap_id: int, update: GapStatusUpdate):
    db.update_gap_status(
        gap_id,
        update.status,
        update.operator_note
    )
    return {"status": "updated"}

@operator.get("/stale")
def get_stale():
    return db.get_stale_policies()

app.include_router(operator)

# ─────────────────────────────────────────
# Static serving — ORDER MATTERS
# API routes registered above BEFORE catch-all
# ─────────────────────────────────────────
STATIC_DIR = os.path.join(
    os.path.dirname(__file__), "static"
)

if os.path.exists(STATIC_DIR):
    app.mount(
        "/assets",
        StaticFiles(
            directory=os.path.join(STATIC_DIR, "assets")
        ),
        name="assets"
    )

    @app.get("/{path:path}")
    def spa(path: str):
        return FileResponse(
            os.path.join(STATIC_DIR, "index.html")
        )