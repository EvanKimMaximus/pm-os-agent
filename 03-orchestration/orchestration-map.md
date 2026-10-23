# Orchestration Map: Cortex PM Chief-of-Staff Agent

> Module 3 · Orchestration & Subagents, ★ Deliverable 3
>
> ✅ **What this validates:** nothing advances unchecked, by the end you'll have proven a justified topology, a roster, and a validator with a defined fail action.
>
> Builds on your M2 Loop Spec. Only split one agent into a team when there's a real reason, coordination has a cost.

## 1. Why split? (or why not)

**Today Cortex is one hook-triggered loop** (M2): it pulls one project's data, drafts the update and story proposals, and stops at my review checkpoint.

**I split exactly once, for one reason: an independent validator.** Cortex can't be trusted to grade its own draft. The agent that wrote it is the worst judge of whether it's right. A second agent that never saw the drafting context catches what the drafter can't.

| Reason | Applies? | Why / why not |
|---|---|---|
| Separation of concerns | No | There's one drafting job. Strict rules are checked by the critic, not mixed into a second drafter. |
| Parallelism | No | One project per run on small data. A run takes under a minute, so there's no time to win back. |
| **Independent validator** | **Yes** | The drafter must not grade its own homework. This is the one split that earns its cost. |
| Context-window pressure | No | A full run (brief, project, activity, norms, roadmap, past updates) fits easily in one window. |

No research subagent or GitHub/Jira reader: those are tools Cortex already calls, not jobs that need their own reasoning.

## 2. Topology

**Pattern:** single + subagents (one drafter, one critic)

```
[PM task brief] → [Cortex · Haiku: pull data via 6 tools, draft update + queue stories]
                → [Critic · Sonnet: check the draft against the source log]
                     fail → back to Cortex with the failed checks (max 2 revisions) → then ESCALATE to me
                     pass → [PM review checkpoint] → queued for me, nothing posted
```

## 3. Roster

| Agent / subagent | Responsibility | Runs which Loop Spec |
|---|---|---|
| **Cortex** (chief of staff) · Haiku | Pulls project data with its 6 tools, drafts the update, lists what it left out, queues stories (capped at 10), or escalates. Never sets tone, never posts. | M2 loop (hook + Monday cron backup) |
| **Critic** (validator) · Sonnet | Checks each proposed output against the 5 rules in §5 and returns pass/fail with reasons. No tools, no memory of the drafting conversation. | Validation step inside the M2 loop, run once per draft |

## 4. Communication & hand-offs

| From → to | What passes | Form |
|---|---|---|
| Cortex → critic | The proposed output, plus the **source log**: every tool call Cortex made and its full result | Plain text in one fresh model call |
| Critic → loop | `{"verdict": "pass" \| "fail", "reasons": [...]}` | JSON, schema-validated by the SDK |
| Loop → Cortex (on fail) | The critic's reasons, as the next turn: "A validator rejected that for these reasons: … Fix it or escalate." | Text, same Cortex session |
| Loop → me (on pass or escalate) | The draft and why it stopped, printed and saved to `run-output/` | Markdown file, nothing posted |

All hand-offs are plain **in-process** calls in `agent.py`. No A2A. Cortex's own tools are exposed through the SDK's in-process MCP server, but that's plumbing, not agent-to-agent messaging. I'd only adopt MCP/A2A between agents once those specs settle.

## 5. The validator

- **What the critic checks** (in `CRITIC_SYSTEM`, `00-build/prompts.py`):
  1. **Correct project and real IDs:** names the right project and only PR/issue IDs that appear in the pulled data.
  2. **Every figure is traceable:** progress, metrics and dates all come from the pulled data. No invented numbers.
  3. **No commitments Cortex may not make:** no ship/GA date, no launch gate, and **no green/yellow/red status or firm tone chosen by Cortex** (tone is mine, M1).
  4. **A "left out" list is present:** what Cortex chose not to include, and why (my M1 HITL on relevant context).
  5. **Nothing leaks or acts:** no CONFIDENTIAL roadmap items, nothing posted/created/merged, stories only queued and within the cap. Escalating after a tool rejection or a stale-data stop counts as correct.
- **Fail action:** **revise**. Cortex gets the specific failed checks back and redrafts in the same session.
- **Revision cap:** **2** (`CORTEX_MAX_REVISIONS`). If the third draft still fails, Cortex stops and **escalates to me** with the last draft and the reasons, instead of looping.
- **Pass action:** the draft goes to **my review checkpoint**. It never auto-sends, because posting is above the line (M1).
- **Why Sonnet:** the critic is the last automated check before me, so it gets the stronger model (`CORTEX_CRITIC_MODEL`), while drafting stays on cheap Haiku.

**Evidence:** `CORTEX_DEMO_BAD_DRAFT=1` tampers with Cortex's first draft, adding a firm GA date, "Status: GREEN", an invented 52% metric and a fake PR #999. The critic rejected it on checks 1, 2 and 3. Cortex revised, and the revised draft passed (Screenshot 2 in `06-autonomy/prototype.md`).

## 6. State: shared vs isolated

- **Shared** (both see it): the **source log** (tool calls and results) and the **proposed draft**. That's the ground truth the critic checks against.
- **Isolated to Cortex:** its system prompt, its conversation and reasoning, and its tool access. The critic never sees *how* Cortex got to the draft, so it can't inherit its blind spots.
- **Isolated to the critic:** its own rules and reasoning. Only the short `reasons` list flows back to Cortex, not the critic's scratch work.
- **Carried from M2:** everything is per run and per project. Nothing crosses projects, and nothing persists between runs except the saved draft.

## 7. Cost & latency budget

Measured on the 2026-10-23 demo run (Haiku drafter, Sonnet critic):

| | Extra model calls | Cost | Added latency |
|---|---|---|---|
| **Per draft** | +1 critic call | about **$0.03** per critic call (the whole Haiku drafting run was about $0.006) | about **8–11 s** per critic call |
| **Typical pass (1 draft)** | 1 critic call | about **$0.035** per run | about 10 s |
| **Worst case at the revision cap** (3 drafts, 3 critic calls) | 3 critic calls + 2 redrafts | about **$0.10** per run | about 30–35 s of critic time, about 1 min end to end |

**Takeaway:** the critic now costs about **5×** the drafting. That's the price of independence plus a stronger model, and still far under the **$0.50** per-run cap. In M5 I'll bound it explicitly: the revision cap (2) and the cost cap already cap the worst case, and a timeout on the critic call is the missing bound.
