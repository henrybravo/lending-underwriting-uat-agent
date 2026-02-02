# Tasks: Add Bonus/Commission Income Support

**Change ID**: add-bonus-income

## Implementation Checklist

- [x] 1. Update `src/lending/models.py` - Add "bonus" and "commission" to IncomeType enum
- [x] 2. Update `src/lending/income.py` - Add calculation logic for bonus/commission (2-year average)
- [x] 3. Update `src/lending/income.py` - Add variance check (>25% flags INCOME_VARIANCE_HIGH)
- [x] 4. Update `tools/generate_synthetic_applicant.py` - Add "bonus_income" scenario
- [x] 5. Update `agent.py` - Add expected result for bonus_income scenario
- [ ] 6. Run `openspec archive add-bonus-income --yes` to merge delta into specs
- [ ] 7. Run `daedalion clean && daedalion build` to regenerate artifacts
- [ ] 8. Test with `python agent.py --manual`
- [ ] 9. Test with `python agent.py --model claude-sonnet-4.5 -s "bonus_income"`
- [ ] 10. Commit and document results

## Acceptance Criteria

- Bonus income scenario passes UAT
- Variance flagging works correctly
- No regression in existing scenarios
