"""Hazard workflow + storage facade.

Every state change goes through a function here and appends to the hazard's
history, so the audit trail is identical whichever backend is active.

Backend selection (env SITEGUARD_BACKEND):
  firestore -- Firestore + Cloud Storage (production / Cloud Run)
  local     -- JSON file + ./data/evidence (offline demo, UI development)
  auto      -- (default) Firestore if Google credentials are available, else local
"""

from __future__ import annotations

import datetime as dt
import os
import random
from typing import Any, Optional

_backend = None
_backend_error: Optional[str] = None

OPEN_ACTION_STATUSES = {"reviewer_confirmed", "action_assigned", "reopened"}
_version = 0  # bumped on every write so cached reads (lib/data.py) refresh


def version() -> int:
    return _version


def _bump() -> None:
    global _version
    _version += 1


def _create(data: dict[str, Any]) -> str:
    _bump()
    return backend().create(data)


def _update(hazard_id: str, updates: dict[str, Any]) -> None:
    _bump()
    backend().update(hazard_id, updates)


def _append(hazard_id: str, field: str, item: dict[str, Any]) -> None:
    _bump()
    backend().append(hazard_id, field, item)


def raw_update(hazard_id: str, updates: dict[str, Any]) -> None:
    """Direct field write without a history entry (seeding/maintenance only)."""
    _update(hazard_id, updates)


def _make_backend():
    global _backend_error
    choice = os.environ.get("SITEGUARD_BACKEND", "auto").strip().lower()
    if choice == "local":
        from .local_store import LocalBackend

        return LocalBackend()
    if choice == "firestore":
        from .firestore import FirestoreBackend

        return FirestoreBackend()
    # auto
    try:
        import google.auth

        google.auth.default()
        from .firestore import FirestoreBackend

        return FirestoreBackend()
    except Exception as exc:  # no credentials / libs -> offline demo mode
        _backend_error = f"{type(exc).__name__}: {exc}"
        from .local_store import LocalBackend

        return LocalBackend()


def backend():
    global _backend
    if _backend is None:
        _backend = _make_backend()
    return _backend


def backend_name() -> str:
    return backend().name


def is_local() -> bool:
    return backend().name.startswith("Local")


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def new_ref(date: str) -> str:
    year = (date or now_iso())[:4]
    return f"SG-{year}-{random.randint(0, 99999):05d}"


def _history(actor: str, event: str, note: str) -> dict[str, Any]:
    return {"timestamp": now_iso(), "actor": actor, "event": event, "note": note}


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------
def upload_evidence(file_bytes: bytes, filename: str, content_type: str) -> str:
    return backend().upload_evidence(file_bytes, filename, content_type)


def read_evidence(url: str) -> bytes:
    return backend().read_evidence(url)


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
def get_hazard(hazard_id: str) -> Optional[dict[str, Any]]:
    return backend().get(hazard_id)


def list_hazards(status: Optional[str] = None, scenario: Optional[str] = None) -> list[dict[str, Any]]:
    results = backend().list(scenario=scenario)
    if status:
        results = [h for h in results if h.get("status") == status]
    results.sort(key=lambda h: h.get("created_at", ""), reverse=True)
    return results


# ---------------------------------------------------------------------------
# State changes (each one is a human decision, recorded in history)
# ---------------------------------------------------------------------------
def create_hazard(
    scenario: str,
    site: str,
    date: str,
    activity: str,
    source_photo_url: str,
    source_audio_url: Optional[str],
    ai_finding: dict[str, Any],
    risk: dict[str, Any],
    actor: str = "system",
    extra: Optional[dict[str, Any]] = None,
    note: str = "AI analysis completed; awaiting reviewer confirmation.",
) -> str:
    """Create a new hazard in the 'flagged' state. No finding without a traceable source."""
    data: dict[str, Any] = {
        "ref": new_ref(date),
        "scenario": scenario,
        "title": "",
        "site": site,
        "date": date,
        "activity": activity,
        "source_photo_url": source_photo_url,
        "source_audio_url": source_audio_url,
        "ai_finding": ai_finding,
        "risk": risk,
        "status": "flagged",
        "action": None,
        "history": [_history(actor, "flagged", note)],
        "followups": [],
        "created_by": actor,
        "created_at": now_iso(),
    }
    if extra:
        data.update(extra)
    return _create(data)


