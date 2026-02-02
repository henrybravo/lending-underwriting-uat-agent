from src.lending.models import Debts, IncomeType, Income, LoanApplication


def calculate_total_monthly_debt(debts: Debts) -> float:
    return (debts.proposed_mortgage + debts.existing_mortgage +
            debts.auto_loans + debts.student_loans +
            debts.credit_cards + debts.other)


def calculate_back_end_dti(application: LoanApplication, monthly_income: float) -> float:
    total_debt = calculate_total_monthly_debt(application.debts)
    return total_debt / monthly_income if monthly_income > 0 else 1.0


def get_compensating_factors(application: LoanApplication) -> dict:
    factors = {}
    if application.credit.score >= 750:
        factors["credit"] = 0.02
    if application.assets and application.assets.reserves_months >= 6:
        factors["reserves"] = 0.03
    if application.income.type == IncomeType.W2 and application.income.tenure_months >= 60:
        factors["tenure"] = 0.02
    ltv = application.loan_request.amount / application.loan_request.property_value
    if ltv < 0.8:
        factors["ltv"] = 0.02
    return factors


def get_effective_threshold(base_threshold: float, application: LoanApplication) -> float:
    factors = get_compensating_factors(application)
    adjustment = sum(factors.values())
    return base_threshold + adjustment