#!/usr/bin/env python3
"""
UAT Validator Agent - Copilot SDK Entry Point

Prerequisites:
    - GitHub Copilot CLI installed (npm install -g @github/copilot-cli)
    - GITHUB_TOKEN environment variable set
    - github-copilot-sdk installed (uv pip install github-copilot-sdk)

Usage:
    python agent.py --list-models              # List available models
    python agent.py --model gpt-4o             # Use specific model
    python agent.py --task "Run UAT"           # Run with SDK
    python agent.py --manual                   # Run without SDK
"""
import asyncio
import argparse
import contextlib
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime
import logging
import time
from dataclasses import dataclass, field

import copilot
from copilot import session as copilot_session
from copilot import tools as copilot_tools

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Import tool handlers
from tools.evaluate_application import evaluate_application
from tools.generate_synthetic_applicant import generate_synthetic_applicant
from tools.compare_decisions import compare_decisions
from tools.read_spec_rules import read_spec_rules
from tools.generate_report import generate_report


# Paths for agent/skill loading
AGENT_MD_PATH = Path(".github/agents/lending-underwriting.agent.md")
SKILL_PATH = Path(".github/skills/lending-underwriting/SKILL.md")


# Persistent tool cache with TTL support
CACHE_FILE = "tool_cache.db"
CACHE_TTL_SECONDS = 86400  # 1 day

def cache_key(tool_name: str, args: dict) -> str:
    """Generate a deterministic cache key from tool name and arguments."""
    serialized = json.dumps({"tool": tool_name, "args": args}, sort_keys=True)
    return hashlib.sha256(serialized.encode()).hexdigest()


# OpenTelemetry setup for instrumentation (lazy init so --help does not trigger it)
tracer_provider = None
tracer = None
OTEL_ENABLED = False


def init_tracing():
    """Initialize OTLP tracing once per process."""
    global tracer_provider, tracer, OTEL_ENABLED

    if OTEL_ENABLED:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        import atexit

        # Configure OTLP exporter to Jaeger via gRPC (localhost:4317)
        otlp_exporter = OTLPSpanExporter(
            endpoint="http://localhost:4317",
            insecure=True,
        )

        tracer_provider = TracerProvider(
            resource=Resource.create({
                "service.name": "fsi-lending-uat-agent",
            })
        )
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        trace.set_tracer_provider(tracer_provider)
        tracer = trace.get_tracer(__name__)

        # Flush spans on exit
        def shutdown_tracer():
            if tracer_provider:
                tracer_provider.shutdown()
        atexit.register(shutdown_tracer)

        # Anthropic instrumentation
        try:
            from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
            AnthropicInstrumentor().instrument()
            print("[OTel] Anthropic instrumentation enabled")
        except ImportError:
            print("[OTel] Anthropic instrumentation not available (optional)")

        OTEL_ENABLED = True
        print("[OTel] Tracing initialized (exporting to grpc://localhost:4317)")

    except ImportError:
        OTEL_ENABLED = False
        tracer = None
        print("[OTel] OpenTelemetry not available; instrumentation disabled")
    except Exception as exc:
        OTEL_ENABLED = False
        tracer = None
        print(f"[OTel] Disabled due to error: {exc}")


def setup_logging(debug_enabled: bool) -> None:
    """Configure logging: INFO to stdout always, DEBUG to file when enabled."""
    # Reset any existing handlers to avoid duplicates across invocations
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    # Base level: DEBUG if debug_enabled so file handler can capture everything
    root.setLevel(logging.DEBUG if debug_enabled else logging.INFO)

    # Console handler for normal output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    root.addHandler(console_handler)

    # File handler only when debug is requested
    if debug_enabled:
        logs_dir = Path("logs")
        logs_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = logs_dir / f"debug_{timestamp}.log"

        file_handler = logging.FileHandler(str(log_path), mode="a")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        root.addHandler(file_handler)
        root.debug("Debug logging initialized")


def get_field(obj, name: str, default=None):
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


