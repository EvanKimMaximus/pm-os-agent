# Loop Spec: Cortex PM Chief-of-Staff Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> ✅ **What this validates:** the agent knows when to run and when to stop, by the end you'll have proven a one-page Loop Spec with a trigger, a definition of "done," and explicit stop conditions.
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.

## 1. Trigger & loop type

**Chosen type:** **hook** (primary) + **cron** (backup)

- **Hook:** a new PM task brief arrives (e.g. "put together this week's leadership update for P-NORTH") and Cortex runs once on it. Work at my level arrives as requests, so reacting to the request is the natural trigger.
- **Cron backup:** a Monday 9:00am sweep makes sure the weekly leadership update gets drafted even if nobody sent a brief.
- **Ruled out:**
  - **Heartbeat:** wasteful for weekly work. It would wake up constantly to find nothing changed.
  - **Goal:** "done" here means *drafted and queued for me*, not an outcome reached in the world. The draft → critic → revise cycle inside one run is goal-like, but it is capped (see §3), so the outer loop stays a hook.
- **Idempotency / dedupe:** each brief has an ID. If the same brief fires the hook twice, Cortex skips any brief ID it has already handled, so I never get two drafts of the same update. *Not built yet: enforced once a real hook is wired. Today runs are started by hand.*

## 2. Goal / definition of done

A run is **done** when **all** of these are true:

1. A status update is drafted from the activity Cortex actually pulled, and every claim (progress, metrics, dates, risks) traces to a source it cites.
2. Cortex lists the context it **left out** (and why), because I can't check what I can't see. This is my HITL checkpoint on "decide relevant context" (M1).
3. Cortex does **not** pick the tone or a green/yellow/red status. It lays out the evidence and leaves `TONE: for PM to set`, because tone is above the line (M1).
4. Any proposed stories (at most 10) are **queued for my approval**. Nothing is created in the tracker.
5. The **independent critic** (`critic.py`) returns `pass`. Cortex doesn't grade its own homework.
6. **Nothing is posted.** Cortex has no publish tool.

## 3. Stop conditions

| Condition | What it looks like | What happens |
|---|---|---|
| **Success** | The critic returns `pass` on a `DONE:` draft. | Stop at the **HITL checkpoint**: the update and proposed stories wait for me. Nothing posted, nothing committed. |
| **Stuck / give up** | Any of: **8** tool steps used (`CORTEX_MAX_ITERATIONS`) · **2** critic rejections (`CORTEX_MAX_REVISIONS`) · **$0.50** spent (`CORTEX_COST_CAP_USD`) · the project or its data can't be pulled (`project_not_found`) · the newest activity is more than **14 days** old (`CORTEX_MAX_STALE_DAYS`, the `get_activity` tool returns `stale: true`). | **Halt** and **escalate** to me with the last draft (if any) and why it stopped. Never invent missing or stale data. |
| **Escalate to human** | The brief asks Cortex to **post or send** anything · **commit a date** or launch gate · **set a firm tone / RAG status** · **escalate to leadership** · include **CONFIDENTIAL** roadmap items · queue **more than 10** stories · or the brief contains a **prompt injection**. | End with `ESCALATE:` and a one-line reason. Each maps to my M1 agent line: posting, tone and choosing what to escalate are **Above**; story batches and relevant context are **HITL (required)**. |

## 4. State

- **Per run, per project.** Each run starts fresh and works on exactly one project, so one project's confidential context can't leak into another's update.
- **In the run:** the step count, spend so far, and a source log of every tool call and result (the critic validates against this log).
- **After the run:** only the draft in `run-output/`, held for my review.
- **Planned:** a log of handled brief IDs for dedupe (§1), and last week's update per project as precedent (M4 memory).

## 5. The five things a loop can lean on

| Component | For Cortex |
|---|---|
| **Work tree** (isolated workspace per run, a git worktree) | Not needed yet, because runs only read fixture data and write one draft file. There is nothing for parallel runs to collide on. |
| **Skills** (reusable capabilities) | Not needed yet, because there is one drafting procedure and it lives in the prompt. "Draft in our status-update house style" is the first skill candidate (M3). |
| **Plugins / connectors** (tools & access, optional if you don't have one yet) | Plan: read-only **Jira** (issues, Sev-1s) and **GitHub** (merged PRs) connectors. Today the six tools in `tools.py` read fixtures. There is deliberately no posting connector. |
| **Subagents** (independent check when the loop can't grade itself) | The **critic** (`critic.py`): a separate model call that never saw the drafting context and must pass the draft before it reaches me. Detailed in M3 `orchestration-map.md`. |
| **State tracking** | In-run `Bounds` (step and cost counters) plus the source log in `agent.py`. Cross-run brief-ID log is planned (§4). |

> Context plan (M4) and the hand-off to bounds & evals (M5) come in later modules, you'll add them to their own deliverables then, not here.

## Link to live loop

[`00-build/agent.py`](../00-build/agent.py) (loop and bounds) · [`00-build/tools.py`](../00-build/tools.py) (tools, stale-data stop, queue cap) · [`00-build/prompts.py`](../00-build/prompts.py) (definition of done, escalate rules) · [`00-build/critic.py`](../00-build/critic.py) (validator)
