---
name: lending-underwriting
description: Mortgage underwriting decision engine with income verification, DTI
  calculation, credit assessment, and compensating factors
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
Use `read_spec_rules` to load the full spec when you need acceptance criteria details.

# Spec: Lending Underwriting

## Requirements
- **Income Verification**: W2 as monthly_gross × 12; self-employed as 2-year average (flag if YoY delta > 20%); rental as gross_monthly_rent × 0.75 × 12. Sum all verified streams.
- **DTI Calculation**: back-end DTI = total_monthly_debt / total_monthly_income. Bands: ≤36% auto-approve, >36–≤43% manual-review, >50% auto-deny. Compensating factors raise thresholds: credit ≥ 750 (+2%), reserves ≥ 6 mo (+3%), tenure ≥ 60 mo (+2%), LTV < 80% (+2%).
- **Credit Assessment**: Tiers: excellent ≥ 750, good 700–749, fair 650–699, minimum 620–649, below-minimum < 620. Min 620. Adverse lookbacks: Ch7 4yr, Ch13 2yr, foreclosure 3yr → deny. Medical collections < $500 ignored.
- **Decision Determination**: AUTO_APPROVE, MANUAL_REVIEW, or AUTO_DENY with rationale. Hard stops: credit < 620, adverse events in window, DTI > 50%.
- **Bonus/Commission Income**: 2-year average; flag if YoY variance > 25% ("INCOME_VARIANCE_HIGH"). Sum with other income.