@contextlib.contextmanager
def trace_span(name: str):
    """Context manager for creating a span - works with or without OTel enabled."""
    if OTEL_ENABLED and tracer is not None:
        with tracer.start_as_current_span(name) as span:
            yield span
    else:
        class NoOpSpan:
            def set_attribute(self, key, value): pass
            def add_event(self, name, attributes=None): pass
            def set_status(self, status): pass
        yield NoOpSpan()


def get_cached_value(key: str) -> str | None:
    """Retrieve cached string value if exists and not expired."""
    import shelve
    import time
    try:
        with shelve.open(CACHE_FILE) as db:
            if key in db:
                entry = db[key]
                if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
                    return entry["value"]
                else:
                    # Expired, delete it
                    del db[key]
    except Exception:
        pass
    return None


def set_cached_value(key: str, value: str) -> None:
    """Store string value with timestamp."""
    import shelve
    import time
    try:
        with shelve.open(CACHE_FILE) as db:
            db[key] = {"value": value, "timestamp": time.time()}
    except Exception:
        pass


# Known scenario names for validation
KNOWN_SCENARIOS = {
    "standard_approval", "dti_at_36_boundary", "dti_at_43_boundary",
    "self_employed_stable", "rental_income", "credit_minimum",
    "credit_below_minimum", "recent_bankruptcy_ch7", "compensating_factors",
    "pension_income", "bonus_income"
}


@dataclass
class UsageStats:
    """Track token usage and costs across the session."""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    total_cost: float = 0.0
    api_calls: int = 0
    tool_calls: int = 0
    duration_ms: int = 0
    wall_clock_start: float = 0.0
    events: list = field(default_factory=list)
    debug_events: list = field(default_factory=list)  # Full event data for --debug

    def add_api_response(self, data):
        """Update stats from an API response event."""
        self.api_calls += 1
        self.input_tokens += int(getattr(data, 'input_tokens', 0) or 0)
        self.output_tokens += int(getattr(data, 'output_tokens', 0) or 0)
        self.cache_read_tokens += int(getattr(data, 'cache_read_tokens', 0) or 0)
        self.cache_write_tokens += int(getattr(data, 'cache_write_tokens', 0) or 0)
        self.total_cost += getattr(data, 'cost', 0) or 0
        self.duration_ms += getattr(data, 'duration', 0) or 0
        if hasattr(data, 'model') and data.model:
            self.model = data.model

    def print_summary(self):
        """Print usage summary."""
        print("\n" + "=" * 60)
        print("SESSION USAGE SUMMARY")
        print("=" * 60)
        print(f"  Model:              {self.model or 'unknown'}")
        print(f"  API Calls:          {self.api_calls}")
        print(f"  Tool Calls:         {self.tool_calls}")
        fresh_input = self.input_tokens - self.cache_read_tokens
        print(f"  Input Tokens:       {self.input_tokens:,}  (fresh: {fresh_input:,}, cached: {self.cache_read_tokens:,})")
        print(f"  Output Tokens:      {self.output_tokens:,}")
        if self.cache_write_tokens:
            print(f"  Cache Write Tokens: {self.cache_write_tokens:,}")
        print(f"  Total Tokens:       {self.input_tokens + self.output_tokens:,}")
        if self.total_cost > 0:
            print(f"  Billing Multiplier: {self.total_cost:.1f}x")
        if self.duration_ms > 0:
            print(f"  LLM Duration:       {self.duration_ms:,}ms")
        if self.wall_clock_start > 0:
            elapsed = time.time() - self.wall_clock_start
            print(f"  Wall Clock:         {elapsed:.1f}s")
        print("=" * 60)

    def print_debug(self):
        """Print detailed debug event data."""
        logging.debug("DEBUG: ALL EVENTS (count=%s)", len(self.debug_events))
        for i, evt in enumerate(self.debug_events):
            logging.debug("--- Event %s: %s ---", i + 1, evt.get("type", "unknown"))
            for k, v in evt.items():
                if v is None or v == "" or v == [] or v == {}:
                    continue
                v_str = str(v)
                if len(v_str) > 200:
                    v_str = v_str[:200] + "..."
                logging.debug("  %s: %s", k, v_str)


