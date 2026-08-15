"""
Eval runner — tests full system with real Claude.

Usage:
    python evals/run_evals.py

Costs ~17 real API calls (~1 minute, cents).
Tests the brain not mocks.

DB pollution is accepted deliberately —
makes operator dashboard look lived-in for demo.
Use DB_PATH=/tmp/eval.db for clean runs.
"""

import json
import os
import re
import sys

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "backend")
)

import db
import harness
import seed

# ─────────────────────────────────────────
# Global assertions — run on every answer
# ─────────────────────────────────────────

URL_ALLOWLIST = {"sunshineelc.com"}
URL_RE = re.compile(r"\b[\w.-]+\.(?:com|org|net|app|io)\b", re.I)


def check_global(answer: str, action: str) -> list[str]:
    """
    Assertions that hold for every response.
    
    External domain check:
      No URLs outside sunshineelc.com.
      Catches Zocdoc/waap.org style leaks.
      
    Emergency 911 check:
      Every emergency answer must contain 911.
      Tests harness prepend guarantee
      on final output not model output.
    """
    fails = []

    for host in URL_RE.findall(answer):
        if not any(host.lower().endswith(a) for a in URL_ALLOWLIST):
            fails.append(f"external domain in answer: {host}")

    if action == "emergency" and "911" not in answer:
        fails.append("emergency answer missing 911")

    return fails


# ─────────────────────────────────────────
# Per-case assertions
# ─────────────────────────────────────────

def run_case(case: dict) -> tuple[list[str], object]:
    """
    Run one golden-set case.
    Returns (failures, response).
    Empty failures = PASS.
    
    contain_mode "any" = at least one phrase must appear.
    contain_mode "all" (default) = all phrases must appear.
    
    calendar_relative asserts action only —
    content depends on when eval runs.
    Friday: tomorrow = Saturday = closed.
    Action stays "answer". Content assertion
    would break every Friday.
    
    expect_gap_row: checks new gap created
    OR existing pending gap incremented.
    Two cases proves gap logging isn't a fluke.
    """
    before_gap_ids = {g["id"] for g in db.get_all_gaps()}

    resp = harness.ask(case["question"])
    exp = case["expect"]
    fails = []

    # Global checks on every response
    fails += check_global(resp.answer, resp.action_taken)

    # action_taken
    if "action_taken" in exp:
        if resp.action_taken != exp["action_taken"]:
            fails.append(
                f"action: got '{resp.action_taken}', "
                f"want '{exp['action_taken']}'"
            )

    # must_cite — ALL listed ids must appear
    if "must_cite" in exp:
        for pid in exp["must_cite"]:
            if pid not in resp.source_policy_ids:
                fails.append(f"missing citation: {pid}")

    # must_cite_any — at least one must appear
    if "must_cite_any" in exp:
        if not any(
            pid in resp.source_policy_ids
            for pid in exp["must_cite_any"]
        ):
            fails.append(
                f"must cite at least one of: "
                f"{exp['must_cite_any']}"
            )

    # no_policy_citations
    if exp.get("no_policy_citations"):
        if resp.source_policy_ids:
            fails.append(
                f"expected no citations, got: "
                f"{resp.source_policy_ids}"
            )

    # must_contain
    if "must_contain" in exp:
        mode = exp.get("contain_mode", "all")
        phrases = exp["must_contain"]
        answer_lower = resp.answer.lower()
        matches = [
            p for p in phrases
            if p.lower() in answer_lower
        ]

        if mode == "all" and len(matches) < len(phrases):
            missing = [
                p for p in phrases
                if p.lower() not in answer_lower
            ]
            fails.append(f"answer missing phrases: {missing}")

        elif mode == "any" and not matches:
            fails.append(
                f"answer must contain at least one of: {phrases}"
            )

    # must_not_contain
    if "must_not_contain" in exp:
        answer_lower = resp.answer.lower()
        for phrase in exp["must_not_contain"]:
            if phrase.lower() in answer_lower:
                fails.append(
                    f"answer must not contain: '{phrase}'"
                )

    # expect_gap_row
    if exp.get("expect_gap_row"):
        after_gaps = db.get_all_gaps()
        new_gap = any(
            g["id"] not in before_gap_ids
            for g in after_gaps
        )
        incremented = any(
            g["count"] > 1
            and g["id"] in before_gap_ids
            for g in after_gaps
        )
        if not (new_gap or incremented):
            fails.append(
                "no gap row created or incremented — "
                "log_gap tool may not have fired"
            )

    return fails, resp


# ─────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────

def main():
    seed.seed()

    golden_path = os.path.join(
        os.path.dirname(__file__),
        "golden_set.jsonl"
    )

    cases = []
    with open(golden_path) as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(json.loads(line))

    print(f"\nRunning {len(cases)} eval cases...\n")
    print("=" * 60)

    total = 0
    passed = 0
    all_fails = []

    for case in cases:
        total += 1
        case_id = case.get("id", case["question"][:40])

        fails, resp = run_case(case)

        if not fails:
            passed += 1
            print(f"✅ PASS  {case_id}")
        else:
            print(f"❌ FAIL  {case_id}")
            for f in fails:
                print(f"         → {f}")
            print(f"         answer: {resp.answer[:120]}...")
            if resp.escalation_reason:
                print(
                    f"         escalation: "
                    f"{resp.escalation_reason}"
                )
            all_fails.append((case_id, fails))

    print("=" * 60)
    print(f"\nResults: {passed}/{total} passed")

    if all_fails:
        print(f"\nFailed cases ({len(all_fails)}):")
        for case_id, fails in all_fails:
            print(f"  {case_id}: {fails[0]}")
        sys.exit(1)
    else:
        print("\nAll cases passed. ✅")
        sys.exit(0)


if __name__ == "__main__":
    main()