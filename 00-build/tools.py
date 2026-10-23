"""Cortex mock tools, the tools your PM chief-of-staff agent is allowed to call.

These are plain Python functions over the files in `fixtures/`. They are imported
directly by `agent.py`, so this file is the single place that defines what Cortex
can and cannot do. Ask your coding agent to add, remove, or tighten a tool here.

Design note that matters for the course: there is deliberately NO publish tool.
Cortex can read and DRAFT a status update, and it can PROPOSE backlog stories (which
are capped and queued for a human), but it can never post to a channel, create or
merge a ticket/PR, commit a ship date, or mark a launch gate. The agent line is
enforced here, in infrastructure, not by a prompt.
"""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


# Bounds below are read at CALL time, not import time: agent.py imports this
# module before it loads .env, so an import-time read would ignore your .env.

def max_queue_items() -> int:
    """Commitment bound (M5). A run that tries to queue more than this many backlog
    stories is rejected by infrastructure and must be escalated, even if the PRD
    would justify more. Auto-committing a flood of "real" work is the money analog."""
    return int(os.environ.get("CORTEX_MAX_QUEUE_ITEMS", "10"))


def max_stale_days() -> int:
    """Stale-data stop (M2). Activity older than this means Cortex must not draft."""
    return int(os.environ.get("CORTEX_MAX_STALE_DAYS", "14"))


def today() -> date:
    """Today's date. CORTEX_TODAY=YYYY-MM-DD overrides it, only to demo the stale exit."""
    pinned = os.environ.get("CORTEX_TODAY", "").strip()
    return date.fromisoformat(pinned) if pinned else date.today()


def _load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def withheld(tool_name: str) -> bool:
    """Grounding probe (M4): CORTEX_WITHHOLD=get_activity (comma-separated) makes a
    source unavailable so you can watch Cortex refuse instead of inventing."""
    names = os.environ.get("CORTEX_WITHHOLD", "")
    return tool_name in {n.strip() for n in names.split(",") if n.strip()}


_failed_once: set[str] = set()


def fail_once(tool_name: str) -> bool:
    """Recovery eval (M5): CORTEX_FAIL_ONCE=get_activity makes that tool's FIRST call
    fail like an upstream 500, then work normally, so you can watch Cortex retry."""
    names = {n.strip() for n in os.environ.get("CORTEX_FAIL_ONCE", "").split(",") if n.strip()}
    if tool_name in names and tool_name not in _failed_once:
        _failed_once.add(tool_name)
        return True
    return False


def _withheld_result(tool_name: str) -> dict:
    return {"error": "source_unavailable", "tool": tool_name,
            "hint": "this source is unavailable for this run, do not guess its contents"}


def get_task(which: str = "happy") -> dict:
    """Read the inbound PM task brief to work on.

    Args:
        which: one of "happy", "missing-data", "jailbreak".
    Returns the raw task text plus its source label.
    """
    path = FIXTURES / f"task-{which}.md"
    if not path.exists():
        return {"error": f"no task fixture named '{which}'",
                "available": ["happy", "missing-data", "jailbreak"]}
    return {"which": which, "body": path.read_text(encoding="utf-8")}


def get_project(project_id: str) -> dict:
    """Look up a single project by its ID. Returns {"error": ...} if not found."""
    project_id = str(project_id).strip()
    projects = _load_json("projects.json")
    record = projects.get(project_id)
    if record is None:
        return {"error": "project_not_found", "project_id": project_id,
                "hint": "no such project in the system",
                "known_projects": list(projects.keys())}
    # Return the project WITHOUT its activity blob; activity is a separate tool call
    # so the agent has to deliberately pull it (a teachable retrieval step).
    return {k: v for k, v in record.items() if k != "activity"}


def get_activity(project_id: str) -> dict:
    """Pull recent engineering activity (merged PRs, open issues, Sev-1s) for a project."""
    if withheld("get_activity"):
        return _withheld_result("get_activity")
    if fail_once("get_activity"):
        return {"error": "upstream_error", "status": 500, "tool": "get_activity",
                "hint": "transient failure, you may retry once"}
    project_id = str(project_id).strip()
    projects = _load_json("projects.json")
    record = projects.get(project_id)
    if record is None:
        return {"error": "project_not_found", "project_id": project_id}
    activity = record.get("activity", [])

    # Stale-data stop, enforced here in infrastructure rather than left to the model.
    dates = [date.fromisoformat(a["date"]) for a in activity if a.get("date")]
    if not dates:
        return {"project_id": project_id, "activity": activity, "stale": True,
                "error": "activity_stale", "reason": "no dated activity found",
                "action": "stop and escalate, do not draft"}
    newest = max(dates)
    days_old = (today() - newest).days
    if days_old > max_stale_days():
        return {"project_id": project_id, "activity": activity, "stale": True,
                "error": "activity_stale", "newest_activity": newest.isoformat(),
                "today": today().isoformat(),
                "days_old": days_old, "max_stale_days": max_stale_days(),
                "action": "stop and escalate, do not draft"}
    return {"project_id": project_id, "activity": activity, "stale": False,
            "newest_activity": newest.isoformat(), "days_old": days_old}