def create_tools() -> list[copilot_tools.Tool]:
    """Create SDK Tool objects with handlers."""

    async def handle_evaluate(invocation: copilot_tools.ToolInvocation) -> copilot_tools.ToolResult:
        with trace_span("Tool: evaluate_application"):
            args = invocation.arguments
            key = cache_key("evaluate_application", args)
            cached = get_cached_value(key)
            if cached is not None:
                print(f"[cache hit] evaluate_application: {key[:16]}...")
                return copilot_tools.ToolResult(text_result_for_llm=cached)
            
            result = evaluate_application(args["application"])
            text = str(result)
            set_cached_value(key, text)
            return copilot_tools.ToolResult(text_result_for_llm=text)

    async def handle_generate(invocation: copilot_tools.ToolInvocation) -> copilot_tools.ToolResult:
        with trace_span("Tool: generate_synthetic_applicant"):
            args = invocation.arguments
            key = cache_key("generate_synthetic_applicant", args)
            cached = get_cached_value(key)
            if cached is not None:
                print(f"[cache hit] generate_synthetic_applicant: {key[:16]}...")
                return copilot_tools.ToolResult(text_result_for_llm=cached)
            
            result = generate_synthetic_applicant(args["scenario_type"], args.get("params", {}))
            text = str(result)
            set_cached_value(key, text)
            return copilot_tools.ToolResult(text_result_for_llm=text)

    async def handle_compare(invocation: copilot_tools.ToolInvocation) -> copilot_tools.ToolResult:
        with trace_span("Tool: compare_decisions"):
            args = invocation.arguments
            key = cache_key("compare_decisions", args)
            cached = get_cached_value(key)
            if cached is not None:
                print(f"[cache hit] compare_decisions: {key[:16]}...")
                return copilot_tools.ToolResult(text_result_for_llm=cached)
            
            result = compare_decisions(args["actual"], args["expected"])
            text = str(result)
            set_cached_value(key, text)
            return copilot_tools.ToolResult(text_result_for_llm=text)

    async def handle_read_spec(invocation: copilot_tools.ToolInvocation) -> copilot_tools.ToolResult:
        with trace_span("Tool: read_spec_rules"):
            args = invocation.arguments
            key = cache_key("read_spec_rules", args)
            cached = get_cached_value(key)
            if cached is not None:
                print(f"[cache hit] read_spec_rules: {key[:16]}...")
                return copilot_tools.ToolResult(text_result_for_llm=cached)
            
            result = read_spec_rules(args["spec_path"])
            text = str(result)
            set_cached_value(key, text)
            return copilot_tools.ToolResult(text_result_for_llm=text)

    async def handle_report(invocation: copilot_tools.ToolInvocation) -> copilot_tools.ToolResult:
        with trace_span("Tool: generate_report"):
            from datetime import datetime
            
            args = invocation.arguments
            result = generate_report(args["test_results"])
            report_dir = Path("tests/uat/reports")
            report_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = report_dir / f"uat_report_{timestamp}.md"
            report_file.write_text(result)
            return copilot_tools.ToolResult(
                text_result_for_llm=f"Report saved to {report_file}\n\n{result}",
                session_log=f"Saved report: {report_file}",
            )

    return [
        copilot_tools.Tool(
            name="evaluate_application",
            description="Run a loan application through the decision engine",
            parameters={
                "type": "object",
                "properties": {
                    "application": {
                        "type": "object",
                        "description": "LoanApplication dict with income, debts, credit, loan_request"
                    }
                },
                "required": ["application"]
            },
            handler=handle_evaluate
        ),
        copilot_tools.Tool(
            name="generate_synthetic_applicant",
            description="Create test application for specific scenario",
            parameters={
                "type": "object",
                "properties": {
                    "scenario_type": {
                        "type": "string",
                        "description": "Scenario: standard_approval, dti_at_36_boundary, dti_at_43_boundary, self_employed_stable, rental_income, credit_minimum, credit_below_minimum, recent_bankruptcy_ch7, compensating_factors, pension_income, bonus_income"
                    },
                    "params": {"type": "object", "description": "Override parameters"}
                },
                "required": ["scenario_type"]
            },
            handler=handle_generate
        ),
        copilot_tools.Tool(
            name="compare_decisions",
            description="Check actual vs expected decision",
            parameters={
                "type": "object",
                "properties": {
                    "actual": {"type": "object", "description": "Decision from evaluate_application"},
                    "expected": {"type": "string", "description": "AUTO_APPROVE, MANUAL_REVIEW, or AUTO_DENY"}
                },
                "required": ["actual", "expected"]
            },
            handler=handle_compare
        ),
        copilot_tools.Tool(
            name="read_spec_rules",
            description="Load rules from spec files",
            parameters={
                "type": "object",
                "properties": {
                    "spec_path": {"type": "string", "description": "Path to spec file"}
                },
                "required": ["spec_path"]
            },
            handler=handle_read_spec
        ),
        copilot_tools.Tool(
            name="generate_report",
            description="Create UAT summary report with full applicant and decision data",
            parameters={
                "type": "object",
                "properties": {
                    "test_results": {
                        "type": "array",
                        "description": "List of test result dicts. Each must include: scenario, expected, actual, passed, applicant, decision",
                        "items": {
                            "type": "object",
                            "properties": {
                                "scenario": {"type": "string"},
                                "expected": {"type": "string"},
                                "actual": {"type": "string"},
                                "passed": {"type": "boolean"},
                                "applicant": {"type": "object"},
                                "decision": {"type": "object"}
                            },
                            "required": ["scenario", "expected", "actual", "passed"]
                        }
                    }
                },
                "required": ["test_results"]
            },
            handler=handle_report
        ),
        copilot_tools.Tool(
            name="run_scenario",
            description="Execute a complete UAT validation for one scenario: generate synthetic applicant, run through decision engine, compare against expected outcome. Use this for standard scenario testing unless you need fine-grained control.",
            parameters={
                "type": "object",
                "properties": {
                    "scenario_type": {
                        "type": "string",
                        "description": "Scenario: standard_approval, dti_at_36_boundary, dti_at_43_boundary, self_employed_stable, rental_income, credit_minimum, credit_below_minimum, recent_bankruptcy_ch7, compensating_factors, pension_income, bonus_income"
                    },
                    "expected": {
                        "type": "string",
                        "description": "Expected decision (AUTO_APPROVE, MANUAL_REVIEW, AUTO_DENY)"
                    },
                    "params": {"type": "object", "description": "Optional overrides for the synthetic applicant"}
                },
                "required": ["scenario_type", "expected"]
            },
            handler=handle_run_scenario
        ),
    ]


