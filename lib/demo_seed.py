"""Fabricated demo records covering every workflow state.

Used by scripts/seed_test_data.py and by Settings -> "Load demo data". All records
are clearly marked raw_model_output={"seeded": True}. Works on either backend.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from . import store
from .risk import compute_risk

TEST_IMAGES = Path(__file__).resolve().parent.parent / "assets" / "test-images"

SEEDS = [
    dict(photo="obstructed_walkway_01_clear.jpg", scenario="obstructed_walkway", title="Materials blocking walkway",
         site="Block A, Ground Floor", activity="Material delivery", days_ago=1, L=3, S=3, state="action_assigned",
         desc="Evidence suggests the designated walkway is blocked by stacked materials.",
         action="Remove materials and keep the walkway clear", owner="Warehouse Operations", due_in=1, priority="High",
         tags=["Housekeeping", "Egress"]),
    dict(photo="unprotected_edge_02_clear.jpg", scenario="unprotected_edge", title="Open floor edge, Level 4",
         site="Block C, Level 4", activity="Formwork stripping", days_ago=4, L=3, S=3, state="action_assigned",
         desc="Evidence suggests an open floor edge on Level 4 with no guardrail or barrier installed.",
         action="Barricade the edge and install guardrail", owner="Site Supervisor", due_in=-1, priority="High",
         tags=["Work at height"]),
    dict(photo="ppe_concern_01_clear.jpg", scenario="ppe_concern", title="Worker without hard hat",
         site="Block B, Level 2", activity="Rebar fixing", days_ago=3, L=2, S=2, state="pending",
         desc="Evidence suggests a worker without a hard hat or high-visibility vest in an active work area.",
         action="Issue PPE and run a toolbox talk", owner="Safety Team", due_in=2, priority="Medium",
         after="ppe_concern_03_ambiguous.jpg", tags=["PPE"]),
    dict(photo="unprotected_edge_01_clear.jpg", scenario="unprotected_edge", title="Unguarded slab edge",
         site="Block C, Level 3", activity="Concrete pour prep", days_ago=6, L=3, S=3, state="closed",
         desc="Evidence suggests an unprotected slab edge with a drop to the level below.",
         action="Install edge protection along the slab", owner="Site Supervisor", due_in=-3, priority="High",
         after="unprotected_edge_03_ambiguous.jpg", tags=["Work at height"]),
    dict(photo="obstructed_walkway_02_clear.jpg", scenario="obstructed_walkway", title="Pallets on egress route",
         site="Warehouse A", activity="Unloading", days_ago=0, L=2, S=2, state="confirmed",
         desc="Evidence suggests pallets partly obstruct the marked egress route.", tags=["Egress"]),
    dict(photo="ppe_concern_02_clear.jpg", scenario="ppe_concern", title="Missing high-vis vest",
         site="Production Line 2", activity="Plant movement", days_ago=0, L=2, S=1, state="draft",
         desc="Evidence suggests a worker near moving plant without a high-visibility vest.", tags=["PPE"]),
]


def _ts(days_ago: float) -> str:
    return (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days_ago)).isoformat()


def seed(actor: str = "seed-script") -> list[str]:
    created = []
    today = dt.date.today()
    for s in SEEDS:
        photo_path = TEST_IMAGES / s["photo"]
        if not photo_path.exists():
            continue
        photo_url = store.upload_evidence(photo_path.read_bytes(), s["photo"], "image/jpeg")
        risk = compute_risk(s["L"], s["S"])
        date = (today - dt.timedelta(days=s["days_ago"])).isoformat()
        hid = store.create_hazard(
            scenario=s["scenario"], site=s["site"], date=date, activity=s["activity"],
            source_photo_url=photo_url, source_audio_url=None,
            ai_finding={"description": s["desc"], "confidence": "confirmed", "confidence_score": 84,
                        "raw_model_output": {"seeded": True}},
            risk=risk.model_dump(), actor=actor,
            extra={"title": s["title"], "observed_at": f"{date}T09:30:00", "tags": s.get("tags", []),
                   "people_exposed": "Site workers", "priority": s.get("priority", risk.level), "seeded": True},
        )
        state = s["state"]
        if state != "draft":
            store.confirm_hazard(hid, actor)
        if state in {"action_assigned", "pending", "closed"}:
            due = (today + dt.timedelta(days=s["due_in"])).isoformat()
            store.assign_action(hid, actor, s["action"], s["owner"], due,
                                "Escalate to site manager if overdue 48h", s["priority"])
        if state in {"pending", "closed"}:
            after = TEST_IMAGES / s["after"]
            after_url = store.upload_evidence(after.read_bytes(), s["after"], "image/jpeg")
            store.add_followup(hid, actor, after_url, {
                "comparison": "The after photo suggests the original condition is no longer visible in the same area.",
                "closure_supported": True, "confidence": "confirmed",
                "reasoning": "Seeded comparison for demo purposes.",
            }, note="Corrective work completed by the assigned team.")
        if state == "closed":
            store.resolve_closure(hid, actor, approve=True)

        # Spread timestamps out so the timeline and notifications look realistic.
        hazard = store.get_hazard(hid)
        n = len(hazard["history"])
        start = s["days_ago"] + 0.2
        hist = []
        for i, entry in enumerate(hazard["history"]):
            entry = dict(entry)
            entry["timestamp"] = _ts(max(start - (start * (i + 1) / (n + 1)), 0.01 * (n - i)))
            hist.append(entry)
        fields = {"history": hist, "created_at": hist[0]["timestamp"]}
        if hazard.get("closed_at"):
            fields["closed_at"] = hist[-1]["timestamp"]
        store.raw_update(hid, fields)
        created.append(hid)
    return created