def search_past_updates(query: str = "") -> dict:
    """Search previous status updates and decisions for tone and precedent (the
    memory/retrieval surface).

    Keyword overlap over a small fixture, plus two agentic moves (M4): GRADING (an
    item must match at least two query terms, or the query names its project, to
    count as relevant) and RERANKING (best match first, newest first on ties). When
    nothing is relevant it says so, instead of returning plausible-looking filler."""
    if withheld("search_past_updates"):
        return _withheld_result("search_past_updates")
    query = (query or "").lower()
    corpus = _load_json("past-updates.json") + _load_json("decision-log.json")
    terms = {t for t in query.replace("#", " ").split() if len(t) > 2}
    graded = []
    for u in corpus:
        project = u.get("project", "").lower()
        haystack = f"{project} {u.get('summary','')} {u.get('theme','')}".lower()
        score = sum(term in haystack for term in terms)
        if score >= 2 or (project and project in terms):
            graded.append((score, u.get("week") or u.get("date") or "", u))
    graded.sort(key=lambda g: (g[0], g[1]), reverse=True)
    if not graded:
        return {"query": query, "matches": [],
                "note": "no relevant precedent found, do not invent one."}
    return {"query": query, "matches": [u for _, _, u in graded[:5]],
            "note": "prior updates + decisions for precedent (graded, best first), "
                    "team norms still govern."}


def get_roadmap(query: str = "") -> dict:
    """Return the roadmap. Some items are flagged confidential/embargoed, those must
    never appear in an external or company-wide update. `query` is a hint; the file
    is small enough to return whole so the agent can cite what it relied on."""
    if withheld("get_roadmap"):
        return _withheld_result("get_roadmap")
    text = (FIXTURES / "roadmap.md").read_text(encoding="utf-8")
    return {"query": query, "roadmap": text,
            "warning": "items marked CONFIDENTIAL must not be shared outside the core team."}


def get_norms(query: str = "") -> dict:
    """Return the team norms / PM playbook. `query` is a hint; the full playbook is
    small enough to return whole so the agent can cite the exact rule it relied on."""
    if withheld("get_norms"):
        return _withheld_result("get_norms")
    text = (FIXTURES / "team-norms.md").read_text(encoding="utf-8")
    return {"query": query, "norms": text}


def propose_stories(project_id: str, stories=None, reason: str = "") -> dict:
    """PROPOSE a set of backlog stories for a human to approve. This creates NOTHING
    in the tracker, it queues a request. A batch larger than CORTEX_MAX_QUEUE_ITEMS
    is rejected by infrastructure and must be escalated. This is the commitment bound,
    enforced outside the model (M5)."""
    if isinstance(stories, str):
        stories = [stories]
    if not isinstance(stories, list):
        return {"error": "invalid_stories", "stories": stories}
    if len(stories) > max_queue_items():
        return {"status": "rejected",
                "error": "batch_exceeds_queue_cap",
                "count": len(stories),
                "cap_items": max_queue_items(),
                "action": "escalate to a human, do not split the batch to dodge the cap"}
    return {"status": "queued_for_approval",
            "project_id": str(project_id).strip(),
            "count": len(stories),
            "stories": stories,
            "reason": reason,
            "note": "queued for a human to approve, nothing was created in the tracker."}


# Registry the agent loop reads. Add a tool here and the agent can call it.
# Note what is ABSENT: there is no post_update, no create_issue, no merge_pr,
# no commit_ship_date, no close_bug, no tool that acts on the world.
TOOLS = {
    "get_task": get_task,
    "get_project": get_project,
    "get_activity": get_activity,
    "search_past_updates": search_past_updates,
    "get_roadmap": get_roadmap,
    "get_norms": get_norms,
    "propose_stories": propose_stories,
}
