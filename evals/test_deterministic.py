import sys
import os
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "backend")
)

from models import Policy, PolicyCreate, Closure, AgentResponse, GapEntry
from harness import _enforce_flag, _enforce_sensitivity
from datetime import date
import tools
import pytest
import seed

# ─────────────────────────────────────────
# Policy model validators
# ─────────────────────────────────────────

seed.seed()
def test_policy_escalate_requires_contact():
    try:
        Policy(
            id="test",
            topic="test",
            title="Test",
            content="Test content",
            action="escalate",
            sensitivity="normal",
            escalation_contact=None,
            last_verified=date.today(),
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_policy_flag_no_contact_required():
    p = Policy(
        id="test",
        topic="test",
        title="Test",
        content="Test content",
        action="answer_then_flag",
        sensitivity="normal",
        escalation_contact=None,
        last_verified=date.today(),
    )
    assert p.action == "answer_then_flag"

def test_policy_sensitive_must_escalate():
    try:
        Policy(
            id="test",
            topic="test",
            title="Test",
            content="Test content",
            action="answer",
            sensitivity="sensitive",
            escalation_contact="Director",
            last_verified=date.today(),
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_policy_valid():
    p = Policy(
        id="hours_regular",
        topic="hours",
        title="Hours of Operation",
        content="We are open 7am to 6pm",
        action="answer",
        sensitivity="normal",
        escalation_contact=None,
        last_verified=date.today(),
    )
    assert p.id == "hours_regular"

    # ─────────────────────────────────────────
# Closure model validators
# ─────────────────────────────────────────

def test_closure_single_date_valid():
    c = Closure(name="Labor Day", date=date(2026, 9, 7))
    assert c.date == date(2026, 9, 7)

def test_closure_range_valid():
    c = Closure(
        name="Winter Break",
        start=date(2026, 12, 24),
        end=date(2027, 1, 1),
    )
    assert c.start == date(2026, 12, 24)
    assert c.end == date(2027, 1, 1)

def test_closure_rejects_both():
    try:
        Closure(
            name="Bad",
            date=date(2026, 9, 7),
            start=date(2026, 9, 7),
            end=date(2026, 9, 8),
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_closure_rejects_neither():
    try:
        Closure(name="Bad")
        assert False, "should have raised"
    except Exception:
        pass

def test_closure_rejects_partial_range():
    try:
        Closure(
            name="Bad",
            start=date(2026, 9, 7),
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_closure_rejects_end_before_start():
    try:
        Closure(
            name="Bad",
            start=date(2026, 9, 8),
            end=date(2026, 9, 7),
        )
        assert False, "should have raised"
    except Exception:
        pass

# ─────────────────────────────────────────
# AgentResponse model validators
# ─────────────────────────────────────────

def test_agent_response_escalate_requires_reason():
    try:
        AgentResponse(
            answer="Please contact staff",
            source_policy_ids=[],
            action_taken="escalate",
            confidence="high",
            escalation_reason=None,
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_agent_response_emergency_requires_reason():
    try:
        AgentResponse(
            answer="Call 911",
            source_policy_ids=[],
            action_taken="emergency",
            confidence="high",
            escalation_reason=None,
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_agent_response_off_topic_no_citations():
    try:
        AgentResponse(
            answer="Outside my scope",
            source_policy_ids=["some_policy"],
            action_taken="off_topic",
            confidence="high",
            escalation_reason=None,
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_agent_response_emergency_no_citations():
    try:
        AgentResponse(
            answer="Call 911",
            source_policy_ids=["some_policy"],
            action_taken="emergency",
            confidence="high",
            escalation_reason="child in danger",
        )
        assert False, "should have raised"
    except Exception:
        pass

def test_agent_response_valid_answer():
    r = AgentResponse(
        answer="We are open 7am to 6pm",
        source_policy_ids=["hours_regular"],
        action_taken="answer",
        confidence="high",
        escalation_reason=None,
    )
    assert r.action_taken == "answer"
    assert r.source_policy_ids == ["hours_regular"]

# ─────────────────────────────────────────
# check_calendar tool
# ─────────────────────────────────────────

def test_calendar_saturday_closed():
    result = tools.check_calendar("2026-09-05")
    assert result["open"] is False
    assert "Weekend" in result["reason"]

def test_calendar_sunday_closed():
    result = tools.check_calendar("2026-09-06")
    assert result["open"] is False
    assert "Weekend" in result["reason"]

def test_calendar_invalid_date():
    result = tools.check_calendar("not-a-date")
    assert "error" in result

def test_calendar_wrong_format():
    result = tools.check_calendar("09/05/2026")
    assert "error" in result

def test_calendar_weekday_open():
    # Regular Monday with no closure
    result = tools.check_calendar("2026-09-14")
    assert result["open"] is True

def test_calendar_labor_day_closed():
    # Labor Day 2026
    result = tools.check_calendar("2026-09-07")
    assert result["open"] is False
    assert "Labor Day" in result["reason"]

def test_calendar_winter_break_closed():
    # Inside Winter Break range
    result = tools.check_calendar("2026-12-28")
    assert result["open"] is False
    assert "Winter Break" in result["reason"]

def test_calendar_day_before_winter_break():
    # Dec 23 — not yet in Winter Break
    result = tools.check_calendar("2026-12-23")
    assert result["open"] is True

# ─────────────────────────────────────────
# _enforce_flag
# ─────────────────────────────────────────

def _make_response(**kwargs):
    defaults = {
        "answer": "Test answer",
        "source_policy_ids": [],
        "action_taken": "answer",
        "confidence": "high",
        "escalation_reason": None,
        "escalation_contact": None,
    }
    defaults.update(kwargs)
    return AgentResponse(**defaults)

def _make_policy(pid, action="answer", sensitivity="normal"):
    return {
        "id": pid,
        "topic": "test",
        "title": "Test",
        "content": "Test content",
        "action": action,
        "sensitivity": sensitivity,
        "escalation_contact": "Director" if action == "escalate" else None,
        "last_verified": "2026-08-01",
    }

def test_enforce_flag_upgrades_answer():
    resp = _make_response(
        action_taken="answer",
        source_policy_ids=["illness_exclusion"]
    )
    policies = [_make_policy("illness_exclusion", "answer_then_flag")]
    result = _enforce_flag(resp, policies)
    assert result.action_taken == "answer_then_flag"
    assert result.escalation_reason is not None

def test_enforce_flag_leaves_escalate_alone():
    resp = _make_response(
        action_taken="escalate",
        source_policy_ids=["billing_disputes"],
        escalation_reason="billing matter",
    )
    policies = [_make_policy("billing_disputes", "answer_then_flag")]
    result = _enforce_flag(resp, policies)
    assert result.action_taken == "escalate"

def test_enforce_flag_no_change_when_policy_is_answer():
    resp = _make_response(
        action_taken="answer",
        source_policy_ids=["tuition_rates"]
    )
    policies = [_make_policy("tuition_rates", "answer")]
    result = _enforce_flag(resp, policies)
    assert result.action_taken == "answer"

def test_enforce_flag_no_change_when_already_flagged():
    resp = _make_response(
        action_taken="answer_then_flag",
        source_policy_ids=["illness_exclusion"],
        escalation_reason="already flagged",
    )
    policies = [_make_policy("illness_exclusion", "answer_then_flag")]
    result = _enforce_flag(resp, policies)
    assert result.action_taken == "answer_then_flag"

# ─────────────────────────────────────────
# _enforce_sensitivity
# ─────────────────────────────────────────

def test_enforce_sensitivity_overrides_to_escalate():
    resp = _make_response(
        action_taken="answer",
        source_policy_ids=["custody_court_orders"]
    )
    policies = [{
        "id": "custody_court_orders",
        "topic": "safety",
        "title": "Custody & Court Orders",
        "content": "We follow court orders exactly.",
        "action": "escalate",
        "sensitivity": "sensitive",
        "escalation_contact": "Director Maria Torres",
        "last_verified": "2026-08-01",
    }]
    result = _enforce_sensitivity(resp, policies)
    assert result.action_taken == "escalate"
    assert "Director Maria Torres" in result.answer
    assert result.escalation_reason is not None
    assert "sensitive policy override" in result.escalation_reason

def test_enforce_sensitivity_leaves_normal_alone():
    resp = _make_response(
        action_taken="answer",
        source_policy_ids=["tuition_rates"]
    )
    policies = [{
        "id": "tuition_rates",
        "topic": "billing",
        "title": "Tuition Rates",
        "content": "Monthly tuition rates here.",
        "action": "answer",
        "sensitivity": "normal",
        "escalation_contact": None,
        "last_verified": "2026-08-01",
    }]
    result = _enforce_sensitivity(resp, policies)
    assert result.action_taken == "answer"

def test_enforce_sensitivity_contact_fallback():
    resp = _make_response(
        action_taken="answer",
        source_policy_ids=["bad_policy"]
    )
    policies = [{
        "id": "bad_policy",
        "topic": "safety",
        "title": "Bad Policy",
        "content": "Content here.",
        "action": "escalate",
        "sensitivity": "sensitive",
        "escalation_contact": None,
        "last_verified": "2026-08-01",
    }]
    result = _enforce_sensitivity(resp, policies)
    assert result.action_taken == "escalate"
    assert "(206) 555-0123" in result.answer

def test_enforce_sensitivity_already_escalated():
    resp = _make_response(
        action_taken="escalate",
        source_policy_ids=["authorized_pickup"],
        escalation_reason="already escalated",
    )
    policies = [{
        "id": "authorized_pickup",
        "topic": "safety",
        "title": "Authorized Pickup",
        "content": "Only authorized adults.",
        "action": "escalate",
        "sensitivity": "sensitive",
        "escalation_contact": "Front desk",
        "last_verified": "2026-08-01",
    }]
    result = _enforce_sensitivity(resp, policies)
    assert result.action_taken == "escalate"
    assert result.escalation_reason == "already escalated"

# ─────────────────────────────────────────
# Runner
# ─────────────────────────────────────────

if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))