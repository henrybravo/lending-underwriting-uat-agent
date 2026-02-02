# Delta: Lending Underwriting - Add Bonus/Commission Income

**Change ID**: add-bonus-income
**Base Spec**: openspec/specs/lending-underwriting/spec.md

---

## ADDED Requirements

### Requirement: Bonus/Commission Income Verification

The system SHALL calculate bonus and commission income as the average of the two most recent years. The system SHALL flag bonus/commission income when year-over-year variance exceeds 25% with flag "INCOME_VARIANCE_HIGH". The system SHALL sum bonus/commission income with other verified income streams for total income calculation.

#### Scenario: Bonus income stable
- **WHEN** bonus income is $15,000 (year1) and $14,000 (year2)
- **THEN** the system averages to $14,500 annual and does not set variance flag because variance is under 25%

#### Scenario: Commission income with high variance
- **WHEN** commission income is $30,000 (year1) and $20,000 (year2)
- **THEN** variance exceeds 25% and the system sets flag "INCOME_VARIANCE_HIGH"

#### Scenario: Bonus income combined with W2
- **WHEN** W2 monthly_gross is $6,000 and stable bonus is $12,000/year average
- **THEN** total annual income is ($6,000 * 12) + $12,000 = $84,000

---

## MODIFIED Requirements

None.

---

## REMOVED Requirements

None.
