import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.lending.models import *
from src.lending.decision_engine import evaluate


def test_standard_approval():
    app = LoanApplication(
        applicant_id="TEST-001",
        income=Income(type=IncomeType.W2, monthly_gross=8500),
        debts=Debts(proposed_mortgage=1800, auto_loans=400, credit_cards=200, student_loans=200),
        credit=Credit(score=720),
        loan_request=LoanRequest(amount=320000, property_value=400000)
    )
    decision = evaluate(app)
    assert decision.result == DecisionResult.AUTO_APPROVE
    assert decision.dti_calculated < 0.36


def test_credit_below_minimum():
    app = LoanApplication(
        applicant_id="TEST-002",
        income=Income(type=IncomeType.W2, monthly_gross=10000),
        debts=Debts(proposed_mortgage=1500),
        credit=Credit(score=615),
        loan_request=LoanRequest(amount=250000, property_value=300000)
    )
    decision = evaluate(app)
    assert decision.result == DecisionResult.AUTO_DENY


if __name__ == "__main__":
    test_standard_approval()
    test_credit_below_minimum()
    print("Basic tests passed")