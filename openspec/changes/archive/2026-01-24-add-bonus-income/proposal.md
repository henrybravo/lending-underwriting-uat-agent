# Proposal: Add Bonus/Commission Income Support

**Change ID**: add-bonus-income
**Status**: Draft
**Created**: 2026-01-24

## Summary

Add support for bonus and commission income types in the underwriting decision engine. Many applicants have variable compensation that should be considered in total income calculations.

## Goals

1. Support bonus income calculation using 2-year average (similar to self-employed)
2. Support commission income with stability requirements
3. Flag high-variance bonus/commission income for manual review
4. Integrate with existing DTI and decision logic

## Scope

- **In scope**: Income calculation for bonus/commission, variance flagging, UAT scenario
- **Out of scope**: Tax document verification, employer verification workflows

## Business Rationale

Mortgage applicants with sales roles, executive positions, or performance-based compensation often have significant bonus/commission income. Current system only handles W2 base, self-employed, rental, and pension. This gap excludes qualified borrowers.

## Risks

- **Low**: Calculation logic follows established 2-year average pattern
- **Medium**: Variance thresholds need calibration (using 25% based on industry standards)

## Non-Goals

- Real-time income verification
- Integration with payroll providers
- Quarterly bonus projections
