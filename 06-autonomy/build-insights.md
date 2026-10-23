# Build Insights: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 4, what you learned building it
>
> ✅ **What this validates:** you can reflect on what building it taught you, by the end you'll have proven the friction, the learning, and the aha that changes how you'd design your next agent.

By Evan Kim

## Friction

Most of the friction came before I could even start the actual lab work. The template runs on OpenAI and my key kept getting rejected, so I followed a colleague's notes and moved Cortex over to the Claude Agent SDK using my Claude login. That turned into a rewrite of the main loop. Partway through, my Claude login expired and every run quietly failed. Cortex treated the error message as if it were a draft, which was a good reminder that failures need to stop the run and not slip through.

The data was the other surprise. The sample files were from June, four months old by the time I ran them, and Cortex actually noticed this on its own in the first test run. Once I added a rule to stop when activity is more than 14 days old, every run stopped until I moved the dates forward. A real feed going stale would cause the same problem, just without anyone noticing.

There were also a few small bugs around how a run ends. Cortex once wrote "ESCALATE: no escalation required", and the summary said "HITL CHECKPOINT" even when the run had escalated. None of these were hard to fix, but any of them could have caused real confusion if this were live.

## Learning

Capability isn't permission. My first instinct put story proposals on Cortex's side of the line because it could clearly figure them out. Scoring it on blast radius and measurability moved it to needing my approval. The better question isn't whether the agent can do something, it's what happens if it gets it wrong and nobody checks.

The loop matters more than the prompt. Most of the real work went into deciding what "done" means and how a run should stop, and then making those stops something the code can actually detect.

A second agent checking the work is worth it, but it isn't free. The critic caught everything I planted, including a fake launch date, a made-up metric and a PR number that doesn't exist. It also costs about five times as much as the drafting. Adding agents is a budget decision, not something to do by default.

## Aha moment

The thing that actually keeps Cortex safe is the tool it doesn't have. In the jailbreak test, the brief claimed leadership had already approved posting the confidential Orbit roadmap company-wide. Cortex refused, which was nice to see. But the real reason nothing bad could happen is that Cortex has no way to post anything at all. Instructions in a prompt are a request. What the agent can't reach is the actual control. Next time I'd start an agent design with its tools and access, and write the prompt after.

## What you'd do differently

I'd write the evals first and treat them as the spec, with a script that runs them automatically on every change instead of me reading through output.

I'd connect to real data from the start, read-only Jira and GitHub with a freshness check, instead of sample files that go stale.

I'd sort out the login and hosting question up front. A personal login on a laptop is fine for a course, but a real version needs a company API key and somewhere to run on a schedule.

I'd also set up replays of past runs early, so the worst runs become tests that catch the same problem if it ever comes back.
