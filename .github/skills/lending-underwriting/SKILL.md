---
name: lending-underwriting
description: Mortgage underwriting decision engine with income verification, DTI
  calculation, credit assessment, and compensating factors
tools:
  - name: evaluate_application
    description: Run a loan application through decision engine
    inputs:
      - name: application
        type: dict
        description: LoanApplication dict per spec schema
    outputs:
      - type: dict
        description: Decision with result, dti_calculated, credit_tier, rationale, flags
  - name: generate_synthetic_applicant
    description: Create test application for specific scenario
    inputs:
      - name: scenario_type
        type: string
        description: Scenario name (e.g., "dti_boundary", "self_employed", "adverse_event")
      - name: params
        type: dict
        description: Scenario parameters (income, debts, credit, adverse_events, etc.)
    outputs:
      - type: dict
        description: LoanApplication dict ready for evaluation
  - name: compare_decisions
    description: Check actual vs expected decision
    inputs:
      - name: actual
        type: dict
        description: Decision returned by evaluate_application
      - name: expected
        type: string
        description: Expected decision string (AUTO_APPROVE, MANUAL_REVIEW, AUTO_DENY)
    outputs:
      - type: dict
        description: Pass/fail with diff showing mismatch
  - name: read_spec_rules
    description: Load rules from spec files
    inputs:
      - name: spec_path
        type: string
        description: Path to spec file (e.g., openspec/specs/lending-underwriting/spec.md)
    outputs:
      - type: dict
        description: Parsed requirements and scenarios
  - name: generate_report
    description: Create UAT summary report with full applicant and decision data
    inputs:
      - name: test_results
        type: list
        description: >
          List of test result dicts. Each result MUST include:

          - scenario: scenario name (string)

          - expected: expected decision (AUTO_APPROVE, MANUAL_REVIEW, AUTO_DENY)

          - actual: actual decision from system

          - passed: boolean (true if actual == expected)

          - applicant: full applicant dict from generate_synthetic_applicant
          (with income, debts, credit, loan_request, assets)

          - decision: full decision dict from evaluate_application (with result,
          dti_calculated, credit_tier, rationale, flags)
    outputs:
      - type: string
        description: Markdown report with full applicant data, decision details (DTI
          percentages, credit tiers), pass/fail status, failure analysis, and
          audit trail
  - name: run_scenario_full
    description: "Execute a complete UAT validation for one scenario: generate
      synthetic applicant, run through decision engine, compare against expected
      outcome. Use this for standard scenario testing unless you need
      fine-grained control."
    inputs:
      - name: scenario_type
        type: string
        description: One of the known scenarios (standard_approval, dti_at_36_boundary,
          dti_at_43_boundary, self_employed_stable, rental_income,
          credit_minimum, credit_below_minimum, recent_bankruptcy_ch7,
          compensating_factors, pension_income, bonus_income)
      - name: expected
        type: string
        description: Expected decision (AUTO_APPROVE, MANUAL_REVIEW, AUTO_DENY)
      - name: params
        type: dict
        description: Optional overrides for the synthetic applicant
    outputs:
      - type: dict
        description: "Complete result containing: scenario, applicant (full dict),
          decision (full dict), comparison (pass/fail + diff), passed (boolean)"
uat_scenarios:
  - name: standard_approval
    expected: AUTO_APPROVE
    description: Standard W2 applicant with good credit and low DTI
  - name: dti_at_36_boundary
    expected: AUTO_APPROVE
    description: DTI right at 36% threshold, should auto-approve
  - name: dti_at_43_boundary
    expected: MANUAL_REVIEW
    description: DTI between 36-43%, triggers manual review
  - name: self_employed_stable
    expected: AUTO_APPROVE
    description: Self-employed with stable 2-year income
  - name: rental_income
    expected: AUTO_APPROVE
    description: W2 + rental income with vacancy factor applied
  - name: credit_minimum
    expected: MANUAL_REVIEW
    description: Credit score at 620 minimum threshold
  - name: credit_below_minimum
    expected: AUTO_DENY
    description: Credit score below 620 minimum
  - name: recent_bankruptcy_ch7
    expected: AUTO_DENY
    description: Chapter 7 bankruptcy within 4-year lookback
  - name: compensating_factors
    expected: AUTO_APPROVE
    description: Higher DTI offset by compensating factors
  - name: pension_income
    expected: AUTO_APPROVE
    description: Fixed pension income applicant
  - name: bonus_income
    expected: AUTO_APPROVE
    description: Bonus income with stable 2-year history
