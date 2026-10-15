"""Seed 2-3 fabricated prior hazard records so the Follow-up screen has something
to match against without waiting on a real first visit. Run after Firestore and
the Cloud Storage bucket exist: python scripts/seed_test_data.py
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from lib import firestore as fs  # noqa: E402
from lib.risk import compute_risk  # noqa: E402

TEST_IMAGES = pathlib.Path(__file__).resolve().parent.parent / "assets" / "test-images"

SEED_HAZARDS = [
    {
        "scenario": "unprotected_edge",
        "site": "Block C, Level 4",
        "date": "2026-10-10",
        "activity": "Formwork stripping",
        "photo": "unprotected_edge_01_clear.jpg",
        "description": "Evidence suggests an open floor edge on Level 4 with no guardrail or barrier installed.",
        "confidence": "confirmed",
        "likelihood": 3,
        "severity": 3,
        "status": "action_assigned",
    },
    {
        "scenario": "obstructed_walkway",
        "site": "Block A, Ground Floor",
        "date": "2026-10-11",
        "activity": "Material delivery",
        "photo": "obstructed_walkway_01_clear.jpg",
        "description": "Evidence suggests the designated walkway is blocked by stacked materials.",
        "confidence": "confirmed",
        "likelihood": 2,
        "severity": 2,
        "status": "reviewer_confirmed",
    },
    {
        "scenario": "ppe_concern",
        "site": "Block B, Level 2",
        "date": "2026-10-12",
        "activity": "Rebar fixing",
        "photo": "ppe_concern_01_clear.jpg",
        "description": "Evidence suggests a worker without a hard hat or high-visibility vest in an active work area.",
        "confidence": "confirmed",
        "likelihood": 2,
        "severity": 2,
        "status": "action_assigned",
    },
]


def main() -> None:
    created = []
    for seed in SEED_HAZARDS:
        photo_path = TEST_IMAGES / seed["photo"]
        if not photo_path.exists():
            print(f"Skipping {seed['scenario']}: {photo_path} not found. Run generate_test_images.py first.")
            continue

        photo_url = fs.upload_evidence(photo_path.read_bytes(), seed["photo"], "image/jpeg")
        risk = compute_risk(seed["likelihood"], seed["severity"])

        hazard_id = fs.create_hazard(
            scenario=seed["scenario"],
            site=seed["site"],
            date=seed["date"],
            activity=seed["activity"],
            source_photo_url=photo_url,
            source_audio_url=None,
            ai_finding={
                "description": seed["description"],
                "confidence": seed["confidence"],
                "raw_model_output": {"seeded": True},
            },
            risk=risk.model_dump(),
            actor="seed-script",
        )
        fs.confirm_hazard(hazard_id, "seed-script")
        if seed["status"] == "action_assigned":
            fs.assign_action(
                hazard_id,
                "seed-script",
                description="Install guardrail / clear path / issue PPE as applicable.",
                owner="Site Supervisor",
                due_date="2026-10-17",
                escalation_rule="Escalate to site manager if overdue 48h",
            )
        created.append((hazard_id, seed["scenario"]))
        print(f"Created {seed['scenario']} hazard: {hazard_id}")

    print(f"\nSeeded {len(created)} fabricated prior hazard record(s) for follow-up testing.")


if __name__ == "__main__":
    main()
