"""
Create UAT summary report
"""
from datetime import datetime


def generate_report(test_results: list) -> str:
    """
    Generate detailed markdown UAT report.

    Args:
        test_results: List of test result dicts, each containing:
            - scenario: str (scenario name)
            - expected: str (expected decision)
            - actual: str (actual decision)
            - passed: bool
            - applicant: dict (optional, from generate_synthetic_applicant)
            - decision: dict (optional, from evaluate_application)

    Returns:
        Markdown formatted report
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed = sum(1 for r in test_results if r.get("passed"))
    failed = len(test_results) - passed
    total = len(test_results)
    success_rate = (passed / total * 100) if total > 0 else 0

    report = f"""# Lending Underwriting UAT Report
Generated: {timestamp}

## Summary
- **Total Scenarios**: {total}
- **Passed**: {passed}
- **Failed**: {failed}
- **Success Rate**: {success_rate:.1f}%

## Test Results

| Scenario | Expected | Actual | DTI % | Credit Tier | Status |
|----------|----------|--------|-------|-------------|--------|
"""

    # Summary table
    for result in test_results:
        scenario = result.get("scenario", "unknown")
        expected = result.get("expected", "?")
        actual = result.get("actual", "?")
        status = "✓ PASS" if result.get("passed") else "✗ FAIL"

        # Extract decision details
        decision = result.get("decision", {})
        dti = decision.get("dti_calculated", 0)
        dti_pct = f"{dti * 100:.2f}" if isinstance(dti, (int, float)) and dti > 0 else "0.0"
        credit_tier = decision.get("credit_tier", "unknown")

        report += f"| {scenario} | {expected} | {actual} | {dti_pct} | {credit_tier} | {status} |\n"

    report += "\n## Detailed Analysis\n"

    # Detailed section for each scenario
    for result in test_results:
        scenario = result.get("scenario", "unknown")
        expected = result.get("expected", "?")
        actual = result.get("actual", "?")
        passed_flag = result.get("passed", False)
        status_icon = "✓" if passed_flag else "❌"
        status_text = "PASSED" if passed_flag else "FAILED"

        decision = result.get("decision", {})
        applicant = result.get("applicant", {})

        report += f"\n### {status_icon} {scenario} - {status_text}\n"
        report += f"- **Result**: {actual}\n"

        # Decision details
        dti = decision.get("dti_calculated", 0)
        if isinstance(dti, (int, float)) and dti > 0:
            report += f"- **DTI**: {dti * 100:.2f}%\n"

        credit_tier = decision.get("credit_tier")
        if credit_tier:
            report += f"- **Credit Tier**: {credit_tier}\n"

        rationale = decision.get("rationale")
        if rationale:
            report += f"- **Rationale**: {rationale}\n"

        flags = decision.get("flags", [])
        if flags:
            report += f"- **Flags**: {', '.join(flags)}\n"

        # Applicant details (if provided)
        if applicant:
            income = applicant.get("income", {})
            debts = applicant.get("debts", {})
            credit = applicant.get("credit", {})

            income_type = income.get("type", "unknown")
            monthly_gross = income.get("monthly_gross", 0)
            credit_score = credit.get("score", 0)

            if monthly_gross or credit_score:
                report += f"- **Applicant**: "
                parts = []
                if monthly_gross:
                    parts.append(f"${monthly_gross:,}/mo ({income_type})")
                if credit_score:
                    parts.append(f"credit {credit_score}")
                report += ", ".join(parts) + "\n"

        # For failures, add expected vs actual
        if not passed_flag:
            report += f"- **Expected**: {expected}\n"
            report += f"- **Issue**: Decision engine returned {actual} instead of {expected}\n"

    # Compliance notes for failures
    if failed > 0:
        report += "\n## Compliance Notes\n"

        for result in test_results:
            if not result.get("passed"):
                scenario = result.get("scenario", "unknown")
                expected = result.get("expected", "?")
                actual = result.get("actual", "?")
                decision = result.get("decision", {})

                report += f"\n### {scenario} Failure\n"
                report += f"The `{scenario}` scenario failed because the decision engine returned "
                report += f"`{actual}` instead of `{expected}`.\n\n"

                # Add scenario-specific notes
                if "dti" in scenario.lower():
                    dti = decision.get("dti_calculated", 0)
                    report += f"- DTI calculated: {dti * 100:.2f}%\n"
                    report += "- Check DTI threshold boundary logic (< vs <=)\n"
                elif "rental" in scenario.lower():
                    report += "- Check rental income vacancy factor (should be 0.75)\n"
                elif "bankruptcy" in scenario.lower():
                    report += "- Check adverse event lookback periods\n"
                elif "pension" in scenario.lower():
                    report += "- Check pension income calculation\n"

                report += f"\n**Spec Reference**: openspec/specs/lending-underwriting/spec.md\n"

    # Recommendations
    if failed > 0:
        report += "\n## Recommendations\n"
        report += "1. Review the failing scenarios against the spec requirements\n"
        report += "2. Check boundary conditions in decision logic\n"
        report += "3. Verify income calculation formulas\n"
        report += "4. Add unit tests for edge cases\n"

    return report