def update_details(hazard_id: str, actor: str, fields: dict[str, Any], note: str = "Reviewer updated the record details.") -> None:
    _update(hazard_id, fields)
    _append(hazard_id, "history", _history(actor, "updated", note))


def confirm_hazard(hazard_id: str, actor: str, risk_override: Optional[dict[str, Any]] = None) -> None:
    updates: dict[str, Any] = {"status": "reviewer_confirmed", "confirmed_by": actor, "confirmed_at": now_iso()}
    if risk_override:
        updates["risk"] = risk_override
    _update(hazard_id, updates)
    _append(hazard_id, "history", _history(actor, "reviewer_confirmed", "Reviewer confirmed the AI finding."))


def reject_hazard(hazard_id: str, actor: str, note: str = "") -> None:
    _update(hazard_id, {"status": "closed", "rejected": True, "closed_by": actor, "closed_at": now_iso()})
    _append(hazard_id, "history", _history(actor, "rejected", note or "Reviewer rejected the AI finding; no hazard present."))


def edit_finding(hazard_id: str, actor: str, new_description: str, new_risk: dict[str, Any], scenario: Optional[str] = None) -> None:
    hazard = get_hazard(hazard_id) or {}
    finding = dict(hazard.get("ai_finding") or {})
    finding["description"] = new_description
    updates: dict[str, Any] = {
        "ai_finding": finding,
        "risk": new_risk,
        "status": "reviewer_confirmed",
        "confirmed_by": actor,
        "confirmed_at": now_iso(),
    }
    if scenario:
        updates["scenario"] = scenario
    _update(hazard_id, updates)
    _append(hazard_id, "history", _history(actor, "edited", "Reviewer edited the finding before confirming."))


def assign_action(
    hazard_id: str,
    actor: str,
    description: str,
    owner: str,
    due_date: str,
    escalation_rule: str,
    priority: str = "Medium",
) -> None:
    _update(
        hazard_id,
        {
            "status": "action_assigned",
            "priority": priority,
            "action": {
                "description": description,
                "owner": owner,
                "due_date": due_date,
                "escalation_rule": escalation_rule,
                "priority": priority,
                "assigned_by": actor,
                "assigned_at": now_iso(),
            },
        },
    )
    _append(hazard_id, "history", _history(actor, "action_assigned", f"Action assigned to {owner}, due {due_date}."))


def add_followup(hazard_id: str, actor: str, photo_url: str, ai_comparison: dict[str, Any], note: str = "") -> None:
    """Record new follow-up evidence and move the hazard to pending_closure_review."""
    entry = {
        "photo_url": photo_url,
        "ai_comparison": ai_comparison,
        "note": note,
        "submitted_by": actor,
        "reviewer_decision": None,
        "timestamp": now_iso(),
    }
    _update(hazard_id, {"status": "pending_closure_review"})
    _append(hazard_id, "followups", entry)
    _append(hazard_id, "history", _history(actor, "followup_submitted", "New evidence submitted for closure review."))


def resolve_closure(hazard_id: str, actor: str, approve: bool) -> None:
    """Human approves or rejects the AI's closure recommendation on the latest follow-up."""
    hazard = get_hazard(hazard_id)
    if not hazard:
        raise ValueError(f"Hazard {hazard_id} not found")
    followups = hazard.get("followups", [])
    updates: dict[str, Any] = {}
    if followups:
        followups[-1]["reviewer_decision"] = "approved" if approve else "rejected"
        updates["followups"] = followups
    if approve:
        updates.update({"status": "closed", "closed_by": actor, "closed_at": now_iso()})
    else:
        updates["status"] = "reopened"
    _update(hazard_id, updates)
    note = "Reviewer approved closure." if approve else "Reviewer rejected closure; hazard stays open."
    _append(hazard_id, "history", _history(actor, "closure_approved" if approve else "closure_rejected", note))


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------
def get_pref(user: str, key: str, default: Any = None) -> Any:
    try:
        return backend().get_pref(user, key, default)
    except Exception:
        return default


def set_pref(user: str, key: str, value: Any) -> None:
    try:
        backend().set_pref(user, key, value)
    except Exception:
        pass