async def handle_run_scenario(invocation: copilot_tools.ToolInvocation) -> copilot_tools.ToolResult:
    """Execute a complete UAT validation for one scenario."""
    with trace_span("Tool: run_scenario"):
        args = invocation.arguments
        scenario_type = args["scenario_type"]
        expected = args["expected"]
        params = args.get("params", {})

        with trace_span("Generate Applicant"):
            applicant = generate_synthetic_applicant(scenario_type, params)

        with trace_span("Evaluate Application"):
            decision = evaluate_application(applicant)

        with trace_span("Compare Decisions"):
            comparison = compare_decisions(decision, expected)

        result = {
            "scenario": scenario_type,
            "applicant": applicant,
            "decision": decision,
            "comparison": comparison,
            "passed": comparison.get("passed", False),
            "expected": expected,
            "actual": decision.get("result", "UNKNOWN")
        }

        return copilot_tools.ToolResult(text_result_for_llm=str(result))


async def list_models():
    """List available models from Copilot CLI."""
    logging.info("Connecting to Copilot CLI to list models")
    client = copilot.CopilotClient()
    await client.start()

    status = await client.get_status()
    logging.info("CLI Version: %s, Protocol: %s", get_field(status, "version"), get_field(status, "protocolVersion"))

    models = await client.list_models()  # Returns list directly

    # Build rows for ASCII table
    rows = []
    for m in models:
        model_id = get_field(m, "id", "unknown")
        name = get_field(m, "name", model_id)
        caps = get_field(m, "capabilities", {})
        limits = get_field(caps, "limits", {})
        supports = get_field(caps, "supports", {})
        policy = get_field(m, "policy", {})
        billing = get_field(m, "billing", {})

        rows.append({
            "Model ID": model_id,
            "Name": name,
            "Vision": "✓" if get_field(supports, "vision") else "",
            "State": get_field(policy, "state", ""),
            "Billing": "[REDACTED]" if get_field(billing, "multiplier") else "",
            "Max Prompt": f"{get_field(limits, 'max_prompt_tokens', 0):,}",
            "Max Context": f"{get_field(limits, 'max_context_window_tokens', 0):,}",
        })

        # Dump full SDK object when --debug is active
        logging.debug("model raw: %s", {
            attr: getattr(m, attr, None)
            for attr in dir(m)
            if not attr.startswith("_")
        })

    if rows:
        headers = list(rows[0].keys())
        col_widths = {h: max(len(h), *(len(str(r[h])) for r in rows)) for h in headers}
        header_line = " | ".join(h.ljust(col_widths[h]) for h in headers)
        sep_line = "-+-".join("-" * col_widths[h] for h in headers)
        print(f"\n {header_line}")
        print(f" {sep_line}")
        for r in rows:
            print(f" {' | '.join(str(r[h]).ljust(col_widths[h]) for h in headers)}")
        print()

    await client.stop()
    print(f"Total: {len(models)} models")


