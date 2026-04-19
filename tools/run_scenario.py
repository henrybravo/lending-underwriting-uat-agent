"""
Execute complete UAT validation for one scenario:
generate synthetic applicant -> run through decision engine -> compare against expected outcome
"""

from tools.generate_synthetic_applicant import generate_synthetic_applicant
from tools.evaluate_application import evaluate_application
from tools.compare_decisions import compare_decisions


def run_scenario(scenario_type: str, expected: str, params: dict | None = None) -> dict:
    """
    Execute a complete UAT validation for one scenario: generate synthetic applicant, 
    run through decision engine, compare against expected outcome.
    
    Args:
        scenario_type: Scenario name (e.g., "standard_approval", "dti_at_36_boundary")
        expected: Expected decision (AUTO_APPROVE, MANUAL_REVIEW, AUTO_DENY)
        params: Optional overrides for the synthetic applicant
    
    Returns:
        Complete result containing:
        - scenario: scenario name
        - applicant: full applicant dict
        - decision: full decision dict from engine
        - comparison: pass/fail + diff
        - passed: boolean
    """
    # Step 1: Generate synthetic applicant
    applicant = generate_synthetic_applicant(scenario_type=scenario_type, params=params or {})
    
    # Step 2: Run through decision engine
    decision = evaluate_application(application=applicant)
    
    # Step 3: Compare against expected
    comparison = compare_decisions(actual=decision, expected=expected)
    
    # Return complete result
    return {
        "scenario": scenario_type,
        "applicant": applicant,
        "decision": decision,
        "comparison": comparison,
        "passed": comparison.get("passed", False),
        "expected": expected,
        "actual": decision.get("result", "UNKNOWN")
    }
