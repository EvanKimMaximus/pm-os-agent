# Agent Line Map: Cortex PM Chief-of-Staff Agent

> Module 1 · The Agent Line
>
> ✅ **What this validates:** every risky action has a clear owner, by the end you'll have proven an above/below-the-line map with HITL checkpoints, scored on reversibility, blast radius, and measurability.

## The workflow, decision by decision

List every discrete decision or action in your agent's workflow, then score each one and place it **above** the line (a human owns it) or **below** (the agent owns it). Borderline calls get an HITL checkpoint.

| Decision / action | Reversibility (H/M/L) | Blast radius (H/M/L) | Measurability (H/M/L) | Above / Below | HITL? |
|---|---|---|---|---|---|
| Pull project state + activity | H | L | H | Below | · |
| Decide relevant context | H | M | L | HITL | required |
| Draft the update | H | L | H | Below | spot-check |
| Decide tone/commitment level | L | H | L | Above | required |
| Flag at-risk/escalation | H | M | M | HITL | spot-check |
| Choose what to escalate | L | H | M | Above | required |
| Propose a story batch (capped) | H | M | M | HITL | required |
| Post an update / approve a company-wide one | L | H | M | Above | required |

## Agent anatomy (sketch)

- **Model:** Haiku (via the Claude Agent SDK) by default, a cheap, fast model for routine drafting. If Haiku hits the revision cap, retry once on Sonnet before escalating to a human. Use a stronger model (Sonnet) for the critic, since it's the last automated check before a human. *(Planned: the build currently uses one model for both.)* A company-wide audience was considered as a trigger for a stronger model, but isn't needed while the cheaper model works well enough.
- **Tools:** `get_project`, `get_activity` (read) · `search_past_updates` · `get_roadmap` (includes confidential items it must keep out) · `get_norms` · `propose_stories` (capped at 10, queued for approval only). There is deliberately no publish/post, create/merge or launch-gate tool.
- **Memory:** nothing persists across runs yet. Each run starts fresh and reads roadmap, past updates, decision log and norms through tools. The only output is the draft in `run-output/`, held for human review.
- **Loop:** _placeholder, defined in M2 loop-spec.md_
- **Bounds:** _placeholder, defined in M5 bounds-and-evals.md_
- **Evals:** _placeholder, defined in M5 bounds-and-evals.md_

## The golden rule, applied

One sentence per decision, naming the axis that settled it.

1. **Pull project state + activity** sits **below** the line because it's easy to reverse, has a small blast radius, and is easy to verify. Deciding factor: **blast radius** ("not much can really go wrong").
2. **Decide relevant context** is **HITL (required)** because it's easy to reverse and has a medium blast radius, but it's hard to verify since you can't see what was left out. Deciding factor: **measurability**.
3. **Draft the update** sits **below** the line (spot-check) because it's easy to reverse, has a small blast radius, and is easy to verify claim by claim. Deciding factor: **reversibility** ("it is a draft").
4. **Decide tone/commitment level** sits **above** the line because it's hard to reverse, has a high blast radius, and is hard to verify. Deciding factor: **reversibility**, because once leadership reads "green," it can't be unread.
5. **Flag at-risk/escalation** is **HITL (spot-check)** because it's easy to reverse, but it has a medium blast radius and is only moderately verifiable, since misses leave no trace. Deciding factor: **measurability** ("it might miss something").
6. **Choose what to escalate** sits **above** the line because it's hard to reverse, has a high blast radius, and is moderately verifiable. Deciding factor: **blast radius**, because it decides who gets pulled in and where leadership looks.
7. **Propose a story batch (capped)** is **HITL (required)** because it's easy to reverse, but it has a medium blast radius (a sprint spent on the wrong work) and is only moderately verifiable. Deciding factor: **blast radius**.
8. **Post / approve a company-wide update** sits **above** the line because it's hard to reverse, has a high blast radius, and is moderately verifiable. Deciding factor: **blast radius** ("it is official and keeps me and my team accountable").

## Hardest call

**Propose a story batch (capped), from Below to HITL (required).**

My first instinct was **Below**: the stories come from a PRD I already work with, Cortex can work out what's important from a good PRD, and my review would catch bad ones. Pushback ("capability is not permission") and the H / M / M scores made me reconsider. In my words: "Just reconsidering the impact and true cost of not reviewing what's going on. That is an actual cost, and can cost us good progress in the commitments we make and say we will deliver to."

**Deciding axis: blast radius.** Wrong stories that slip into a sprint cost real delivery against our commitments, so every batch needs my approval.
