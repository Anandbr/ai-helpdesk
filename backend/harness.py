import json
import os
import anthropic
from dotenv import load_dotenv
from contextlib import contextmanager

load_dotenv()

import db
from models import AgentResponse
from prompts import build_system_prompt
import tools as tool_impls

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"
MAX_TOOL_ITERATIONS = 3

FALLBACK_ANSWER = (
    "I want to make sure you get an accurate answer, "
    "so I've passed your question to our staff. "
    "You can also reach the front desk directly at "
    "(206) 555-0123."
)

TOOLS = [
    {
        "name": "check_calendar",
        "description": (
            "Check whether the center is open on a specific date. "
            "Use for ANY question involving a date or day — "
            "never guess open/closed status yourself."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": (
                        "ISO date YYYY-MM-DD. Resolve relative dates "
                        "like 'next Monday' yourself using today's date "
                        "before calling."
                    )
                }
            },
            "required": ["date"],
        },
    },
    {
        "name": "escalate",
        "description": (
            "Signal that this question needs a human. "
            "Use for sensitive topics, account-specific questions, "
            "or anything the policies don't cover safely."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "contact": {"type": "string"}
            },
            "required": ["reason", "contact"],
        },
    },
    {
        "name": "log_gap",
        "description": (
            "Record that the knowledge base could not answer "
            "this question, so staff can add the missing information."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string"}
            },
            "required": ["question"],
        },
    },
]

TOOL_FUNCTIONS = {
    "check_calendar": lambda inp: tool_impls.check_calendar(inp["date"]),
    "escalate": lambda inp: tool_impls.escalate(inp["reason"], inp["contact"]),
    "log_gap": lambda inp: tool_impls.log_gap(inp["question"]),
}

def _fallback_escalation(
    question: str,
    reason: str
) -> AgentResponse:
    """
    Every error path lands here.
    No code path returns a guess.
    Wrong answer worse than warm handoff
    for an anxious parent.
    """
    return AgentResponse(
        answer=FALLBACK_ANSWER,
        source_policy_ids=[],
        action_taken="escalate",
        confidence="low",
        escalation_reason=reason,
        escalation_contact="(206) 555-0123"
    )

def _finalize(
    question: str,
    agent_response: AgentResponse,
    gap_logged: bool = False
) -> AgentResponse:
    """
    Every exit in ask() goes through here.
    Invariant: every question produces exactly
    one log row no matter what path was taken.
    
    Guard with own try/except so DB failure
    during error handling can't mask
    the original error.
    """
    try:
        log_id = db.insert_question_log(
            question=question,
            answer=agent_response.answer,
            source_policy_ids=agent_response.source_policy_ids,
            action_taken=agent_response.action_taken,
            confidence=agent_response.confidence,
            escalation_reason=agent_response.escalation_reason,
        )
        if gap_logged:
            db.insert_or_increment_gap(log_id, question)
    except Exception as db_err:
        import sys
        print(
            f"[_finalize] DB write failed: {db_err}",
            file=sys.stderr
        )
    return agent_response

def _parse_and_validate(
    response,
    question: str,
    messages: list,
    system: str,
) -> AgentResponse | None:
    """
    Extract text, strip fences, validate.
    One retry with full message history preserved.
    
    Why pass messages in:
      If tools were called, tool results
      live in messages history.
      Retry needs that context or model
      must guess without calendar data etc.
      
    Returns None on double failure.
    Caller routes to _fallback_escalation.
    """
    def extract_text(r) -> str:
        for block in r.content:
            if hasattr(block, "text"):
                return block.text.strip()
        return ""

    def strip_fences(text: str) -> str:
        if text.startswith("```"):
            lines = text.split("\n")
            return "\n".join(lines[1:-1]).strip()
        return text

    text = strip_fences(extract_text(response))

    try:
        return AgentResponse.model_validate_json(text)
    except Exception as e:
        retry_messages = messages + [
            {
                "role": "assistant",
                "content": text or "(empty response)"
            },
            {
                "role": "user",
                "content": (
                    f"Your response failed validation: {e}. "
                    f"Respond with only valid JSON matching "
                    f"the schema. No markdown fences."
                )
            }
        ]

        try:
            retry = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                tools=TOOLS,
                tool_choice={"type": "none"},
                messages=retry_messages,
            )
            retry_text = strip_fences(extract_text(retry))
            return AgentResponse.model_validate_json(retry_text)
        except Exception:
            return None

