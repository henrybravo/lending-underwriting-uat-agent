# SDD build project using OpenSpec and Daedalion

Spec-driven UAT agent for mortgage underwriting. Demonstrates Daedalion compilation of underwriting specs into agent skills and uses the GitHub Copilot SDK to run the agent locally against the lending codebase.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  SOURCE OF TRUTH                                                    │
├─────────────────────────────────────────────────────────────────────┤
│  openspec/specs/lending-underwriting/spec.md                        │
│  └── Tools, requirements, acceptance criteria, scenarios            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  DAEDALION BUILD (daedalion clean && build)                         │
├─────────────────────────────────────────────────────────────────────┤
│  Generates:                                                         │
│  ├── .github/skills/lending-underwriting/SKILL.md                   │
│  ├── .github/agents/lending-underwriting.agent.md                   │
│  └── .github/copilot-instructions.md                                │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│  AGENT EXECUTION (agent.py)                                         │
├─────────────────────────────────────────────────────────────────────┤
│  • Loads skills via skill_directories                               │
│  • Registers 5 tools explicitly                                     │
│  • Filters unwanted tools (excluded_tools)                          │
│  • Runs UAT with Copilot SDK session                                │
└─────────────────────────────────────────────────────────────────────┘
```

## Workflow: Making Changes (OpenSpec Cycle)

The project uses **OpenSpec** for spec-driven development. All changes follow this cycle:

```
openspec/changes/<id>/     →    Review (HIL)    →    Implement    →    Archive
├── proposal.md                   ↓                    ↓               ↓
├── tasks.md               User approves         Execute tasks    Merge to specs/
└── specs/.../spec.md      delta specs           Mark [x] done    daedalion build
    (DELTA only)
```

### Human-In-the-Loop (HIL) Approval

**Critical step**: Implementation MUST NOT begin until specs are explicitly approved.

| Phase | Agent Action | User Action | Gate |
|-------|-------------|-------------|------|
| Draft | Creates proposal.md, tasks.md, delta spec.md | Reviews | - |
| Review | Presents delta summary table | Says "approved" or provides feedback | **HIL GATE** |
| Implement | Executes tasks.md checklist | Monitors | - |
| Archive | Runs `openspec archive <id>` | Confirms | - |

**Example HIL exchange:**
```
Agent: "Do you approve these specs?"
       | Scenario | Input | Expected |
       |----------|-------|----------|
       | bonus_stable | $15K/$14K | Avg $14.5K, no flag |

User:  "approved"  ← Implementation begins only after this
```

This ensures humans validate requirements before any code is written.

---

### 1. Create Change Proposal

```bash
# Create change directory
mkdir -p openspec/changes/<change-id>/specs/lending-underwriting

# Create required files:
# - proposal.md (why, goals, scope)
# - tasks.md (implementation checklist)
# - specs/lending-underwriting/spec.md (DELTA: ADDED/MODIFIED/REMOVED only)
```

### 2. Review & Approve (HIL Gate)

Present delta specs to user. **Wait for explicit approval** before proceeding.

### 3. Implement

Execute tasks from tasks.md, mark completed with `[x]`.

### 4. Archive & Regenerate

```bash
openspec archive <change-id> --yes    # Merge delta into specs/
daedalion clean && daedalion build    # Regenerate .github/ artifacts
```

### 5. Validate

```bash
python agent.py --manual              # Quick test
python agent.py --model claude-sonnet-4.5 -s "<scenario>"  # Full test
```

---

### Direct Spec Edit (Simple Changes)

For minor updates without full OpenSpec cycle:

1. Edit `openspec/specs/lending-underwriting/spec.md` directly
2. Run `daedalion clean && daedalion build`
3. If tool definitions changed, sync descriptions in `agent.py`
4. Test with `python agent.py --manual`

## Key Configuration

### Agent Session (agent.py)

```python
session = await client.create_session(
    on_permission_request=PermissionHandler.approve_all,
    tools=tools,                              # 6 registered tools
    streaming=True,
    skill_directories=[".github/skills"],     # Load Daedalion-generated context
    excluded_tools=["bash", "view", "edit"],  # Filter unwanted SDK tools
    model=model,
    on_event=on_event,
)
```

### Tool Definitions (spec.md YAML frontmatter)

```yaml
tools:
  - name: evaluate_application
    description: Run loan application through decision engine
    inputs:
      - name: application
        type: dict
        description: LoanApplication dict with income, debts, credit, loan_request, assets
    outputs:
      - name: decision
        type: dict
        description: Decision dict with result, dti_calculated, credit_tier, rationale, flags
```