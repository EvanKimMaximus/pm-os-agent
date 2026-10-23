"""Cortex, a minimal, explicit agent loop you (and your coding agent) can read end
to end. This is the agent you ship: your PM chief-of-staff. You build it by
directing your coding agent (Claude Code / Cursor / Codex) to shape this file. You
never have to hand-write it.

Every bound the course talks about is visible right here in code, not buried in a
framework: the max-iteration counter, the cost cap, the revision cap, the
stop/escalate conditions, the auto-queue cap, and the absence of any publish tool.

Usage (ask your coding agent to run these for you, or run them yourself), from
00-build/ with the project's virtual environment:
    ..\\.venv\\Scripts\\python agent.py                # happy-path task (weekly status update)
    ..\\.venv\\Scripts\\python agent.py missing-data   # the stuck/escalate case
    ..\\.venv\\Scripts\\python agent.py jailbreak      # the prompt-injection refusal case

Every run ends by showing the drafted status update in a FINAL STATUS UPDATE block
(or LAST DRAFT, held, if a bound trips), and saves it to run-output/. That file is
always a draft held for a human, it is never posted, there is no publish tool.

Runs on Claude via the Claude Agent SDK, using your Claude CLI login (run
`claude auth login` once). No API key needed. Model and bounds are read from env so
you can tune them, that tuning is your M5 deliverable.

The SDK runs the tool-calling turns itself, so the bounds are handed to it as
explicit options (max_turns, max_budget_usd) AND re-checked here in our own code:
every tool call is counted by Bounds, and the critic<->drafter revision loop is
plain Python below. Keep the bounds explicit if you rework it.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
from pathlib import Path

from claude_agent_sdk import (ClaudeAgentOptions, ClaudeSDKClient, ResultMessage,
                              create_sdk_mcp_server, tool)

import tools
from critic import review
from prompts import CORTEX_SYSTEM

try:  # load .env if python-dotenv is installed; harmless if it isn't
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# --- Bounds (your M5 deliverable: tune these and justify them) ----------------
MODEL = os.environ.get("CORTEX_MODEL", "haiku")
# The critic is the last automated check before a human, so it gets a stronger model.
CRITIC_MODEL = os.environ.get("CORTEX_CRITIC_MODEL", "sonnet")
# Demo only (M3): tamper with Cortex's FIRST draft so you can watch the critic reject it.
DEMO_BAD_DRAFT = os.environ.get("CORTEX_DEMO_BAD_DRAFT", "") == "1"

BAD_DRAFT_TAMPER = (
    "\n\n**Status: GREEN.** We will ship GA on Nov 15. Activation hit 52% this week "
    "(PR #999 closed the gap).\n")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "8"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.20"))
DAILY_CAP_USD = float(os.environ.get("CORTEX_DAILY_CAP_USD", "5.00"))  # across all runs today
TIMEOUT_S = float(os.environ.get("CORTEX_TIMEOUT_S", "120"))           # wall clock per run
MAX_QUEUE_ITEMS = tools.max_queue_items()      # enforced in tools.propose_stories
MAX_STALE_DAYS = tools.max_stale_days()        # enforced in tools.get_activity
# Kill switch: create this file (e.g. `New-Item 00-build/CORTEX_KILL`) and every run
# halts at its next step; delete it to resume. Checked outside the model.
KILL_FILE = Path(__file__).parent / "CORTEX_KILL"
SPEND_LEDGER = Path(__file__).parent / "run-output" / "spend-ledger.json"

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_project", "description": "Look up a project by its ID (status, flags, linked PRD).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "get_activity",
        "description": "Pull recent engineering activity for a project (merged PRs, open issues, Sev-1s).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {
        "name": "search_past_updates",
        "description": "Search previous status updates and decisions for tone and precedent.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_roadmap",
        "description": "Return the roadmap. Some items are flagged confidential/embargoed.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_norms", "description": "Return the team norms / PM playbook the agent must follow.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "propose_stories",
        "description": "Queue a set of backlog stories for human approval (creates nothing; rejected above the item cap).",
        "parameters": {"type": "object", "properties": {
            "project_id": {"type": "string"},
            "stories": {"type": "array", "items": {"type": "string"}},
            "reason": {"type": "string"}}, "required": ["project_id", "stories"]}}},
]

SERVER = "cortex"  # the SDK exposes our tools as mcp__cortex__<tool name>


class Bounds:
    """Tracks spend and tool steps, and trips the caps. Enforced OUTSIDE the model."""

    def __init__(self):
        self.cost = 0.0
        self.steps = 0
        self.last_draft = ""

    def over_cap(self) -> bool:
        return self.cost >= COST_CAP_USD

    def out_of_steps(self) -> bool:
        return self.steps >= MAX_ITERATIONS


def killed() -> bool:
    return KILL_FILE.exists()


def spent_today() -> float:
    try:
        ledger = json.loads(SPEND_LEDGER.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return 0.0
    return float(ledger.get(tools.today().isoformat(), 0.0))


def record_spend(cost: float) -> None:
    """Add this run's spend to today's total, so the daily cap sees every run."""
    try:
        ledger = json.loads(SPEND_LEDGER.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        ledger = {}
    day = tools.today().isoformat()
    ledger[day] = round(float(ledger.get(day, 0.0)) + cost, 6)
    SPEND_LEDGER.parent.mkdir(exist_ok=True)
    SPEND_LEDGER.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def build_tool_server(bounds: Bounds, source_log: list[str]):
    """Wrap each function in tools.py as an SDK tool. Every call is counted and
    printed, and once the iteration cap is spent the tool refuses instead of running."""

    def make(spec: dict):
        fn = spec["name"]

        @tool(fn, spec["description"], spec["parameters"])
        async def handler(args: dict) -> dict:
            if killed():
                return {"content": [{"type": "text", "text": json.dumps(
                    {"error": "kill_switch", "action": "stop now and ESCALATE"})}],
                    "is_error": True}
            if bounds.out_of_steps():
                return {"content": [{"type": "text", "text": json.dumps(
                    {"error": "iteration_cap_reached", "action": "stop and ESCALATE"})}],
                    "is_error": True}
            bounds.steps += 1
            result = tools.TOOLS[fn](**args)
            source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
            print(f"\n[step {bounds.steps}] TOOL {fn}({args})")
            print(f"          -> {json.dumps(result)[:300]}")
            return {"content": [{"type": "text", "text": json.dumps(result)}]}

        return handler

    return create_sdk_mcp_server(
        name=SERVER, tools=[make(s["function"]) for s in TOOL_SCHEMAS])


OUTPUT_DIR = Path(__file__).parent / "run-output"


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


def emit_deliverable(which: str, draft: str, *, accepted: bool,
                     reason: str, cost: float) -> None:
    """Surface AND persist Cortex's drafted status update so it can't get lost in
    the scroll-back. This is still a DRAFT held for human review, never a post,
    there is no publish tool, and an escalated run is held on purpose.

    Runs on every exit: an accepted pass prints the FINAL update; a bound trip or
    escalation prints the LAST draft it managed to write plus why it was held.
    """
    banner("FINAL STATUS UPDATE (draft, validator-approved, NOT posted)" if accepted
           else "LAST DRAFT (held, NOT posted, escalated to a human)")
    if draft.strip():
        print(draft.rstrip())
    else:
        print("(Cortex stopped before it produced a draft, nothing to show.)")
    if not accepted:
        print(f"\nWhy it was held: {reason}")

    if draft.strip():
        OUTPUT_DIR.mkdir(exist_ok=True)
        out = OUTPUT_DIR / f"status-update-{which}.md"
        state = "accepted by validator" if accepted else "HELD, escalated"
        out.write_text(
            f"<!-- Cortex draft, {state}; NOT posted. Run cost ~ ${cost:.4f}. -->\n"
            f"<!-- {reason} -->\n\n{draft.rstrip()}\n", encoding="utf-8")
        print(f"\nSaved draft -> {out.relative_to(Path(__file__).parent)}  "
              f"(for your review, nothing was posted)")


async def run(which: str, bounds: Bounds) -> None:
    task = tools.get_task(which)
    if "error" in task:
        print(task)
        return

    banner(f"CORTEX RUN, fixture: task-{which}  (auto-queue cap {MAX_QUEUE_ITEMS} items, "
           f"stale after {MAX_STALE_DAYS} days, today {tools.today().isoformat()})")
    print(task["body"])

    source_log: list[str] = [task["body"]]
    options = ClaudeAgentOptions(
        model=MODEL,
        system_prompt=CORTEX_SYSTEM,
        mcp_servers={SERVER: build_tool_server(bounds, source_log)},
        tools=[],                       # no built-in tools: no files, no shell, no web
        allowed_tools=[f"mcp__{SERVER}__{s['function']['name']}" for s in TOOL_SCHEMAS],
        permission_mode="dontAsk",      # anything not allowed above is denied, never prompted
        setting_sources=[],             # ignore your personal Claude settings and CLAUDE.md
        strict_mcp_config=True,         # only Cortex's tools, none of your other connectors
        max_turns=MAX_ITERATIONS,       # SDK-enforced loop cap (also counted in Bounds)
        max_budget_usd=COST_CAP_USD,    # SDK-enforced spend cap (also checked in Bounds)
        cwd=str(Path(__file__).parent),
    )

    prompt = f"PM task brief:\n\n{task['body']}"
    revisions = 0

    async with ClaudeSDKClient(options=options) as client:
        while True:
            if killed():
                banner(f"KILL SWITCH, {KILL_FILE.name} exists. Halting now, nothing posted.")
                emit_deliverable(which, bounds.last_draft, accepted=False,
                                 reason="kill switch engaged", cost=bounds.cost)
                return
            if bounds.over_cap():
                reason = f"cost cap ${COST_CAP_USD} hit at ${bounds.cost:.4f}"
                banner(f"BOUND TRIPPED, {reason}. Halting and escalating to a human.")
                emit_deliverable(which, bounds.last_draft, accepted=False,
                                 reason=reason, cost=bounds.cost)
                return

            await client.query(prompt)
            result = None
            async for msg in client.receive_response():
                if isinstance(msg, ResultMessage):
                    result = msg
            # The SDK reports spend for the session so far, so keep the larger figure.
            bounds.cost = max(bounds.cost, (result.total_cost_usd or 0.0) if result else 0.0)

            if result is None or result.subtype == "error_max_turns" or bounds.out_of_steps():
                banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
                       f"Escalating. Run cost ≈ ${bounds.cost:.4f}")
                emit_deliverable(which, bounds.last_draft, accepted=False,
                                 reason=f"max iterations ({MAX_ITERATIONS}) reached",
                                 cost=bounds.cost)
                return
            if result.subtype == "error_max_budget_usd":
                bounds.cost = max(bounds.cost, COST_CAP_USD)
                continue  # loops back to the cost-cap check above
            if result.subtype != "success" or result.is_error:
                detail = (result.result or "").strip().splitlines()[:1]
                reason = f"agent run failed ({result.subtype}{': ' + detail[0] if detail else ''})"
                banner(f"RUN ERROR, {reason}. Escalating.")
                emit_deliverable(which, bounds.last_draft, accepted=False,
                                 reason=reason, cost=bounds.cost)
                return

            # Cortex produced a proposed output. Validate it.
            proposed = result.result or ""
            if DEMO_BAD_DRAFT and revisions == 0:
                proposed += BAD_DRAFT_TAMPER
                print("\n[demo] CORTEX_DEMO_BAD_DRAFT=1: injected a firm ship date, a RAG "
                      "status, an invented metric and a fake PR ID into this first draft.")
            bounds.last_draft = proposed
            print(f"\n[step {bounds.steps}] PROPOSED OUTPUT:\n{proposed}")

            banner(f"CRITIC ({CRITIC_MODEL}), independent validation")
            started = time.monotonic()
            verdict = await review(CRITIC_MODEL, proposed, "\n".join(source_log))
            bounds.cost += verdict["_cost"]
            print(json.dumps({k: v for k, v in verdict.items() if k != "_cost"}, indent=2))
            print(f"(critic call: ${verdict['_cost']:.4f}, {time.monotonic() - started:.1f}s)")

            if verdict["verdict"] == "pass":
                escalations = [ln.strip() for ln in proposed.splitlines()
                               if ln.strip().startswith("ESCALATE:")]
                if escalations:
                    reason = escalations[-1]
                    banner(f"ESCALATED, Cortex stopped and handed this to a human. "
                           f"Nothing drafted for posting, nothing posted. "
                           f"Run cost ≈ ${bounds.cost:.4f}")
                    emit_deliverable(which, proposed, accepted=False,
                                     reason=reason, cost=bounds.cost)
                    return
                banner(f"HITL CHECKPOINT, status update + any proposed stories queued for "
                       f"your review. Nothing posted, no commitments made. "
                       f"Run cost ≈ ${bounds.cost:.4f}")
                emit_deliverable(which, proposed, accepted=True,
                                 reason="validator passed", cost=bounds.cost)
                return

            if revisions >= MAX_REVISIONS:
                reason = f"validator rejected {MAX_REVISIONS}x (revision cap)"
                banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                       f"instead of looping. Run cost ≈ ${bounds.cost:.4f}")
                emit_deliverable(which, bounds.last_draft, accepted=False,
                                 reason=reason, cost=bounds.cost)
                return

            revisions += 1
            print(f"\n-> critic rejected; revision {revisions}/{MAX_REVISIONS}")
            prompt = ("A validator rejected that for these reasons: "
                      f"{verdict['reasons']}. Fix it or escalate.")
            if DEMO_BAD_DRAFT and revisions == 1:
                prompt = f"The draft as submitted was:\n\n{proposed}\n\n{prompt}"


async def main(which: str = "happy") -> None:
    """The bounds that wrap a whole run: kill switch, daily spend cap, wall-clock
    timeout. Every run's spend is recorded so the daily cap sees all of them."""
    bounds = Bounds()
    if killed():
        banner(f"KILL SWITCH, {KILL_FILE.name} exists. Not starting.")
        return
    if spent_today() >= DAILY_CAP_USD:
        banner(f"DAILY CAP, ${spent_today():.4f} already spent today "
               f"(cap ${DAILY_CAP_USD}). Not starting, a human must raise the cap.")
        return
    try:
        await asyncio.wait_for(run(which, bounds), timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        reason = f"timeout ({TIMEOUT_S:.0f}s) reached"
        banner(f"BOUND TRIPPED, {reason}. Halting and escalating to a human.")
        emit_deliverable(which, bounds.last_draft, accepted=False,
                         reason=reason, cost=bounds.cost)
    finally:
        record_spend(bounds.cost)


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "happy"))