def _enforce_flag(
    agent_response: AgentResponse,
    policies: list[dict]
) -> AgentResponse:
    """
    Mechanical guarantee: if any cited policy
    has action='answer_then_flag' and model
    returned 'answer', upgrade it.
    
    Why code not prompt:
      This mapping is deterministic.
      Prompt instructions fail
      nondeterministically even with
      ALL-CAPS mandatory rules.
      Mechanical guarantees belong in code.
      
    Why NOT do this for escalate:
      Escalate requires withholding the
      substance of the answer.
      Code can't retroactively fix that
      by flipping a field.
    """
    policy_map = {p["id"]: p for p in policies}

    if agent_response.action_taken == "answer" and any(
        policy_map.get(pid, {}).get("action") == "answer_then_flag"
        for pid in agent_response.source_policy_ids
    ):
        return agent_response.model_copy(update={
            "action_taken": "answer_then_flag",
            "escalation_reason": (
                "flag upgrade (harness): "
                "cited policy requires staff awareness"
            ),
        })
    return agent_response


def _enforce_sensitivity(
    agent_response: AgentResponse,
    policies: list[dict]
) -> AgentResponse:
    """
    Hard guarantee for sensitive policies.
    If any cited policy is sensitive and
    action_taken is not escalate/emergency
    → override to escalate.
    
    Honest limitation:
      Only catches CITED sensitive policies.
      If model answers custody question without
      citing the policy, this guard can't see it.
      That's why this is one of three layers:
      prompt instructs, this catches cited cases,
      eval suite catches regressions.
    """
    policy_map = {p["id"]: p for p in policies}

    for pid in agent_response.source_policy_ids:
        policy = policy_map.get(pid)
        if not policy:
            continue
        if (
            policy["sensitivity"] == "sensitive"
            and agent_response.action_taken
            not in ("escalate", "emergency")
        ):
            contact = (
                policy.get("escalation_contact")
                or "(206) 555-0123"
            )
            return agent_response.model_copy(update={
                "action_taken": "escalate",
                "escalation_reason": (
                    "sensitive policy override (harness)"
                ),
                "escalation_contact": contact,
                "answer": (
                    f"I've flagged this for {contact} as a "
                    f"priority — they'll follow up directly. "
                    f"In the meantime, here's our policy:\n\n"
                    f"{policy['content']}"
                )
            })

    return agent_response

def ask(question: str) -> AgentResponse:
    """
    Main entry point.
    
    Invariant: every question produces exactly
    one log row no matter what path was taken.
    No code path returns a guess.
    """
    try:
        policies = db.get_all_policies()
        system = build_system_prompt(
            json.dumps(policies, indent=None)
        )

        messages = [{"role": "user", "content": question}]
        gap_logged = False

        for _ in range(MAX_TOOL_ITERATIONS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason != "tool_use":
                break

            messages.append({
                "role": "assistant",
                "content": response.content
            })

            results = []
            for block in response.content:
                if block.type == "tool_use":
                    if block.name == "log_gap":
                        gap_logged = True
                    result = TOOL_FUNCTIONS[block.name](block.input)
                    results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result)
                    })

            messages.append({
                "role": "user",
                "content": results
            })

        else:
            return _finalize(
                question,
                _fallback_escalation(
                    question,
                    "tool loop limit reached"
                )
            )

        agent_response = _parse_and_validate(
            response, question, messages, system
        )

        if agent_response is None:
            return _finalize(
                question,
                _fallback_escalation(
                    question,
                    "response validation failed after retry"
                ),
                gap_logged
            )

        agent_response = _enforce_flag(agent_response, policies)
        agent_response = _enforce_sensitivity(agent_response, policies)

        if agent_response.action_taken == "emergency":
            agent_response = agent_response.model_copy(update={
                "answer": (
                    "🚨 If this is an emergency, "
                    "call 911 first.\n\n"
                    + agent_response.answer
                )
            })

        return _finalize(question, agent_response, gap_logged)

    except anthropic.APIError as e:
        return _finalize(
            question,
            _fallback_escalation(
                question,
                f"API error: {str(e)}"
            )
        )
    except Exception as e:
        return _finalize(
            question,
            _fallback_escalation(
                question,
                f"unexpected error: {str(e)}"
            )
        )
