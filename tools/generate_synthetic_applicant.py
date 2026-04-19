"""
Create test application for specific scenario
"""

KNOWN_SCENARIOS = {
    "standard_approval",
    "dti_at_36_boundary",
    "dti_at_43_boundary",
    "self_employed_stable",
    "rental_income",
    "credit_minimum",
    "credit_below_minimum",
    "recent_bankruptcy_ch7",
    "compensating_factors",
    "pension_income",
    "bonus_income",
}


def generate_synthetic_applicant(scenario_type: str, params: dict) -> dict:
    """
    Generate a synthetic loan application for testing.

    Args:
        scenario_type: Type of scenario to generate
        params: Override parameters for the scenario

    Returns:
        LoanApplication as dict
    """
    # Base application template
    base = {
        "applicant_id": f"SYN-{scenario_type.upper()[:3]}-001",
        "income": {
            "type": "w2",
            "monthly_gross": 8500,
            "employer": "Test Corp",
            "tenure_months": 36
        },
        "debts": {
            "proposed_mortgage": 1800,
            "auto_loans": 400,
            "credit_cards": 200,
            "student_loans": 200
        },
        "credit": {
            "score": 720,
            "adverse_events": []
        },
        "loan_request": {
            "amount": 320000,
            "property_value": 400000
        },
        "assets": {
            "reserves_months": 3
        }
    }

    scenarios = {
        "standard_approval": {},  # Use base as-is

        "dti_at_36_boundary": {
            "income": {"type": "w2", "monthly_gross": 7500},
            "debts": {"proposed_mortgage": 1700, "auto_loans": 500, "credit_cards": 300, "student_loans": 200},
            "credit": {"score": 710}
        },

        "dti_at_43_boundary": {
            "income": {"type": "w2", "monthly_gross": 7000},
            "debts": {"proposed_mortgage": 1900, "auto_loans": 600, "credit_cards": 300, "student_loans": 210},
            "credit": {"score": 705}
        },

        "self_employed_stable": {
            "income": {
                "type": "self_employed",
                "year_1_net": 94000,
                "year_2_net": 86000,
                "tenure_months": 48
            },
            "debts": {"proposed_mortgage": 1600, "auto_loans": 350, "credit_cards": 150},
            "credit": {"score": 735}
        },

        "rental_income": {
            "income": {
                "type": "w2",
                "monthly_gross": 6500,
                "gross_monthly_rent": 2000,  # Should be adjusted by 0.75
                "tenure_months": 60
            },
            "debts": {"proposed_mortgage": 1600, "existing_mortgage": 700, "auto_loans": 300, "credit_cards": 200},
            "credit": {"score": 710}
        },

        "credit_minimum": {
            "credit": {"score": 620},
            "debts": {"proposed_mortgage": 1500, "auto_loans": 300, "credit_cards": 200}
        },

        "credit_below_minimum": {
            "credit": {"score": 615}
        },

        "recent_bankruptcy_ch7": {
            "credit": {
                "score": 680,
                "adverse_events": [{
                    "event_type": "bankruptcy_ch7",
                    "date": "2023-02-01",
                    "years_ago": 2.9
                }]
            }
        },

        "compensating_factors": {
            "income": {"type": "w2", "monthly_gross": 6800, "tenure_months": 72},
            "debts": {"proposed_mortgage": 1900, "auto_loans": 600, "credit_cards": 300, "student_loans": 200},
            "credit": {"score": 760},
            "loan_request": {"amount": 340000, "property_value": 450000},
            "assets": {"reserves_months": 8}
        },

        "pension_income": {
            "income": {
                "type": "pension",
                "monthly_gross": 4500,
                "tenure_months": 999
            },
            "debts": {
                "proposed_mortgage": 1200,
                "auto_loans": 200,
                "credit_cards": 150,
                "student_loans": 0  # Override base to get DTI 34.44% for AUTO_APPROVE
            },
            "credit": {"score": 700}
        },

        "bonus_income": {
            "income": {
                "type": "bonus",
                "year_1_net": 15000,  # Stable bonus: 15K yr1, 14K yr2 → avg 14.5K
                "year_2_net": 14000,  # Variance 6.9% < 25%, no flag
                "tenure_months": 60
            },
            "debts": {
                "proposed_mortgage": 350,  # Low debts for DTI ~29% with $14.5K/12=$1208/mo
                "auto_loans": 0,
                "credit_cards": 0,
                "student_loans": 0
            },
            "credit": {"score": 720}
        }
    }

    if scenario_type not in KNOWN_SCENARIOS:
        supported = ", ".join(sorted(KNOWN_SCENARIOS))
        raise ValueError(
            f"Unknown scenario_type '{scenario_type}'. Supported scenarios: {supported}"
        )

    # Get scenario template
    scenario = scenarios[scenario_type]

    # Deep merge: base <- scenario <- params
    result = _deep_merge(base, scenario)
    result = _deep_merge(result, params)

    # Update applicant ID
    result["applicant_id"] = f"SYN-{scenario_type.upper()[:6]}-001"

    return result


def _deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts, override takes precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
