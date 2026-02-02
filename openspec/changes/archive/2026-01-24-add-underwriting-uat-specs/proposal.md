# Change: Add initial underwriting UAT specs

## Why
We need baseline OpenSpec coverage for the lending underwriting UAT agent so that future changes can trace back to requirements and scenarios.

## What Changes
- Add capability spec for lending underwriting (income, DTI, credit, decision, audit).
- Capture boundary scenarios aligned to existing instructions and agent workflows.
- Provide tasks to compile specs into skills and validate UAT flows.

## Impact
- Affected specs: lending-underwriting
- Affected code: agent-driven UAT flow, synthetic applicant generation, decision engine validation
