# Development Notes

## Adding New Scenarios

1. Add scenario to `tools/generate_synthetic_applicant.py`:
   ```python
   "new_scenario": {
       "income": {"type": "w2", "monthly_gross": 5000, ...},
       "debts": {...},
       "credit": {...}
   }
   ```

2. Add expected outcome to `tools/generate_synthetic_applicant.py` `KNOWN_SCENARIOS` (optional)

3. Add to `SCENARIO_EXPECTATIONS` in `tests/test_tools.py` and run unit tests:
   ```bash
   uv run python tests/test_tools.py
   ```

4. Test with agent: `uv run python agent.py --scenarios new_scenario`

## Modifying Decision Rules

1. Edit `spec/lending-underwriting.md` (single source of truth — requirements and acceptance criteria live here)
2. Implement changes in `src/lending/*.py`
3. Validate with unit tests and UAT:
   ```bash
   uv run python tests/test_basic.py && uv run python tests/test_tools.py
   uv run python agent.py
   ```

## Testing

```bash
# Unit tests — decision engine basics (2 tests)
uv run python tests/test_basic.py

# Unit tests — all tool functions (15 tests)
uv run python tests/test_tools.py

# Agent UAT — LLM-driven end-to-end validation (requires Copilot CLI)
uv run python agent.py --model claude-sonnet-4.5 -s standard_approval,bonus_income
```

## Debugging

```bash
# Enable debug mode for full event logging - writes logfiles to ./logs/debug_[date_time].log
uv run python agent.py --debug

# Run manual mode (direct tool invocation, no SDK)
uv run python agent.py --manual

# Check session telemetry
# Look for "SESSION USAGE SUMMARY" at end of run and see docs/mlflow.md
uv run python agent.py --mlflow
mlflow ui --backend-store-uri sqlite:///mlruns/mlflow.db  # → http://localhost:5000
```
