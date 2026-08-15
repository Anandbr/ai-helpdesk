from datetime import date_type, datetime
from typing import Literal, Optional
from pydantic import BaseModel, model_validator

ActionTaken = Literal[
    "answer",
    "answer_then_flag",
    "escalate",
    "off_topic",
    "emergency"
]

Confidence = Literal[
    "high",
    "medium",
    "low"
]

Sensitivity = Literal[
    "normal",
    "sensitive"
]

class Policy(BaseModel):
    id: str
    topic: str
    title: str
    content: str
    action: Literal["answer", "answer_then_flag", "escalate"]
    sensitivity: Sensitivity
    escalation_contact: Optional[str] = None
    last_verified: date_type
    expires: Optional[date_type] = None

    @model_validator(mode="after")
    def check_invariants(self):
        if self.action == "escalate" and not self.escalation_contact:
            raise ValueError(
                f"{self.id}: action 'escalate' requires escalation_contact"
            )
        if self.sensitivity == "sensitive" and self.action != "escalate":
            raise ValueError(
                f"{self.id}: sensitive policies must always escalate"
            )
        return self

class PolicyCreate(BaseModel):
    id: Optional[str] = None
    topic: str
    title: str
    content: str
    action: Literal["answer", "answer_then_flag", "escalate"]
    sensitivity: Sensitivity = "normal"
    escalation_contact: Optional[str] = None
    last_verified: Optional[date_type] = None
    expires: Optional[date_type] = None

class PolicyUpdate(BaseModel):
    """
    PATCH semantics — all fields optional.
    Send only what changed.
    sensitivity deliberately omitted —
    demoting a sensitive policy is too
    consequential for a casual edit.
    Requires code change and deliberate review.
    """
    title: Optional[str] = None
    content: Optional[str] = None
    action: Optional[
        Literal["answer", "answer_then_flag", "escalate"]
    ] = None
    escalation_contact: Optional[str] = None
    expires: Optional[date_type] = None

class Closure(BaseModel):
    id: Optional[int] = None
    name: str
    date: Optional[date_type] = None
    start: Optional[date_type] = None
    end: Optional[date_type] = None

    @model_validator(mode="after")
    def check_shape(self):
        has_single = self.date is not None
        has_range = (
            self.start is not None and self.end is not None
        )
        has_partial = (
            self.start is not None or self.end is not None
        ) and not has_range

        if has_single and has_range:
            raise ValueError(
                f"Closure '{self.name}: provide date or start+end not both"
            )
        if not has_single and not has_range:
            raise ValueError(
                f"Closuer '{self.name}' must provide date or start+end"
            )
        if has_partial:
            raise ValueError(
                f"Closure '{self.name}' start and not both must be present"
            )
        if has_range and self.end < self.start:
            raise ValueError(
                f"Closure '{self.name}: end must be on or after start"
            )
        return self

# TODO: this check can be added in db.py as simple sql query
    # def contains(self, check_date: date_type) -> bool:
    #     if self.date:
    #         return self.date == check_date
    #     return self.start <= check_date <= self.end

class AgentResponse(BaseModel):
    answer: str
    source_policy_ids: list[str]
    action_taken: ActionTaken
    confidence: Confidence
    escalation_reason: Optional[str] = None
    escalation_contact: Optional[str] = None

    @model_validator(model="after")
    def check_escalation(self):
        if(
            self.action_taken in ("escalate", "emergency")
            and not self.escalation_reason
        ):
            raise ValueError(
                f"action_taken='{self.action_taken}' requires escalation_reason"
            )
        if(
            self.action_taken in ("off_topic", "emergency")
            and self.source_policy_ids
        ):
            raise ValueError(
                f"acion_taken='{self.action_taken}' should not cite policy ids"
            )
        return self

class QuestionLog(BaseModel):
    id: Optional[int] = None
    question: str
    answer: str
    source_policy_ids: list[str]
    action_taken = ActionTaken
    confidence = Confidence
    escalation_reason = Optional[str] = None
    timestamp: datetime = datetime.now()

class GapEntry(BaseModel):
    id: Optional[int] = None
    question_log_id: int
    question: str
    normalized_question: str
    count: int = 1
    status: Literal["pending", "approved", "dismissed"] = "pending"
    operator_note: Optional[str] = None
    created_at: datetime = datetime.now()
    resolved_at: Optional[datetime] = None
