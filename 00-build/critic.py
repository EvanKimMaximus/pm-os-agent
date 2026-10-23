"""Independent validator (M3). A separate model call that never saw the drafting
context, so it can't inherit the draft's blind spots. Returns a pass/fail verdict.
The revision cap that stops a critic<->drafter loop lives in `agent.py`.
"""

from __future__ import annotations

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

from prompts import CRITIC_SYSTEM

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "reasons": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["verdict", "reasons"],
}


async def review(model: str, proposed_output: str, source_data: str) -> dict:
    """Return {"verdict": "pass"|"fail", "reasons": [...]} for a proposed output."""
    options = ClaudeAgentOptions(
        model=model,
        system_prompt=CRITIC_SYSTEM,
        tools=[],                # the critic only reads what it is given
        setting_sources=[],
        strict_mcp_config=True,
        max_turns=3,             # room for the SDK's structured-output step
        output_format={"type": "json_schema", "schema": VERDICT_SCHEMA},
    )
    prompt = (f"SOURCE DATA Cortex used:\n{source_data}\n\n"
              f"CORTEX PROPOSED OUTPUT:\n{proposed_output}")
    result = None
    try:
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, ResultMessage):
                result = msg
    except Exception:  # the SDK raises after an error result; we already kept it
        pass

    ok = result is not None and result.subtype == "success" and not result.is_error
    verdict = result.structured_output if ok else None
    if not isinstance(verdict, dict) or "verdict" not in verdict:
        verdict = {"verdict": "fail", "reasons": ["critic returned unparseable output"]}
    verdict["_cost"] = (result.total_cost_usd or 0.0) if result else 0.0
    return verdict
