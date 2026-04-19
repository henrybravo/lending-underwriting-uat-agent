"""
Load rules from spec files
"""
import re
from pathlib import Path

RE_REQUIREMENT_HEADER = re.compile(r"^### Requirement:\s*(.+?)\s*$", re.MULTILINE)
RE_SCENARIO_HEADER = re.compile(r"^#### Scenario:\s*(.+?)\s*$", re.MULTILINE)
RE_WHEN_LINE = re.compile(r"^- \*\*WHEN\*\*\s+(.+)$", re.MULTILINE)
RE_THEN_LINE = re.compile(r"^- \*\*THEN\*\*\s+(.+)$", re.MULTILINE)
RE_BULLET_REQUIREMENT = re.compile(r"^- \*\*([^*]+)\*\*:\s*(.+)$")


def _extract_requirement_text(block: str) -> str:
    """Extract the requirement narrative paragraph from a requirement block."""
    lines = []
    started = False
    for raw_line in block.splitlines():
        line = raw_line.strip()
        if not line:
            if started:
                break
            continue
        if line.startswith("#### Scenario:") or line.startswith("### ") or line.startswith("## "):
            break
        started = True
        lines.append(line)
    return " ".join(lines).strip()


def _extract_requirements(content: str) -> list[dict]:
    requirements = []
    headers = list(RE_REQUIREMENT_HEADER.finditer(content))

    for idx, header in enumerate(headers):
        block_end = headers[idx + 1].start() if idx + 1 < len(headers) else len(content)
        block = content[header.end():block_end]
        text = _extract_requirement_text(block)
        if text:
            requirements.append({
                "id": header.group(1).strip(),
                "text": text,
            })

    # Fallback for condensed specs that only keep bullet requirements.
    if not requirements:
        in_requirements = False
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if line.startswith("## Requirements"):
                in_requirements = True
                continue
            if in_requirements and line.startswith("## "):
                break
            if not in_requirements:
                continue
            match = RE_BULLET_REQUIREMENT.match(line)
            if not match:
                continue
            requirements.append({
                "id": match.group(1).strip(),
                "text": match.group(2).strip(),
            })

    return requirements


def _extract_acceptance_criteria(content: str) -> list[dict]:
    criteria = []
    scenario_headers = list(RE_SCENARIO_HEADER.finditer(content))

    for idx, header in enumerate(scenario_headers):
        block_end = scenario_headers[idx + 1].start() if idx + 1 < len(scenario_headers) else len(content)
        block = content[header.end():block_end]
        when_match = RE_WHEN_LINE.search(block)
        then_match = RE_THEN_LINE.search(block)
        if not when_match or not then_match:
            continue
        criteria.append({
            "name": header.group(1).strip(),
            "when": when_match.group(1).strip(),
            "then": then_match.group(1).strip(),
        })

    return criteria


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

    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {"error": f"Failed to read spec: {exc}"}

    return {
        "requirements": _extract_requirements(content),
        "acceptance_criteria": _extract_acceptance_criteria(content),
        "thresholds": {
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
        },
    }
