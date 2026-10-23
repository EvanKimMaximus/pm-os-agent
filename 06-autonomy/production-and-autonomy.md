# Production & Autonomy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it, govern it, and widen trust over time
>
> ✅ **What this validates:** you can ship it, govern it, and widen trust deliberately, by the end you'll have proven an autonomy dial, a Trust Ladder rung with its eval gate, and a governance plan.

## Autonomy Dial by segment

_Autonomy is a product decision per user, not one global setting._ The dial sets how many of Cortex's below-the-line actions still pause for a human **for that user**. It never moves my M1 agent line: posting, tone, dates and escalation choices stay above the line for everyone.

| Segment | Desired autonomy | Why |
|---|---|---|
| **A PM new to Cortex** ("Tesla driver") | **Supervised** | They need to see Cortex be right before trusting it. Every draft and every story batch waits for their approval, and they read the "left out" list each time. |
| **Me (the PM owning Northstar), after a clean shadow period** ("Waymo passenger", for drafting only) | **Bounded-autonomous, drafting lane only** | The Monday cron drafts and queues the weekly update without me starting it, and I spot-check the evidence. Tone, posting and what to escalate stay mine. |
| **Exec / leadership readers** | **Assisted** | They only ever see what I approved and posted. Cortex never acts toward them directly. At most it prepares an evidence summary I choose to share. |

## Trust Ladder

- **Current rung: Supervised by design, proven on fixtures only.** Every run ends at a HITL checkpoint or an escalation, nothing posts, and all six M5 evals pass. But Cortex has **never run on real briefs or real Jira/GitHub data**, so in production it starts one rung lower, at **Shadow**: it runs silently on the real weekly brief and I compare its draft to what I actually post.
- **Eval gate to reach the next rung (Shadow → Supervised):** over **4 consecutive weeks** of shadow runs (at least 4 weekly briefs per project), all of these, sourced from `05-bounds-evals/bounds-and-evals.md`:
  - **EV-1 tool-call accuracy ≥ 95%** (right tool, right project, every run)
  - **EV-5 safety = 100%**: 0 unsafe steps, every injection refused
  - **Critic pass rate ≥ 90%** on the first or second draft, and **≤ 10%** of runs hitting the revision cap
  - **0 invented figures or dates** in my weekly spot-check against the real data (EV-6)
  - **EV-4 completion ≥ 90%**: grounded, cited draft with left-out list reaching the checkpoint
- **Next gate (Supervised → Bounded-autonomous, drafting lane):** 8 weeks where **≥ 95%** of drafts are approved with only tone edits (no factual corrections) and **0 trust incidents**.
- **Incident record so far:** **0 trust incidents** across all recorded runs (M2–M6, fixtures). An incident is any run that posts, commits, leaks a CONFIDENTIAL item, states an invented figure that reaches me unflagged, or acts outside its bounds. Found issues so far were build bugs caught in testing, not trust incidents: a sign-in error treated as a draft, the wrong banner on escalations, and "ESCALATE: no escalation required".

## Deployment plan

- **Runtime:** **serverless function**, because the M2 loop is a **hook** (a new PM brief arrives) plus a **Monday 9:00 cron**. Both are short, bursty runs (about 50 s) with no state to keep between them, so pay-per-run fits. The function packages `00-build/` with the Claude Agent SDK. In production Cortex authenticates with an **API key under a company agreement**, not a personal Claude login: Anthropic's SDK docs specify API-key auth for products built on the SDK.
- **Operator / on-call owner:** **Evan Kim** (PM, owner) decides go/no-go and owns the dial. **Backup:** the **Northstar engineering lead**, who can pull the kill switch and roll back. Escalation path: Cortex escalates to Evan; if Evan is out, to the eng lead; anything touching confidential data goes to Evan only.
- **Rollback** (fastest first):
  1. **Kill switch:** create `CORTEX_KILL`. Every run halts at its next step.
  2. **Drop the dial a rung** for the affected segment (e.g. back to Supervised).
  3. **Disable a tool** by removing it from `TOOLS` in `tools.py`.
  4. **Revert** the last prompt/tool/model change with `git revert` and redeploy. Model pinned by `CORTEX_MODEL` / `CORTEX_CRITIC_MODEL`.
- **Runbook:** how to run (`..\.venv\Scripts\python agent.py`), pause (kill switch), replay a failed run (saved trace in `06-autonomy/screenshots/*.txt` plus the matching demo switches), and recover (delete the kill file, rerun). Lives in `06-autonomy/prototype.md` → *How to run it*.
- **Monitoring** (one dashboard, weekly review): eval pass % per case, escalation rate and reasons, critic-reject rate, revision-cap hits, cost per run and per day (spend ledger), timeouts, and the trust-incident count.

## ROI metrics (beyond adoption & tokens)

| Metric | Target |
|---|---|
| **Outcome: task completion rate** | **≥ 80%** of weekly updates reach my checkpoint and are approved with only tone edits. Captured from approve/edit decisions at the checkpoint. |
| **Outcome: time saved** | **~45 min/week per project** vs my shadow-period baseline (time I spend assembling the update by hand, logged for 4 weeks) |
| **Cost-to-serve** | **≤ $0.10 model cost per completed update** (measured today: about $0.03–0.06 with the Sonnet critic) **plus ~5 min of my review**, fully loaded including retries and escalations. Captured from the spend ledger plus review time. |
| **Trust incidents** | **0 per quarter.** Any single one freezes the dial and drops a rung. Captured from the incident log. |

## Widen-autonomy decision rule

Cortex moves up **one rung, for one segment**, only after **4 consecutive weeks at or above every gate threshold with zero trust incidents**, and **any single trust incident drops it back a rung immediately** until it re-clears the gate.

## Governance & forward strategy

- **Compliance:** no customer, clinic, patient or personal data ever enters a prompt. Cortex only sees project and engineering metadata (project records, PR/issue titles, roadmap, norms). CONFIDENTIAL/embargoed items (Orbit, Pulsar) are flagged at the source and kept out of any company-wide update (critic check 5). Drafts are kept 30 days in a gitignored folder, and nothing persists across runs.
- **Safety:** for **every** segment, **posting/sending, setting tone or RAG status, committing dates or launch gates, and choosing what to escalate stay above the line**. Cortex has no tool for any of them. Future posting uses a **single-use, per-update, per-channel credential** minted only when I approve. The **kill switch** (`CORTEX_KILL`) is owned by me and the eng lead.
- **Reliability:** 8-step iteration cap, 120 s timeout, $0.20/run and $5/day spend caps, 2-revision critic cap, 14-day stale-data stop, escalate-on-stuck for missing/stale/withheld sources. **If the model is down:** no draft. Cortex reports "Cortex unavailable" and I write that week's update by hand. Nothing ever posts by default.
- **Strategy:** the next capability is **one-click posting to the internal team channel only** (not company-wide), using the single-use approval credential, for the "me, after shadow" segment. **Gated by:** 8 weeks at ≥ 95% approve-without-factual-edits, EV-5 at 100%, and 0 trust incidents. Before that, build the automated eval runner + CI gate and the replay harness from M5, and swap fixtures for read-only Jira/GitHub connectors.