async def run_uat(task: str, model: str = None, scenarios: list[str] = None, streaming: bool = True, timeout: float = 300.0, debug: bool = False):
    """Run UAT with Copilot SDK."""
    logging.info("=== UAT Validator Agent (Copilot SDK) ===")
    logging.info("task=%s model=%s scenarios=%s streaming=%s timeout=%s debug=%s", task, model, scenarios, streaming, timeout, debug)

    # Initialize client
    client = copilot.CopilotClient()
    logging.info("Connecting to Copilot CLI...")
    await client.start()

    status = await client.get_status()
    logging.info("Connected: CLI v%s, Protocol v%s", get_field(status, "version"), get_field(status, "protocolVersion"))

    # Create tools
    tools = create_tools()
    logging.info("Registered %s tools", len(tools))

    # Track usage stats
    stats = UsageStats(wall_clock_start=time.time())

    def _update_stats_from_usage(data):
        """Extract usage stats from ASSISTANT_USAGE event data only."""
        stats.input_tokens += int(getattr(data, 'input_tokens', 0) or 0)
        stats.output_tokens += int(getattr(data, 'output_tokens', 0) or 0)
        stats.cache_read_tokens += int(getattr(data, 'cache_read_tokens', 0) or 0)
        stats.cache_write_tokens += int(getattr(data, 'cache_write_tokens', 0) or 0)
        stats.total_cost += getattr(data, 'cost', 0) or 0
        stats.duration_ms += int(getattr(data, 'duration', 0) or 0)
        selected_model = getattr(data, 'model', None)
        if selected_model:
            stats.model = selected_model

    # Register event handler
    def on_event(event: copilot_session.SessionEvent):
        raw_type = str(event.type.value) if hasattr(event.type, 'value') else str(event.type)
        event_type = raw_type.lower()
        stats.events.append(raw_type)

        data = getattr(event, 'data', None)

        # Only count usage from ASSISTANT_USAGE events
        if event_type == "assistant.usage" and data:
            stats.api_calls += 1
            _update_stats_from_usage(data)

        # Capture full event data for debug mode
        if debug and data:
            evt_dict = {"type": raw_type}
            for attr in dir(data):
                if not attr.startswith('_'):
                    try:
                        val = getattr(data, attr)
                        if callable(val) or val is None:
                            continue
                        if isinstance(val, (str, bytes, list, tuple, dict, set)) and len(val) == 0:
                            continue
                        evt_dict[attr] = val
                    except Exception:
                        pass
            stats.debug_events.append(evt_dict)
            try:
                payload = str(evt_dict)
                if len(payload) > 2000:
                    payload = payload[:2000] + "..."
                logging.debug("event=%s payload=%s", raw_type, payload)
            except Exception:
                pass

        # Count API responses whenever token usage fields are present.
        # (already counted above for assistant.usage events)

        # Count tool executions (start events only, not complete)
        if event_type == "tool.execution_start":
            tool_name = getattr(data, 'tool_name', None) or getattr(data, 'name', None) or 'unknown'
            # Only count our registered tools, not SDK internals (skill, report_intent, etc.)
            if tool_name in {"generate_synthetic_applicant", "evaluate_application", "compare_decisions", "read_spec_rules", "generate_report", "run_scenario"}:
                stats.tool_calls += 1
                tool_args = getattr(data, 'arguments', None) or {}
                scenario = tool_args.get("scenario_type", "")
                label = f"{tool_name}({scenario})" if scenario else tool_name
                logging.info("tool: %s", label)
        elif event_type == "assistant.message_delta" and streaming:
            delta = getattr(data, 'delta_content', '') or getattr(data, 'text', '')
            if delta:
                print(delta, end='', flush=True)
        elif event_type in {"session.start", "session.model_selected"}:
            selected = getattr(data, 'selected_model', None) or getattr(data, 'model', None)
            if selected:
                stats.model = selected
                logging.info("session model selected: %s", selected)

        # Debug: surface unexpected event types
        if event_type not in {"assistant.message_delta", "tool.execution_start", "tool.execution_complete", "session.start", "session.model_selected", "api.response"}:
            extra = getattr(data, 'event', None) or getattr(data, 'type', None)
            if extra:
                print(f"  [event] {raw_type} ({extra})")

    # Create session
    session = await client.create_session(
        on_permission_request=copilot_session.PermissionHandler.approve_all,
        tools=tools,
        streaming=streaming,
        skill_directories=[".github/skills"],
        excluded_tools=["bash", "view", "edit"],
        model=model,
        on_event=on_event,
    )
    if model:
        logging.info("Model selected: %s", model)
    logging.info("Session created")

    # Build minimal task prompt - domain knowledge lives in skill files
    if scenarios:
        scenario_list = ", ".join(scenarios)
        task_prompt = (
            f"Run UAT validation for ONLY these scenarios: {scenario_list}\n\n"
            "Do NOT run any other scenarios.\n"
            "Always conclude by calling generate_report with ALL collected results."
        )
    else:
        task_prompt = """Execute standard UAT validation for the lending-underwriting skill.

Follow the instructions and preferred workflow defined in the loaded skill.

Validate all scenarios listed in the skill.
Always conclude by calling generate_report with collected results.
"""

    logging.info("Task: %s", task)
    logging.info("Timeout: %ss", timeout)

    # Send and wait with configured timeout
    # Provide both prompt and messages for compatibility with SDK expectations.
    with trace_span("Session Send And Wait"):
        await session.send_and_wait(task_prompt, timeout=timeout)

    if streaming:
        print()  # newline after streamed content

    # Print usage summary
    stats.print_summary()

    # Print debug info if enabled
    if debug:
        stats.print_debug()

    # Cleanup
    await session.disconnect()
    await client.stop()
    print("\n✓ Session complete")


