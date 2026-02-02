"""
Run a loan application through decision engine
"""
import sys
sys.path.insert(0, '.')

from src.lending.models import (
    LoanApplication, Income, IncomeType, Credit,
    Debts, LoanRequest, Assets, AdverseEvent
)
from src.lending.decision_engine import evaluate


def evaluate_application(application: dict) -> dict:
    """
    Run a loan application through the decision engine.

    Args:
        application: dict with keys matching LoanApplication structure

    Returns:
        dict with result, dti_calculated, credit_tier, rationale, flags
    """
    # Parse income
    income_data = application.get("income", {})
    income = Income(
        type=IncomeType(income_data.get("type", "w2")),
        monthly_gross=income_data.get("monthly_gross", 0),
        employer=income_data.get("employer"),
        tenure_months=income_data.get("tenure_months", 0),
        year_1_net=income_data.get("year_1_net", 0),
        year_2_net=income_data.get("year_2_net", 0),
        gross_monthly_rent=income_data.get("gross_monthly_rent", 0)
    )

    # Parse debts
    debts_data = application.get("debts", {})
    debts = Debts(
        proposed_mortgage=debts_data.get("proposed_mortgage", 0),
        existing_mortgage=debts_data.get("existing_mortgage", 0),
        auto_loans=debts_data.get("auto_loans", 0),
        student_loans=debts_data.get("student_loans", 0),
        credit_cards=debts_data.get("credit_cards", 0),
        other=debts_data.get("other", 0)
    )

    # Parse credit
    credit_data = application.get("credit", {})
    adverse_events = [
        AdverseEvent(
            event_type=ae.get("event_type", ""),
            date=ae.get("date", ""),
            years_ago=ae.get("years_ago", 0),
            amount=ae.get("amount", 0),
            subtype=ae.get("subtype")
        )
        for ae in credit_data.get("adverse_events", [])
    ]
    credit = Credit(
        score=credit_data.get("score", 0),
        adverse_events=adverse_events
    )

    # Parse loan request
    loan_data = application.get("loan_request", {})
    loan_request = LoanRequest(
        amount=loan_data.get("amount", 0),
        property_value=loan_data.get("property_value", 0),
        term_months=loan_data.get("term_months", 360)
    )

    # Parse assets (optional)
    assets = None
    if "assets" in application:
        assets_data = application["assets"]
        assets = Assets(
            checking=assets_data.get("checking", 0),
            savings=assets_data.get("savings", 0),
            retirement=assets_data.get("retirement", 0),
            reserves_months=assets_data.get("reserves_months", 0)
        )

    # Create application object
    loan_app = LoanApplication(
        applicant_id=application.get("applicant_id", "UNKNOWN"),
        income=income,
        debts=debts,
        credit=credit,
        loan_request=loan_request,
        assets=assets
    )

    # Evaluate
    decision = evaluate(loan_app)

    return {
        "result": decision.result.value,
        "dti_calculated": decision.dti_calculated,
        "credit_tier": decision.credit_tier.value,
        "rationale": decision.rationale,
        "flags": decision.flags
    }
