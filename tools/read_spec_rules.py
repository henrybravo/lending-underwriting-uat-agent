"""
Load rules from spec files
"""
import re
from pathlib import Path


def read_spec_rules(spec_path: str) -> dict:
    """
    Parse spec file and extract rules.

    Args:
        spec_path: Path to spec markdown file

    Returns:
        dict with requirements, rules, thresholds
    """
    path = Path(spec_path)
    if not path.exists():
        return {"error": f"Spec not found: {spec_path}"}

    content = path.read_text()

    rules = {
        "requirements": [],
        "acceptance_criteria": [],
        "thresholds": {}
    }

    # Extract requirements (lines starting with - **REQ or bullet points with SHALL)
    req_pattern = r'-\s+\*\*([^*]+)\*\*:\s*(.+)'
    for match in re.finditer(req_pattern, content):
        rules["requirements"].append({
            "id": match.group(1).strip(),
            "text": match.group(2).strip()
        })

    # Extract acceptance criteria (WHEN/THEN blocks)
    criteria_pattern = r'###\s+(.+?)\n-\s+\*\*WHEN\*\*\s+(.+?)\n-\s+\*\*THEN\*\*\s+(.+?)(?=\n\n|\n###|\Z)'
    for match in re.finditer(criteria_pattern, content, re.DOTALL):
        rules["acceptance_criteria"].append({
            "name": match.group(1).strip(),
            "when": match.group(2).strip(),
            "then": match.group(3).strip()
        })

    # Extract known thresholds
    rules["thresholds"] = {
        "dti_auto_approve": 36,
        "dti_manual_review": 43,
        "dti_auto_deny": 50,
        "credit_minimum": 620,
        "credit_excellent": 750,
        "credit_good": 700,
        "rental_factor": 0.75,
        "variance_threshold": 20,
        "bankruptcy_ch7_years": 4,
        "bankruptcy_ch13_years": 2,
        "foreclosure_years": 3
    }

    return rules
