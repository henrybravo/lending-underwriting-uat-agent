from src.lending.models import Income, IncomeType, LoanApplication


def calculate_annual_income(income: Income) -> float:
    if income.type == IncomeType.W2:
        return income.monthly_gross * 12
    elif income.type == IncomeType.SELF_EMPLOYED:
        return (income.year_1_net + income.year_2_net) / 2
    elif income.type == IncomeType.RENTAL:
        return income.gross_monthly_rent * 12
    elif income.type == IncomeType.PENSION:
        return income.monthly_gross * 12
    elif income.type in (IncomeType.BONUS, IncomeType.COMMISSION):
        return (income.year_1_net + income.year_2_net) / 2
    else:
        return 0.0


def check_income_variance(income: Income) -> list[str]:
    """Check for high variance in variable income types (>25% for bonus/commission, >20% for self-employed)."""
    flags = []
    if income.type in (IncomeType.BONUS, IncomeType.COMMISSION):
        if income.year_1_net > 0 and income.year_2_net > 0:
            avg = (income.year_1_net + income.year_2_net) / 2
            variance = abs(income.year_1_net - income.year_2_net) / avg
            if variance > 0.25:
                flags.append("INCOME_VARIANCE_HIGH")
    elif income.type == IncomeType.SELF_EMPLOYED:
        if income.year_1_net > 0 and income.year_2_net > 0:
            avg = (income.year_1_net + income.year_2_net) / 2
            variance = abs(income.year_1_net - income.year_2_net) / avg
            if variance > 0.20:
                flags.append("INCOME_VARIANCE_HIGH")
    return flags


def calculate_total_income(application: LoanApplication) -> float:
    return calculate_annual_income(application.income)