async def run_manual_uat():
    """Run UAT without SDK, using tools directly."""
    logging.info("=== Manual UAT (No SDK) ===")

    scenarios = [
        ("standard_approval", "AUTO_APPROVE"),
        ("dti_at_36_boundary", "AUTO_APPROVE"),
        ("dti_at_43_boundary", "MANUAL_REVIEW"),
        ("self_employed_stable", "AUTO_APPROVE"),
        ("rental_income", "AUTO_APPROVE"),
        ("credit_minimum", "MANUAL_REVIEW"),
        ("credit_below_minimum", "AUTO_DENY"),
        ("recent_bankruptcy_ch7", "AUTO_DENY"),
        ("compensating_factors", "AUTO_APPROVE"),
        ("pension_income", "AUTO_APPROVE"),
        ("bonus_income", "AUTO_APPROVE"),
    ]

    results = []
    for scenario_type, expected in scenarios:
        logging.info("scenario start: %s", scenario_type)
        applicant = generate_synthetic_applicant(scenario_type, {})
        logging.info("generated applicant: %s", applicant.get('applicant_id'))

        decision = evaluate_application(applicant)
        logging.info("decision: %s (DTI: %.1f%%)", decision.get('result'), decision.get('dti_calculated', 0) * 100)

        comparison = compare_decisions(decision, expected)
        status = "pass" if comparison["passed"] else "fail"
        logging.info("compare: %s expected=%s got=%s", status, expected, decision.get('result'))

        results.append({
            "scenario": scenario_type,
            "passed": comparison["passed"],
            "expected": expected,
            "actual": decision["result"],
            "applicant": applicant,
            "decision": decision,
            "diff": comparison.get("diff")
        })

    report = generate_report(results)
    report_path = Path("tests/uat/reports")
    report_path.mkdir(parents=True, exist_ok=True)
    report_file = report_path / "uat-report-manual.md"
    report_file.write_text(report)

    print(f"\n=== Report saved: {report_file} ===")
    print("\n" + report)


