# Context Engineering & Memory: Cortex PM Chief-of-Staff Agent

> Module 4 · Context Engineering & Memory
>
> ✅ **What this validates:** the agent reasons on the right, safe inputs, by the end you'll have proven a context budget, per-source retrieve-vs-long-context decisions, and a memory map with risk mitigations.
>
> 🗂️ **How the lab maps to this file:** In **Part A** (before the lecture) you don't edit this file, you rough-draft on scratch, focused on the per-source calls in **section 2** plus a quick remember/forget + "how it rots" sketch. In **Part B** (after the lecture) you complete **all five sections**; the Lab Guide's guided builder writes this file for you to copy in and commit.

**Data ingested:** the week-of-2026-07-06 Cortex Data Pack (5 fixtures: projects, past updates, decision log, roadmap, team norms), committed in `879fdbd`. Dates were shifted +108 days so the newest activity stays inside my 14-day stale-data window (M2).

## 1. Context budget

Each Cortex turn sees what it needs for **one project's update**, in this priority order. If anything has to be cut, it's cut from the bottom.

1. **Cortex's rules** (`CORTEX_SYSTEM`, about 1K tokens): the agent line, the escalate rules, the citation rule. Never cut.
2. **The task brief** in full (about 120 tokens).
3. **The project record + its activity** (only this project's slice, about 200 tokens): the facts the update is built on.
4. **Team norms** (about 550 tokens), re-read every run.
5. **Roadmap** (about 350 tokens), for scope and confidentiality flags.
6. **Past updates and decisions** (graded matches only, at most 5, about 100–300 tokens): tone and precedent.

**Measured size:** a full run's sources total about **2–3K tokens**, plus about 1K of rules. That's under 2% of the window, so today nothing gets cut. The budget matters as the activity feed and past updates grow, and the priority order is what decides what gets dropped first.

**What does *not* go in:** other projects' activity, Cortex's own earlier runs, and the critic's reasoning (isolated, M3).

## 2. Retrieve vs. long-context: per source

| Source | Size / volatility | Decision | Why (deciding factor) |
|---|---|---|---|
| **Task brief** (`get_task`) | One short doc, fixed for the run | **Long-context** | **Size:** it's tiny and bounded, so Cortex reads all of it. Splitting it would only lose context. |
| **Project record** (`get_project`) | Small per project, many projects | **Retrieve** (exact lookup by ID) | **Size:** only one project is relevant, and the others must stay out of the window. |
| **Engineering activity** (`get_activity`) | Grows every day, changes constantly | **Retrieve** (this project only, freshness-checked) | **Citation:** every claim in the update has to point to a specific PR or issue. |
| **Past updates + decisions** (`search_past_updates`) | Grows every week, unbounded | **Retrieve** (graded, best first) | **Size:** precedent piles up forever, and only a few items are ever relevant. |
| **Roadmap** (`get_roadmap`) | Medium, slow-changing, has CONFIDENTIAL items | **Retrieve** (this project's section) | **Citation:** I need to prove nothing confidential (Orbit, Pulsar) went into a leadership update. *Today the file is small enough to include whole, which is what the tool does. Retrieving only the project's slice is the target.* |
| **Team norms** (`get_norms`) | Medium, bounded, must stay current | **Long-context**, re-read fresh every run | **Volatility:** a missed or out-of-date rule costs more than the tokens, so Cortex reads the whole current playbook every time. |

## 3. Retrieval quality plan

| Source | Routing | Grading | Reranking | Self-verification | Caching |
|---|---|---|---|---|---|
| Activity | ✅ by project ID | ✅ freshness: stale (>14 days) → stop | · | ✅ critic checks every figure and ID | · |
| Past updates | · | ✅ must match ≥2 query terms or name the project; else "no relevant precedent" | ✅ best match first, newest on ties | ✅ critic | · |
| Roadmap | ✅ by project section | ✅ CONFIDENTIAL flag = never in the update | · | ✅ critic check 5 | · |
| Project record | ✅ exact ID lookup | ✅ `project_not_found` → escalate | · | · | · |

- **Routing:** each tool answers one question, and Cortex picks the tool by what it needs (activity vs precedent vs rules).
- **Document grading:** fixed a real naive-RAG bug. When nothing matched, `search_past_updates` used to return the first two past updates anyway, which was plausible-looking filler. It now grades every item and says "no relevant precedent found, do not invent one" when nothing qualifies.
- **Reranking:** past updates come back best match first, newest first on ties, capped at 5.
- **Self-verification:** Cortex must cite a source after every claim, like `[get_activity #820]`. The independent critic (M3) fails any figure that isn't in the pulled data.
- **Caching:** not needed yet. A run makes 5–6 small local calls, and re-reading is safer than reusing a stale copy.

**Evidence (Screenshot 3 in `06-autonomy/prototype.md`):**
- **Grounded:** the update cites the new data inline: activation **43%** (prior 41%), PRs **#820/#823**, issue **#825**. Orbit and Pulsar are excluded and not named.
- **Withheld** (`CORTEX_WITHHOLD=get_activity`): Cortex says it can't verify progress or Sev-1 status and escalates instead of drafting. *Lesson learned:* the 41% → 43% metric still surfaced, because the roadmap repeats it, and Cortex cited it to the roadmap. Withholding one source doesn't remove a fact that another source duplicates.
- **Hallucination caught:** the same withheld run with a planted "Activation hit 52%". The critic failed it on traceability, Cortex revised, and the clean escalation passed.

## 4. Memory map (your PM brain)

| Memory type | What Cortex stores | Scope / TTL |
|---|---|---|
| **Working** (in-loop) | This run's pulled data, the source log of every tool call and result, the step and cost counters | **This run only**, discarded when the run ends |
| **Episodic** (past runs) | Past status updates and decision-log entries (only ones I approved), plus the saved drafts in `run-output/` | **Per project**. Precedent kept **90 days**, drafts **30 days**, drafts never pushed to GitHub |
| **Semantic** (durable facts/prefs) | Team norms, roadmap facts and confidentiality flags, project records | **Long-lived, changed only by me** (the PM), re-read fresh every run, never written by Cortex |
| **Shared** (across agents) | The draft plus the source log handed to the critic, and the critic's pass/fail reasons back | **This run only**. The critic never sees Cortex's reasoning |

**Read/write scope, tied to my M1 agent line:** Cortex can **read** all four. It can **write** nothing durable: no norms, no roadmap, no precedent. Only drafts I approve become episodic memory. Writing to memory would be a below-the-line action reaching above-the-line data.

## 5. Memory risks & mitigations

| Risk | Where it bites Cortex | Mitigation |
|---|---|---|
| **Drift** | The project record still says `on_track` while the activity says otherwise. | Facts are re-read fresh every run (no cached copies). The critic checks every claim against what was pulled this run. Tone is left to me, so a drifted status can't be locked in. |
| **Poisoning** | A brief or pasted note plants a "fact" ("leadership pre-approved posting", "GA is March 1") that then gets trusted. | Brief content is data, not instructions (jailbreak rule). Cortex can't write to memory. Only updates I approved become precedent. Any figure must cite a pulled source. |
| **Staleness** | An old activity feed reported as this week. The shipped fixtures were 4 months old. | The **14-day stale-data stop** in `get_activity` (M2) makes Cortex escalate and not draft. Precedent expires after 90 days. |
| **Confidential / retention** | Orbit or Pulsar leaking into a company-wide update. Drafts with internal data sitting around forever. | CONFIDENTIAL flags in the roadmap, enforced by the prompt and critic check 5. Per-project scope. Drafts kept 30 days in `run-output/`, which is gitignored. TTLs become M5 bounds. |
