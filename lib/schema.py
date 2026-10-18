"""Shared type definitions for SafeGuard AI (formerly SiteGuard AI)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

Scenario = Literal["unprotected_edge", "obstructed_walkway", "ppe_concern", "none"]
Confidence = Literal["confirmed", "uncertain"]
HazardStatus = Literal[
    "flagged",
    "reviewer_confirmed",
    "action_assigned",
    "pending_closure_review",
    "closed",
    "reopened",
]

SCENARIO_LABELS = {
    "unprotected_edge": "Unprotected Edge / Fall risk",
    "obstructed_walkway": "Access obstruction / Walkway",
    "ppe_concern": "PPE Concern",
    "none": "No Hazard Detected",
}

SCENARIO_ICONS = {
    "unprotected_edge": ":material/stairs:",
    "obstructed_walkway": ":material/block:",
    "ppe_concern": ":material/engineering:",
    "none": ":material/help:",
}

# Fine-grained status label (kept for backwards compatibility with older code).
STATUS_LABELS = {
    "flagged": "Draft",
    "reviewer_confirmed": "Open",
    "action_assigned": "In Progress",
    "pending_closure_review": "Pending Review",
    "closed": "Closed",
    "reopened": "Reopened",
}

STATUS_PILL_COLOR = {
    "flagged": "gray",
    "reviewer_confirmed": "amber",
    "action_assigned": "blue",
    "pending_closure_review": "violet",
    "closed": "green",
    "reopened": "amber",
}

# Register tabs (design screen 6): All / Open / In Progress / Closed.
STATUS_GROUP = {
    "flagged": "Open",
    "reviewer_confirmed": "Open",
    "reopened": "Open",
    "action_assigned": "In Progress",
    "pending_closure_review": "In Progress",
    "closed": "Closed",
}

RISK_COLOR = {"High": "red", "Medium": "amber", "Low": "green"}

PRIORITIES = ["High", "Medium", "Low"]

DEFAULT_TEAMS = [
    "Site Supervisor",
    "Safety Team",
    "Warehouse Operations",
    "Facilities",
    "Maintenance",
    "Housekeeping",
    "Electrical",
]

LIKELIHOOD_LABELS = {1: "1 - Unlikely", 2: "2 - Possible", 3: "3 - Likely"}
SEVERITY_LABELS = {1: "1 - Minor", 2: "2 - Serious", 3: "3 - Major"}


class GeminiFinding(BaseModel):
    """Structured output requested from Gemini for an initial hazard analysis."""

    scenario: Scenario = Field(description="Which of the in-scope hazard scenarios this matches, or 'none'.")
    title: str = Field(default="", description="Short observation title, max 8 words, e.g. 'Boxes blocking fire exit'.")
    description: str = Field(description="Plain-language description of what the evidence shows.")
    confidence: Confidence = Field(description="'confirmed' if clearly visible/audible, 'uncertain' if angle, occlusion, or audio quality prevents a clear read.")
    confidence_score: int = Field(default=0, ge=0, le=100, description="0-100 estimate of how clearly the evidence supports this finding.")
    suggested_likelihood: int = Field(ge=1, le=3, description="1-3 likelihood estimate for the deterministic risk matrix.")
    suggested_severity: int = Field(ge=1, le=3, description="1-3 severity estimate for the deterministic risk matrix.")
    potential_impact: str = Field(default="", description="One sentence on who or what could be harmed and how.")
    suggested_actions: list[str] = Field(default_factory=list, description="2-4 short, concrete corrective actions for the reviewer to choose from.")
    responsible_team: str = Field(default="", description="The team most likely responsible for the corrective action, e.g. 'Site Supervisor'.")
    additional_evidence: list[str] = Field(default_factory=list, description="0-3 short notes on extra evidence that would make the finding clearer.")
    reasoning: str = Field(description="One or two sentences on what specifically drove this finding, for reviewer context.")


class GeminiFollowup(BaseModel):
    """Structured output requested from Gemini for a follow-up closure comparison."""

    comparison: str = Field(description="What changed between the original and new evidence.")
    closure_supported: bool = Field(description="Whether the new evidence supports closing the hazard.")
    confidence: Confidence = Field(description="'confirmed' if the comparison is clear, 'uncertain' if inconclusive.")
    reasoning: str = Field(description="Why closure is or isn't supported, in reviewer-facing language.")


class RiskResult(BaseModel):
    likelihood: int
    severity: int
    score: int
    level: Literal["Low", "Medium", "High"]
    reviewer_override: Optional[str] = None
