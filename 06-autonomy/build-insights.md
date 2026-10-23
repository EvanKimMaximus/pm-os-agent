# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it
>
> ✅ **What this validates:** you can reflect on what building it taught you, by the end you'll have proven the friction, the learning, and the aha that changes how you'd design your next agent.

## Friction

- **Getting it to run at all.** The template runs on OpenAI and my key was rejected, so I switched Cortex to the Claude Agent SDK on my Claude login, following a colleague's runbook. That meant rewriting the core loop. The SDK runs its own loop, so I had to keep every bound visible as explicit options *plus* our own counters. Later my CLI sign-in expired mid-module, and every run "succeeded" with an auth error as its draft until I made run errors stop the loop.
- **The data was quietly stale.** The shipped fixtures ended in June, four months before I ran them. Cortex noticed it on its own in the first smoke test. Once I added a 14-day stale-data stop, every run escalated until I shifted the fixture dates. A real feed would have the same problem silently.
- **Exits are fiddly.** Cortex wrote "ESCALATE: no escalation required", the banner said "HITL CHECKPOINT" after an escalation, and the queue cap from `.env` was ignored because it was read before `.env` loaded. Each was small, and each would have been an incident in production.

## Learning

1. **Capability is not permission.** My first instinct put story proposals below the line because Cortex "can figure it out". The scores (Medium blast radius, Medium measurability) moved it to HITL. The question is never "can it?" but "what does it cost if it's wrong and nobody checks?"
2. **The loop is the product, not the prompt.** Most of the real work was the definition of done and the three exits (success, stuck, escalate), and making them *detectable* in code, not vibes in a prompt.
3. **An independent critic earns its cost, and the cost is real.** The Sonnet critic caught every planted problem (fake GA date, "GREEN", invented 52%, fake PR #999), but it costs about 5× the drafting. Splitting into agents is a budget decision, not a default.

## Aha moment

**The missing tool is the real bound.** In the jailbreak run, the brief said posting Orbit company-wide was "pre-authorized by leadership". Cortex refused, but what actually made that harmless was that Cortex has no publish tool at all. Good behaviour in the prompt is a suggestion; what the agent *can't reach* is the control. I'd now design every agent from its tool list and credentials first, and its prompt second.

## What you'd do differently

- **Write the evals first**, as the PRD, and build the scripted eval runner and CI gate before the features, so every prompt change is tested automatically instead of by reading traces.
- **Start on real, read-only data connectors** (Jira/GitHub) with freshness checks from day one, instead of fixtures that rot.
- **Decide auth and runtime up front:** API key under a company agreement and a serverless runtime, not a personal login on a laptop.
- **Build the replay harness early**, so my worst runs become regression tests immediately.
