"""Deterministic stand-in for Gemini (SITEGUARD_MOCK_AI=1).

Lets the whole capture -> review -> follow-up -> closure workflow run offline, e.g.
when the free-tier quota is exhausted mid-demo. Results are keyed off the image
file name / typed note so the bundled test images give sensible output. It still
follows the non-negotiables: "evidence suggests", never "safe" or "fixed".
"""

from __future__ import annotations

from .schema import GeminiFinding, GeminiFollowup

_PRESETS = {
    "obstructed_walkway": dict(
        title="Materials obstructing walkway",
        description="Evidence suggests stacked materials are blocking a designated walkway, narrowing the egress path.",
        likelihood=2, severity=3, score=85,
        impact="Delayed evacuation and trip/fall risk for anyone using the route.",
        actions=["Remove materials from the walkway immediately", "Keep the walkway marked and clear",
                 "Review storage and delivery set-down practices", "Consider floor marking for the route"],
        team="Site Supervisor",
        evidence=["Take a wider photo of the surrounding area", "Confirm whether this is a frequently used route"],
    ),
    "unprotected_edge": dict(
        title="Open edge without guardrail",
        description="Evidence suggests an open floor edge with no guardrail, barrier, or cover installed.",
        likelihood=3, severity=3, score=88,
        impact="Fall from height for workers near the edge; risk of falling objects below.",
        actions=["Barricade the edge and restrict access", "Install a guardrail or cover over the opening",
                 "Brief the crew on working near open edges"],
        team="Site Supervisor",
        evidence=["Photo from below showing the drop height", "Confirm whether the area is in active use"],
    ),
    "ppe_concern": dict(
        title="Worker missing required PPE",
        description="Evidence suggests a worker in an active area without a hard hat or high-visibility vest.",
        likelihood=2, severity=2, score=78,
        impact="Head injury or reduced visibility to plant operators.",
        actions=["Stop work and issue the missing PPE", "Toolbox talk on PPE requirements for this zone",
                 "Check PPE stock at the site entrance"],
        team="Safety Team",
        evidence=["A closer photo of the worker's PPE", "Confirm the PPE rules posted for the zone"],
    ),
}


def _guess(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("edge", "fall", "opening", "guardrail", "height")):
        return "unprotected_edge"
    if any(k in t for k in ("ppe", "helmet", "hard hat", "vest", "harness")):
        return "ppe_concern"
    return "obstructed_walkway"


def mock_finding(image_name: str, note: str) -> GeminiFinding:
    scenario = _guess(f"{image_name} {note}")
    p = _PRESETS[scenario]
    ambiguous = "ambiguous" in image_name.lower()
    return GeminiFinding(
        scenario=scenario,
        title=p["title"],
        description=p["description"],
        confidence="uncertain" if ambiguous else "confirmed",
        confidence_score=52 if ambiguous else p["score"],
        suggested_likelihood=p["likelihood"],
        suggested_severity=p["severity"],
        potential_impact=p["impact"],
        suggested_actions=p["actions"],
        responsible_team=p["team"],
        additional_evidence=p["evidence"],
        reasoning="[Demo AI] Preset finding chosen from the file name and note -- not a real model call.",
    )


def mock_followup(note: str) -> GeminiFollowup:
    negative = any(k in note.lower() for k in ("still", "not yet", "partial", "pending"))
    return GeminiFollowup(
        comparison=(
            "The after photo appears to show the original condition still present."
            if negative
            else "The after photo suggests the original obstruction/condition is no longer visible in the same area."
        ),
        closure_supported=not negative,
        confidence="confirmed",
        reasoning="[Demo AI] Preset comparison -- not a real model call. The reviewer makes the closure decision.",
    )
