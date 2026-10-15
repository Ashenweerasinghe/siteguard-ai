"""Firestore read/write layer and Cloud Storage evidence uploads for SiteGuard AI."""

from __future__ import annotations

import datetime as dt
import os
import uuid
from typing import Any, Optional

from google.cloud import firestore, storage

_db: Optional[firestore.Client] = None
_bucket = None

HAZARDS_COLLECTION = "hazards"


def get_db() -> firestore.Client:
    global _db
    if _db is None:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        _db = firestore.Client(project=project) if project else firestore.Client()
    return _db


def get_bucket():
    global _bucket
    if _bucket is None:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        bucket_name = os.environ.get("GCS_BUCKET")
        if not bucket_name:
            raise RuntimeError("GCS_BUCKET is not set. Add it to your .env file.")
        client = storage.Client(project=project) if project else storage.Client()
        _bucket = client.bucket(bucket_name)
    return _bucket


def upload_evidence(file_bytes: bytes, filename: str, content_type: str) -> str:
    """Upload a photo/audio file to Cloud Storage, return its public URL."""
    bucket = get_bucket()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
    blob_path = f"evidence/{uuid.uuid4().hex}.{ext}"
    blob = bucket.blob(blob_path)
    blob.upload_from_string(file_bytes, content_type=content_type)
    return f"https://storage.googleapis.com/{bucket.name}/{blob_path}"


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


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
) -> str:
    """Create a new hazard in the 'flagged' state. No finding without a traceable source."""
    db = get_db()
    doc_ref = db.collection(HAZARDS_COLLECTION).document()
    history_entry = {
        "timestamp": _now(),
        "actor": actor,
        "event": "flagged",
        "note": "AI analysis completed; awaiting reviewer confirmation.",
    }
    doc_ref.set(
        {
            "scenario": scenario,
            "site": site,
            "date": date,
            "activity": activity,
            "source_photo_url": source_photo_url,
            "source_audio_url": source_audio_url,
            "ai_finding": ai_finding,
            "risk": risk,
            "status": "flagged",
            "action": None,
            "history": [history_entry],
            "followups": [],
            "created_at": _now(),
        }
    )
    return doc_ref.id


def get_hazard(hazard_id: str) -> Optional[dict[str, Any]]:
    db = get_db()
    snap = db.collection(HAZARDS_COLLECTION).document(hazard_id).get()
    if not snap.exists:
        return None
    data = snap.to_dict()
    data["id"] = snap.id
    return data


def list_hazards(status: Optional[str] = None, scenario: Optional[str] = None) -> list[dict[str, Any]]:
    db = get_db()
    query = db.collection(HAZARDS_COLLECTION)
    if status:
        query = query.where("status", "==", status)
    if scenario:
        query = query.where("scenario", "==", scenario)
    docs = query.stream()
    results = []
    for d in docs:
        data = d.to_dict()
        data["id"] = d.id
        results.append(data)
    results.sort(key=lambda h: h.get("created_at", ""), reverse=True)
    return results


def _append_history(doc_ref, actor: str, event: str, note: str) -> None:
    doc_ref.update({"history": firestore.ArrayUnion([{
        "timestamp": _now(),
        "actor": actor,
        "event": event,
        "note": note,
    }])})


def confirm_hazard(hazard_id: str, actor: str, risk_override: Optional[dict[str, Any]] = None) -> None:
    db = get_db()
    doc_ref = db.collection(HAZARDS_COLLECTION).document(hazard_id)
    updates: dict[str, Any] = {"status": "reviewer_confirmed"}
    if risk_override:
        updates["risk"] = risk_override
    doc_ref.update(updates)
    _append_history(doc_ref, actor, "reviewer_confirmed", "Reviewer confirmed the AI finding.")


def reject_hazard(hazard_id: str, actor: str, note: str = "") -> None:
    db = get_db()
    doc_ref = db.collection(HAZARDS_COLLECTION).document(hazard_id)
    doc_ref.update({"status": "closed"})
    _append_history(doc_ref, actor, "rejected", note or "Reviewer rejected the AI finding; no hazard present.")


def edit_finding(hazard_id: str, actor: str, new_description: str, new_risk: dict[str, Any]) -> None:
    db = get_db()
    doc_ref = db.collection(HAZARDS_COLLECTION).document(hazard_id)
    doc_ref.update({
        "ai_finding.description": new_description,
        "risk": new_risk,
        "status": "reviewer_confirmed",
    })
    _append_history(doc_ref, actor, "edited", "Reviewer edited the finding before confirming.")


def assign_action(
    hazard_id: str,
    actor: str,
    description: str,
    owner: str,
    due_date: str,
    escalation_rule: str,
) -> None:
    db = get_db()
    doc_ref = db.collection(HAZARDS_COLLECTION).document(hazard_id)
    doc_ref.update({
        "status": "action_assigned",
        "action": {
            "description": description,
            "owner": owner,
            "due_date": due_date,
            "escalation_rule": escalation_rule,
        },
    })
    _append_history(doc_ref, actor, "action_assigned", f"Action assigned to {owner}, due {due_date}.")


def add_followup(
    hazard_id: str,
    actor: str,
    photo_url: str,
    ai_comparison: dict[str, Any],
) -> None:
    """Record new follow-up evidence and move the hazard to pending_closure_review."""
    db = get_db()
    doc_ref = db.collection(HAZARDS_COLLECTION).document(hazard_id)
    followup_entry = {
        "photo_url": photo_url,
        "ai_comparison": ai_comparison,
        "reviewer_decision": None,
        "timestamp": _now(),
    }
    doc_ref.update({
        "status": "pending_closure_review",
        "followups": firestore.ArrayUnion([followup_entry]),
    })
    _append_history(doc_ref, actor, "followup_submitted", "New evidence submitted for closure review.")


def resolve_closure(hazard_id: str, actor: str, approve: bool) -> None:
    """Human approves or rejects the AI's closure recommendation on the latest follow-up."""
    db = get_db()
    doc_ref = db.collection(HAZARDS_COLLECTION).document(hazard_id)
    hazard = get_hazard(hazard_id)
    if not hazard:
        raise ValueError(f"Hazard {hazard_id} not found")

    followups = hazard.get("followups", [])
    if followups:
        followups[-1]["reviewer_decision"] = "approved" if approve else "rejected"
        doc_ref.update({"followups": followups})

    new_status = "closed" if approve else "reopened"
    doc_ref.update({"status": new_status})
    note = "Reviewer approved closure." if approve else "Reviewer rejected closure; hazard stays open."
    _append_history(doc_ref, actor, "closure_approved" if approve else "closure_rejected", note)