def main():
    parser = argparse.ArgumentParser(
        description="UAT Validator Agent - Copilot SDK",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agent.py --list-models
  python agent.py --model claude-sonnet-4.5
  python agent.py --model claude-sonnet-4.5 --scenarios "rental_income,pension_income"
  python agent.py --model claude-sonnet-4.5 --debug --scenarios "standard_approval"
  python agent.py --manual

Available scenarios:
  standard_approval, dti_at_36_boundary, dti_at_43_boundary,
  self_employed_stable, rental_income, credit_minimum,
  credit_below_minimum, recent_bankruptcy_ch7, compensating_factors,
  pension_income
        """
    )
    parser.add_argument("--list-models", action="store_true", help="List available models and exit")
    parser.add_argument("--model", "-m", help="Model to use (e.g., claude-sonnet-4.5, gpt-5)")
    parser.add_argument("--task", default="Run UAT for lending underwriting",
                        help="Override the default user prompt (the instructions shown under “Examples”) when you want a custom run description.")
    parser.add_argument("--scenarios", "-s",
                        help="Scenario names to run: 'all' for all scenarios, or comma-separated list (e.g., 'rental_income,pension_income')")
    parser.add_argument("--no-streaming", action="store_true", help="Disable streaming output")
    parser.add_argument("--timeout", "-t", type=float, default=300.0, help="Timeout in seconds (default: 300)")
    parser.add_argument("--debug", "-d", action="store_true",
                        help="Capture and print all event data (quota, compaction, context, etc.)")
    parser.add_argument("--manual", action="store_true", help="Run without SDK (direct tool calls)")
    parser.add_argument("--tracing", action="store_true", help="Enable OpenTelemetry tracing (exports to localhost:4317)")

    args = parser.parse_args()

    # Configure logging: INFO to stdout; DEBUG to file when --debug
    setup_logging(args.debug)
    logging.debug("args: %s", args)

    if args.list_models:
        asyncio.run(list_models())
    else:
        # Initialize tracing only when explicitly requested
        if args.tracing:
            init_tracing()

        # Warn if --task looks like scenario names
        if args.task != "Run UAT for lending underwriting":
            task_parts = set(args.task.replace(" ", "").split(","))
            if task_parts & KNOWN_SCENARIOS:
                print("=" * 60)
                print("WARNING: --task appears to contain scenario names!")
                print(f"  You used: --task \"{args.task}\"")
                print(f"  Did you mean: --scenarios \"{args.task}\"")
                print("=" * 60)
                print()

        if args.manual:
            asyncio.run(run_manual_uat())
        else:
            # Handle --scenarios all as explicit "run all scenarios"
            if args.scenarios and args.scenarios.lower() == "all":
                scenarios = None
            else:
                scenarios = args.scenarios.split(",") if args.scenarios else None
            asyncio.run(run_uat(args.task, args.model, scenarios, not args.no_streaming, args.timeout, args.debug))


if __name__ == "__main__":
    main()