agent_instructions: >
  You are an automated UAT validator for mortgage underwriting rules.


  ## Strict Tool Preference

  - **Mandatory**: Use `run_scenario_full` for **every** scenario in normal UAT
  runs.

  - Never call `generate_synthetic_applicant`, `evaluate_application` or
  `compare_decisions` individually unless the user message explicitly says
  "debug step-by-step" or "override parameters for scenario X".


  ## Scenario Selection Rules – Mandatory

  1. When the user message contains a list of specific scenarios (e.g. "Run
  only: X,Y,Z" or "--scenarios X,Y"), execute **EXCLUSIVELY** those scenarios.
  Do NOT add any others.

  2. Only when the user message contains no scenario restriction (or says "all"
  / "full" / "default"), execute the complete default_scenarios list.

  3. Never expand or add scenarios beyond what is explicitly requested.

  4. **CRITICAL RULE**: If the user message contains ANY specific scenario list
  (even one item), **NEVER** run additional scenarios — even if you think it
  would be helpful or safe. Violating this rule is forbidden.


  ## Critical Execution Rules – No Skipping Allowed

  - **NEVER** skip, filter, optimize away, or drop any scenario that is
  requested (whether explicitly named or "all"/"full"/"default").

  - Even if a scenario is documented as a "known bug", "intentional failure", or
  "for validation purposes", you **MUST** still execute it and report the
  result.

  - Do not apply any judgment, prioritization, or "helpfulness" heuristics that
  reduce the number of scenarios run.

  - Always run **exactly** the number requested: if "all" → exactly the full
  default list (currently 11 scenarios).


  ## Core Workflow

  1. If specific scenarios are provided in the user message → run **only** those
  scenarios.

  2. Otherwise run **all** scenarios listed under `uat_scenarios`.

  3. For each scenario, call `run_scenario_full` once (it executes generate →
  evaluate → compare atomically).

  4. Collect results as a list containing: scenario, expected, actual, passed,
  applicant (full dict), decision (full dict).

  5. After all scenarios complete, call `generate_report` with the complete
  list.

  6. Do not output summaries yourself — let the report tool produce the final
  output.


  ## Validation Rules

  Follow the Requirements and Acceptance Criteria sections. Reference exact
  WHEN-THEN criteria when analyzing discrepancies.
---
# Agent Instructions

You are an automated UAT validator for mortgage underwriting rules.

## Strict Tool Preference
- **Mandatory**: Use `run_scenario_full` for **every** scenario in normal UAT runs.
- Never call `generate_synthetic_applicant`, `evaluate_application` or `compare_decisions` individually unless the user message explicitly says "debug step-by-step" or "override parameters for scenario X".

## Scenario Selection Rules – Mandatory
1. When the user message contains a list of specific scenarios (e.g. "Run only: X,Y,Z" or "--scenarios X,Y"), execute **EXCLUSIVELY** those scenarios. Do NOT add any others.
2. Only when the user message contains no scenario restriction (or says "all" / "full" / "default"), execute the complete default_scenarios list.
3. Never expand or add scenarios beyond what is explicitly requested.
4. **CRITICAL RULE**: If the user message contains ANY specific scenario list (even one item), **NEVER** run additional scenarios — even if you think it would be helpful or safe. Violating this rule is forbidden.

## Critical Execution Rules – No Skipping Allowed
- **NEVER** skip, filter, optimize away, or drop any scenario that is requested (whether explicitly named or "all"/"full"/"default").
- Even if a scenario is documented as a "known bug", "intentional failure", or "for validation purposes", you **MUST** still execute it and report the result.
- Do not apply any judgment, prioritization, or "helpfulness" heuristics that reduce the number of scenarios run.
- Always run **exactly** the number requested: if "all" → exactly the full default list (currently 11 scenarios).

## Core Workflow
1. If specific scenarios are provided in the user message → run **only** those scenarios.
2. Otherwise run **all** scenarios listed under `uat_scenarios`.
3. For each scenario, call `run_scenario_full` once (it executes generate → evaluate → compare atomically).
4. Collect results as a list containing: scenario, expected, actual, passed, applicant (full dict), decision (full dict).
5. After all scenarios complete, call `generate_report` with the complete list.
6. Do not output summaries yourself — let the report tool produce the final output.

## Validation Rules
Follow the Requirements and Acceptance Criteria sections. Reference exact WHEN-THEN criteria when analyzing discrepancies.

# Spec: Lending Underwriting

## Requirements
- **Income Verification**: The system SHALL calculate income per source: W2 as monthly_gross * 12; self-employed as average of two most recent years; rental as gross_monthly_rent * 0.75 * 12; and SHALL flag self-employed variance when year-over-year delta exceeds 20%. The system SHALL sum all verified streams for mixed-income applicants.
- **Debt-to-Income Calculation**: The system SHALL calculate back-end DTI as total_monthly_debt / total_monthly_income and compare against thresholds: <=36% auto-approve band, >36%-<=43% manual-review band, >50% auto-deny band. Compensating factors SHALL increase applicable thresholds cumulatively: credit score >= 750 adds 2%, reserves >= 6 months adds 3%, employment tenure >= 60 months adds 2%, LTV < 80% adds 2%.
- **Credit Assessment**: The system SHALL classify credit tiers (excellent >= 750, good 700-749, fair 650-699, minimum 620-649, below-minimum < 620), enforce minimum 620, and apply adverse event lookbacks: Chapter 7 within 4 years -> deny, Chapter 13 within 2 years -> deny, foreclosure within 3 years -> deny. Medical collections under $500 SHALL be ignored; non-medical collections over $500 SHALL be flagged.
- **Decision Determination**: The system SHALL return AUTO_APPROVE, MANUAL_REVIEW, or AUTO_DENY with rationale. Decision logic SHALL respect hard stops (credit < 620, adverse events within lookback, DTI > 50%) and otherwise follow DTI bands with compensating factors applied.
- **Audit, Logging, and Security**: The system SHALL log all inputs and outputs immutably with timestamps; PII (SSN, DOB) SHALL be masked in logs; reports SHALL be retained 90 days; logs SHALL capture spec references for failed cases.
- **Performance Targets**: The system SHALL complete single-application decisioning within 500ms and a batch of 100 applications within 60s during UAT runs.
- **Bonus/Commission Income Verification**: The system SHALL calculate bonus and commission income as the average of the two most recent years. The system SHALL flag bonus/commission income when year-over-year variance exceeds 25% with flag "INCOME_VARIANCE_HIGH". The system SHALL sum bonus/commission income with other verified income streams for total income calculation.

## Acceptance Criteria
### W2 annualized income
- **WHEN** a W2 applicant provides monthly_gross of $8,500
- **THEN** the system computes annual income as $8,500 * 12 and includes it in total income

### Self-employed average without variance flag
- **WHEN** self-employed net income is $94,000 (year1) and $86,000 (year2)
- **THEN** the system averages to $90,000 annual and does not set variance flag because variance is under 20%

### Self-employed variance flagged
- **WHEN** self-employed net income is $100,000 (year1) and $70,000 (year2)
- **THEN** variance exceeds 20% and the system sets flag "INCOME_VARIANCE_HIGH"

### Rental income vacancy factor
- **WHEN** rental gross is $2,000/month
- **THEN** the system uses $2,000 * 0.75 * 12 in annual income and sums with other streams

### Standard approval band
- **WHEN** income is $8,500/mo and debts are $2,600/mo
- **THEN** back-end DTI is 30.6% and qualifies within the auto-approve band

### Manual review boundary
- **WHEN** income is $7,000/mo and debts are $3,010/mo
- **THEN** back-end DTI is 43.0% and falls into manual-review band

### Auto-deny threshold
- **WHEN** income is $5,000/mo and debts are $2,600/mo
- **THEN** back-end DTI is 52.0% and triggers auto-deny band

### Compensating factors raise threshold
- **WHEN** base DTI is 44% with credit 760, reserves 8 months, tenure 72 months, and LTV 75%
- **THEN** effective threshold increases by 2%+3%+2%+2%=9% enabling approval up to 45% and the case is eligible for auto-approve if other criteria pass

### Minimum credit tier
- **WHEN** credit score is 620 with no adverse events
- **THEN** credit tier is minimum and the application remains eligible for manual review or better if other criteria pass

### Below minimum denies
- **WHEN** credit score is 615
- **THEN** the system returns auto-deny for credit

### Adverse event within window
- **WHEN** Chapter 7 bankruptcy occurred 3 years ago
- **THEN** the system returns auto-deny due to lookback violation

### Adverse event outside window
- **WHEN** Chapter 7 bankruptcy occurred 5 years ago with otherwise acceptable credit
- **THEN** the application remains eligible subject to DTI and other rules

### Medical collections ignored
- **WHEN** medical collections total $400 and no other adverse events exist
- **THEN** the medical collections are ignored in credit assessment

### Auto-approve outcome
- **WHEN** DTI is 30.6% and credit is 720 with no adverse events
- **THEN** the decision is AUTO_APPROVE with rationale citing DTI band and credit tier

### Manual review outcome
- **WHEN** DTI is 43.0% and credit is 705 with no adverse events
- **THEN** the decision is MANUAL_REVIEW with rationale referencing boundary DTI band

### Auto-deny outcome
- **WHEN** credit is 615 or DTI exceeds 50%
- **THEN** the decision is AUTO_DENY with rationale citing the failing criterion

### Failure audit trail
- **WHEN** a test case fails validation
- **THEN** the report includes masked applicant data, expected vs actual decision, spec rule reference, timestamp, and is stored immutably for audit

### Batch performance envelope
- **WHEN** 100 synthetic applications are evaluated in UAT
- **THEN** total execution completes within 60 seconds and no individual decision exceeds 500ms

### Bonus income stable
- **WHEN** bonus income is $15,000 (year1) and $14,000 (year2)
- **THEN** the system averages to $14,500 annual and does not set variance flag because variance is under 25%

### Commission income with high variance
- **WHEN** commission income is $30,000 (year1) and $20,000 (year2)
- **THEN** variance exceeds 25% and the system sets flag "INCOME_VARIANCE_HIGH"

### Bonus income combined with W2
- **WHEN** W2 monthly_gross is $6,000 and stable bonus is $12,000/year average
- **THEN** total annual income is ($6,000 * 12) + $12,000 = $84,000
