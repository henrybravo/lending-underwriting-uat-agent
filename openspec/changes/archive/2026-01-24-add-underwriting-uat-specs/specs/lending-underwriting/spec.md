## ADDED Requirements
### Requirement: Income Verification
The system SHALL calculate income per source (W2, self-employed average of 2 years, rental at 75% vacancy factor) and sum verified streams; variance over 20% for self-employed SHALL be flagged.

#### Scenario: W2 annualized income
- **WHEN** a W2 applicant provides monthly_gross of $8,500
- **THEN** the system computes annual income as $8,500 * 12 and includes it in total income

#### Scenario: Self-employed average with variance flag
- **WHEN** self-employed net income is $94,000 (year1) and $86,000 (year2)
- **THEN** the system averages to $90,000 annual and does not set variance flag because variance is under 20%

#### Scenario: Rental income vacancy factor
- **WHEN** rental gross is $2,000/month
- **THEN** the system uses $2,000 * 0.75 * 12 in annual income and sums with other streams

### Requirement: Debt-to-Income Calculation
The system SHALL calculate back-end DTI as total_monthly_debt / total_monthly_income and compare against thresholds: <=36% auto-approve band, >36%-<=43% manual-review band, >50% auto-deny band; compensating factors (credit>=750 +2%, reserves>=6mo +3%, tenure>=60mo +2%, LTV<80% +2%) SHALL increase applicable thresholds cumulatively.

#### Scenario: Standard approval band
- **WHEN** income is $8,500/mo and debts are $2,600/mo
- **THEN** back-end DTI is 30.6% and qualifies within the auto-approve band

#### Scenario: Manual review boundary
- **WHEN** income is $7,000/mo and debts are $3,010/mo
- **THEN** back-end DTI is 43.0% and falls into manual-review band

#### Scenario: Auto-deny threshold
- **WHEN** income is $5,000/mo and debts are $2,600/mo
- **THEN** back-end DTI is 52.0% and triggers auto-deny band

#### Scenario: Compensating factors raise threshold
- **WHEN** base DTI is 44% with credit 760, reserves 8 months, tenure 72 months, and LTV 75%
- **THEN** effective threshold increases by 2%+3%+2%+2%=9% enabling approval up to 45% and the case is eligible for auto-approve if other criteria pass

### Requirement: Credit Assessment
The system SHALL classify credit tiers (excellent>=750, good 700-749, fair 650-699, minimum 620-649, below-minimum<620), enforce minimum 620, and apply adverse event lookbacks (Chapter 7 within 4y deny, Chapter 13 within 2y deny, foreclosure within 3y deny); medical collections under $500 SHALL be ignored while non-medical collections over $500 SHALL be flagged.

#### Scenario: Minimum credit tier
- **WHEN** credit score is 620 with no adverse events
- **THEN** credit tier is minimum and the application remains eligible for manual review or better if other criteria pass

#### Scenario: Below minimum denies
- **WHEN** credit score is 615
- **THEN** the system returns auto-deny for credit

#### Scenario: Adverse event within window
- **WHEN** Chapter 7 bankruptcy occurred 3 years ago
- **THEN** the system returns auto-deny due to lookback violation

### Requirement: Decision Determination
The system SHALL return AUTO_APPROVE, MANUAL_REVIEW, or AUTO_DENY with rationale; decision logic SHALL respect hard stops (credit<620, adverse events within lookback, DTI>50%) and otherwise follow DTI bands with compensating factors.

#### Scenario: Auto-approve outcome
- **WHEN** DTI is 30.6% and credit is 720 with no adverse events
- **THEN** the decision is AUTO_APPROVE with rationale citing DTI and credit tier

#### Scenario: Manual review outcome
- **WHEN** DTI is 43.0% and credit is 705 with no adverse events
- **THEN** the decision is MANUAL_REVIEW with rationale referencing boundary DTI band

#### Scenario: Auto-deny outcome
- **WHEN** credit is 615 or DTI exceeds 50%
- **THEN** the decision is AUTO_DENY with rationale citing the failing criterion

### Requirement: Audit, Logging, and Security
The system SHALL log all inputs/outputs immutably with timestamps; PII (SSN, DOB) SHALL be masked in logs; reports SHALL be retained 90 days; logs SHALL capture spec references for failed cases.

#### Scenario: Failure audit trail
- **WHEN** a test case fails validation
- **THEN** the report includes masked applicant data, expected vs actual decision, spec rule reference, timestamp, and is stored immutably for audit

### Requirement: Performance Targets
The system SHALL complete single-application decisioning within 500ms and a batch of 100 applications within 60s during UAT runs.

#### Scenario: Batch performance envelope
- **WHEN** 100 synthetic applications are evaluated in UAT
- **THEN** total execution completes within 60 seconds and no individual decision exceeds 500ms
