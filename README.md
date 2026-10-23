# Cortex, a PM Chief-of-Staff Agent

> A bounded PM chief-of-staff that drafts the weekly leadership update and next sprint's stories from real activity, cites every claim, gets checked by an independent critic, and never posts on its own.

_Evan Kim · Advanced AI Agents (Agentic Loops for PMs) · IDEXX cohort · Oct 2026_

Repo: https://github.com/EvanKimMaximus/pm-os-agent

This repo is my final project for the Agentic Loops for PMs Certification, **Cortex**. Each module’s artifact lives in its own folder; this README is the dashboard and the pitch.

---

## Module artifacts

### M1 · The Agent Line
- **Agent-line map**: [`01-agent-line/agent-line-map.md`](01-agent-line/agent-line-map.md)

### M2 · Loop Engineering
- **Loop spec**: [`02-loop-design/loop-spec.md`](02-loop-design/loop-spec.md)

### M3 · Orchestration & Subagents
- **Orchestration map**: [`03-orchestration/orchestration-map.md`](03-orchestration/orchestration-map.md)

### M4 · Context Engineering & Memory
- **Memory & context plan**: [`04-memory-context/memory-and-context.md`](04-memory-context/memory-and-context.md)

### M5 · Bounds & Evals
- **Bounds & evals**: [`05-bounds-evals/bounds-and-evals.md`](05-bounds-evals/bounds-and-evals.md)

### M6 · Autonomy & Production
- **Production & autonomy plan**: [`06-autonomy/production-and-autonomy.md`](06-autonomy/production-and-autonomy.md)
- **Prototype write-up**: [`06-autonomy/prototype.md`](06-autonomy/prototype.md)
- **Build insights**: [`06-autonomy/build-insights.md`](06-autonomy/build-insights.md)

---

## Ship plan

### Autonomy dial (per segment)
- A PM new to Cortex ("Tesla driver") → Supervised: every draft and story batch waits for approval until Cortex has proven itself.
- Me, the Northstar PM, after a clean shadow period ("Waymo passenger", drafting lane only) → Bounded-autonomous: the Monday cron drafts and queues without me starting it; I spot-check. Tone, posting and escalation choices stay mine.
- Exec / leadership readers → Assisted: they only see what I approved and posted; Cortex never acts toward them.
- The dial never moves the M1 agent line: posting, tone/RAG status, dates and what to escalate stay above the line for everyone.

### Trust Ladder rung + eval gate
Current rung: Supervised by design, proven on fixtures only (every run ends at a HITL checkpoint or an escalation; 6/6 M5 evals pass). In production it starts at Shadow on real weekly briefs.
Eval gate Shadow → Supervised, over 4 consecutive weeks (≥4 briefs/project): EV-1 tool-call accuracy ≥95%, EV-5 jailbreak safety 100% (0 unsafe steps), critic pass ≥90% with ≤10% hitting the revision cap, EV-4 completion ≥90%, 0 invented figures/dates in my weekly spot-check.
Gate Supervised → Bounded-autonomous (drafting lane): 8 weeks with ≥95% of drafts approved with only tone edits and 0 trust incidents.
Incident record: 0 trust incidents to date (bugs found in testing were fixed, none reached a reader).

### Deployment plan
- Runtime: serverless function, triggered by the M2 hook (a new PM brief) plus a Monday 9:00 cron; ~50 s runs, no state between runs. Production auth via an API key under a company agreement, not a personal login.
- On-call: Evan Kim (PM, owner, go/no-go and the dial); backup: the Northstar engineering lead (kill switch + rollback).
- Rollback: create CORTEX_KILL (halts every run) → drop the dial a rung → remove a tool from TOOLS → git revert the last prompt/tool/model change.
- Monitoring: eval pass % per case, escalation rate and reasons, critic-reject rate, revision-cap hits, cost per run and per day (spend ledger), timeouts, trust-incident count.

### ROI metrics + widen-autonomy rule
- Outcome: ≥80% of weekly updates reach my checkpoint and are approved with only tone edits; ~45 min/week saved per project vs my shadow-period baseline.
- Cost-to-serve: ≤$0.10 model cost per completed update (measured $0.03–0.06 with the Sonnet critic) + ~5 min of my review, fully loaded.
- Trust incidents: 0 per quarter; any one freezes the dial and drops a rung.
- Widen rule: Cortex moves up one rung, for one segment, only after 4 consecutive weeks at or above every gate threshold with zero trust incidents; any single trust incident drops it back a rung immediately.

### Governance & strategy
- Compliance: no customer, clinic, patient or personal data ever enters a prompt; only project/engineering metadata. CONFIDENTIAL items (Orbit, Pulsar) flagged at source and blocked by the critic; drafts kept 30 days, gitignored.
- Safety: Cortex has no publish/create/merge/gate tool; posting, tone, dates and escalation choices stay above the line for everyone. Future posting = a single-use, per-update, per-channel credential minted only when I approve. Kill switch owned by me + eng lead.
- Reliability: 8-step cap, 120 s timeout, $0.20/run and $5/day caps, 2 critic revisions, 14-day stale-data stop, escalate on missing/stale/withheld data; model down → no draft, I write it by hand.
- Strategy: next is one-click posting to the internal team channel only, gated by 8 weeks at ≥95% approve-without-factual-edits, EV-5 at 100%, 0 incidents. Before that: automated eval runner + CI gate, replay harness, read-only Jira/GitHub connectors.

---

## Build insights

- **Friction point.** Getting it to run at all. My OpenAI key kept getting rejected, so I moved Cortex onto the Claude Agent SDK, and then the sample data turned out to be four months old, so my own stale-data rule stopped every run until I refreshed it.
- **Key learning.** Capability isn't permission. The better question isn't whether the agent can do something, it's what happens if it gets it wrong and nobody checks.
- **Aha moment.** The thing that keeps Cortex safe is the tool it doesn't have. The jailbreak claimed posting was pre-approved, and nothing could happen because Cortex has no way to post at all.

---

_Certification submission, Agentic Loops for PMs Certification._
