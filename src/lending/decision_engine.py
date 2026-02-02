from src.lending.models import Decision, DecisionResult, LoanApplication
from src.lending.credit import get_credit_tier, is_credit_acceptable
from src.lending.income import calculate_total_income, check_income_variance
from src.lending.dti import calculate_back_end_dti, get_effective_threshold


def evaluate(application: LoanApplication) -> Decision:
    credit_acceptable, credit_status = is_credit_acceptable(application.credit)
    income_flags = check_income_variance(application.income)

    if not credit_acceptable:
        return Decision(
            result=DecisionResult.AUTO_DENY,
            dti_calculated=0.0,
            credit_tier=get_credit_tier(application.credit.score),
            rationale=f"Credit check failed: {credit_status}"
        )
    
    annual_income = calculate_total_income(application)
    monthly_income = annual_income / 12
    dti = calculate_back_end_dti(application, monthly_income)
    
    if dti > 0.50:
        return Decision(
            result=DecisionResult.AUTO_DENY,
            dti_calculated=dti,
            credit_tier=get_credit_tier(application.credit.score),
            rationale="DTI exceeds 50%"
        )
    
    effective_36 = get_effective_threshold(0.36, application)
    effective_43 = get_effective_threshold(0.43, application)
    
    has_flags = "credit_with_flags" in credit_status or "large_collections" in credit_status
    
    if dti <= effective_36 and application.credit.score >= 700 and not has_flags:
        return Decision(
            result=DecisionResult.AUTO_APPROVE,
            dti_calculated=dti,
            credit_tier=get_credit_tier(application.credit.score),
            rationale="Meets auto-approve criteria",
            flags=income_flags
        )
    
    if dti < effective_43:
        return Decision(
            result=DecisionResult.MANUAL_REVIEW,
            dti_calculated=dti,
            credit_tier=get_credit_tier(application.credit.score),
            rationale="Eligible for manual review",
            flags=income_flags
        )

    return Decision(
        result=DecisionResult.AUTO_DENY,
        dti_calculated=dti,
        credit_tier=get_credit_tier(application.credit.score),
        rationale="Does not meet approval criteria",
        flags=income_flags
    )