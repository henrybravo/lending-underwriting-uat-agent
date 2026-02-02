"""
Check actual vs expected decision
"""


def compare_decisions(actual: dict, expected: str) -> dict:
    """
    Compare actual decision against expected.

    Args:
        actual: Decision dict from evaluate_application
        expected: Expected result string (AUTO_APPROVE, MANUAL_REVIEW, AUTO_DENY)

    Returns:
        dict with passed, actual, expected, diff
    """
    actual_result = actual.get("result", "UNKNOWN")
    passed = actual_result == expected

    diff = None
    if not passed:
        diff = {
            "expected": expected,
            "actual": actual_result,
            "dti": actual.get("dti_calculated"),
            "credit_tier": actual.get("credit_tier"),
            "rationale": actual.get("rationale"),
            "flags": actual.get("flags", [])
        }

    return {
        "passed": passed,
        "actual": actual_result,
        "expected": expected,
        "diff": diff
    }
