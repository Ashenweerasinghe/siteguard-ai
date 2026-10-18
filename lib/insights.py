"""Register-wide digest for the Site Insights page.

Every number Gemini reasons over is computed here, in plain Python, exactly as
the risk matrix is. The model interprets the digest -- it never counts, and it
never sees a raw record it could miscount. That keeps a site lead able to check
any figure in the summary against the register itself.
"""

from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from . import ui
from .schema import SCENARIO_LABELS, STATUS_GROUP

# Below this many confirmed records the register cannot support a pattern read.
MIN_RECORDS = 5


def _days_between(start: str | None, end: str | None) -> int | None:
    a, b = ui.parse_iso(start), ui.parse_iso(end)
    if not a or not b:
        return None
    return max((b - a).days, 0)


def build_digest(hazards: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate the register into the compact, checkable shape Gemini is given."""
    live = [h for h in hazards if not h.get("rejected")]
    today = ui.now_local().date()

    by_status = Counter(STATUS_GROUP.get(h.get("status"), "Open") for h in live)
    by_category = Counter(SCENARIO_LABELS.get(h.get("scenario"), "Unclassified") for h in live)
    by_risk = Counter((h.get("risk") or {}).get("level", "Unrated")
                      for h in live if STATUS_GROUP.get(h.get("status")) != "Closed")

    locations: dict[str, dict[str, Any]] = {}
    for h in live:
        site = (h.get("site") or "Unspecified").strip()
        slot = locations.setdefault(site, {"total": 0, "open": 0, "categories": Counter()})
        slot["total"] += 1
        if STATUS_GROUP.get(h.get("status")) != "Closed":
            slot["open"] += 1
        slot["categories"][SCENARIO_LABELS.get(h.get("scenario"), "Unclassified")] += 1

    teams: dict[str, dict[str, int]] = {}
    overdue, due_soon = [], []
    for h in live:
        action = h.get("action") or {}
        owner = (action.get("owner") or "").strip()
        if not owner or h.get("status") == "closed":
            continue
        slot = teams.setdefault(owner, {"open": 0, "overdue": 0})
        slot["open"] += 1
        state = ui.due_state(action.get("due_date"))
        if state == "overdue":
            slot["overdue"] += 1
            overdue.append((owner, ui.hazard_title(h), action.get("due_date")))
        elif state == "soon":
            due_soon.append((owner, ui.hazard_title(h), action.get("due_date")))

    closed = [h for h in live if h.get("status") == "closed"]
    durations = [d for d in (_days_between(h.get("created_at"), h.get("closed_at")) for h in closed) if d is not None]

    recent = Counter()
    for h in live:
        day = (h.get("date") or "")[:10]
        if day:
            recent[day] += 1
    last14 = sum(recent[(today - dt.timedelta(days=i)).isoformat()] for i in range(14))
    prev14 = sum(recent[(today - dt.timedelta(days=i)).isoformat()] for i in range(14, 28))

    return {
        "generated": ui.now_local().isoformat(timespec="minutes"),
        "total_records": len(live),
        "rejected_findings": sum(1 for h in hazards if h.get("rejected")),
        "by_status": dict(by_status),
        "by_category": dict(by_category),
        "open_by_risk": dict(by_risk),
        "locations": {k: {"total": v["total"], "open": v["open"], "top_category": v["categories"].most_common(1)[0][0]}
                      for k, v in sorted(locations.items(), key=lambda kv: -kv[1]["total"])[:8]},
        "teams": dict(sorted(teams.items(), key=lambda kv: -kv[1]["overdue"])[:8]),
        "overdue_actions": [{"team": t, "hazard": h, "due": d} for t, h, d in overdue[:10]],
        "due_soon_actions": [{"team": t, "hazard": h, "due": d} for t, h, d in due_soon[:10]],
        "reopened_count": sum(1 for h in live if h.get("status") == "reopened"),
        "uncertain_findings": sum(1 for h in live if (h.get("ai_finding") or {}).get("confidence") == "uncertain"),
        "closed_count": len(closed),
        "avg_days_to_close": round(sum(durations) / len(durations), 1) if durations else None,
        "observations_last_14_days": last14,
        "observations_previous_14_days": prev14,
    }


def digest_text(d: dict[str, Any]) -> str:
    """Flatten the digest into the compact text block sent to the model."""
    def block(title: str, body: str) -> str:
        return f"{title}:\n{body}" if body else ""

    lines = [
        f"Register digest generated {d['generated']}",
        f"Confirmed records: {d['total_records']} (rejected findings excluded: {d['rejected_findings']})",
        f"By status: {d['by_status']}",
        f"By hazard category: {d['by_category']}",
        f"Open records by risk level: {d['open_by_risk']}",
        f"Reopened (closure rejected at least once): {d['reopened_count']}",
        f"Findings the model itself flagged uncertain: {d['uncertain_findings']}",
        f"Closed: {d['closed_count']}, average days from report to closure: {d['avg_days_to_close']}",
        f"Observations last 14 days: {d['observations_last_14_days']} (previous 14 days: {d['observations_previous_14_days']})",
    ]
    loc = "\n".join(f"  - {k}: {v['total']} total, {v['open']} still open, most common: {v['top_category']}"
                    for k, v in d["locations"].items())
    team = "\n".join(f"  - {k}: {v['open']} open actions, {v['overdue']} overdue" for k, v in d["teams"].items())
    od = "\n".join(f"  - {a['team']}: {a['hazard']} (due {a['due']})" for a in d["overdue_actions"])
    parts = [l for l in lines] + [p for p in (
        block("Locations", loc), block("Assignee teams", team), block("Overdue corrective actions", od)) if p]
    return "\n".join(parts)
