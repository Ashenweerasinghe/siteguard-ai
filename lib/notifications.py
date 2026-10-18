"""Notification feed derived from hazard history + computed due-date alerts.

No separate notifications collection is needed: every state change is already
recorded in a hazard's history, which keeps the feed and the audit trail in sync.
"Read" state is a per-user last-seen timestamp stored via store.set_pref.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from . import store, ui

_EVENTS = {
    "flagged": ("New observation logged", "add_a_photo", "blue"),
    "reviewer_confirmed": ("Hazard confirmed by reviewer", "verified", "amber"),
    "edited": ("Finding edited and confirmed", "edit_note", "amber"),
    "updated": ("Record updated", "edit", "gray"),
    "rejected": ("Finding rejected - no hazard", "do_not_disturb_on", "gray"),
    "action_assigned": ("Corrective action assigned", "assignment_ind", "blue"),
    "followup_submitted": ("Evidence submitted for verification", "published_with_changes", "violet"),
    "closure_approved": ("Hazard closed", "task_alt", "green"),
    "closure_rejected": ("Closure rejected - hazard reopened", "replay", "red"),
}


def build(hazards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for h in hazards:
        title = ui.hazard_title(h)
        where = h.get("site", "")
        for i, e in enumerate(h.get("history", [])):
            label, icon, color = _EVENTS.get(e.get("event"), (e.get("event", "Update").replace("_", " ").title(), "info", "gray"))
            items.append({
                "id": f"{h['id']}:{i}",
                "ts": e.get("timestamp", ""),
                "title": label,
                "body": f"{title} - {where}" + (f". {e['note']}" if e.get("event") == "action_assigned" else ""),
                "actor": e.get("actor", ""),
                "icon": icon, "color": color, "hazard_id": h["id"], "kind": "event",
            })
        action = h.get("action") or {}
        if h.get("status") in {"action_assigned", "reopened"} and action.get("due_date"):
            state = ui.due_state(action["due_date"])
            due = dt.date.fromisoformat(action["due_date"][:10])
            if state == "overdue":
                ts = dt.datetime.combine(due + dt.timedelta(days=1), dt.time(0, 0), tzinfo=ui.TZ)
                items.append({"id": f"{h['id']}:overdue", "ts": ts.isoformat(), "title": "Action overdue",
                              "body": f"{title} - {action.get('owner', '')} was due {ui.fmt_date(action['due_date'])}",
                              "actor": "system", "icon": "alarm", "color": "red", "hazard_id": h["id"], "kind": "alert"})
            elif state == "soon":
                ts = max(dt.datetime.combine(due - dt.timedelta(days=2), dt.time(8, 0), tzinfo=ui.TZ),
                         ui.parse_iso((action.get("assigned_at") or store.now_iso())))
                items.append({"id": f"{h['id']}:soon", "ts": ts.isoformat(), "title": "Action due soon",
                              "body": f"{title} - {action.get('owner', '')} due {ui.fmt_date(action['due_date'])}",
                              "actor": "system", "icon": "schedule", "color": "amber", "hazard_id": h["id"], "kind": "alert"})
    now = ui.now_local()
    items = [n for n in items if (ui.parse_iso(n["ts"]) or now) <= now + dt.timedelta(minutes=1)]
    items.sort(key=lambda n: ui.parse_iso(n["ts"]) or now, reverse=True)
    return items


def last_seen(username: str) -> str:
    return store.get_pref(username, "notifications_seen_at", "") or ""


def mark_all_read(username: str) -> None:
    store.set_pref(username, "notifications_seen_at", store.now_iso())


def is_unread(item: dict[str, Any], seen: str, me: str) -> bool:
    if item["actor"] == me:
        return False
    if not seen:
        return True
    a, b = ui.parse_iso(item["ts"]), ui.parse_iso(seen)
    return bool(a and b and a > b)


def unread_count(items: list[dict[str, Any]], username: str, me: str) -> int:
    seen = last_seen(username)
    return sum(1 for n in items if is_unread(n, seen, me))
