from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IncomeType(Enum):
    W2 = "w2"
    SELF_EMPLOYED = "self_employed"
    RENTAL = "rental"
    PENSION = "pension"
    BONUS = "bonus"
    COMMISSION = "commission"


class DecisionResult(Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    AUTO_DENY = "AUTO_DENY"


class CreditTier(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    MINIMUM = "minimum"
    BELOW_MINIMUM = "below"


@dataclass
class Income:
    type: IncomeType
    monthly_gross: float = 0.0
    employer: Optional[str] = None
    tenure_months: int = 0
    year_1_net: float = 0.0
    year_2_net: float = 0.0
    gross_monthly_rent: float = 0.0


@dataclass
class AdverseEvent:
    event_type: str
    date: str
    years_ago: float
    amount: float = 0.0
    subtype: Optional[str] = None


@dataclass
class Credit:
    score: int
    adverse_events: list[AdverseEvent] = field(default_factory=list)


@dataclass
class Debts:
    proposed_mortgage: float = 0.0
    existing_mortgage: float = 0.0
    auto_loans: float = 0.0
    student_loans: float = 0.0
    credit_cards: float = 0.0
    other: float = 0.0


@dataclass
class LoanRequest:
    amount: float
    property_value: float
    term_months: int = 360


@dataclass
class Assets:
    checking: float = 0.0
    savings: float = 0.0
    retirement: float = 0.0
    reserves_months: int = 0


@dataclass
class LoanApplication:
    applicant_id: str
    income: Income
    debts: Debts
    credit: Credit
    loan_request: LoanRequest
    assets: Optional[Assets] = None


@dataclass
class Decision:
    result: DecisionResult
    dti_calculated: float
    credit_tier: CreditTier
    rationale: str
    flags: list[str] = field(default_factory=list)