"""Shared type definitions for SiteGuard AI."""

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


class InsightPattern(BaseModel):
    """One recurring pattern Gemini reads out of the register."""

    pattern: str = Field(description="The recurring pattern in one short phrase, e.g. 'Walkway obstructions cluster at Loading Dock B'.")
    evidence: str = Field(description="Which counts in the supplied digest support this, quoted back concretely.")
    why_it_matters: str = Field(description="One sentence on the operational consequence if it continues.")


class InsightFocus(BaseModel):
    """A recommended focus area. A recommendation, never an instruction the app acts on."""

    area: str = Field(description="The location, team, or hazard category to focus on.")
    recommendation: str = Field(description="One concrete, operational step a site lead could take this week.")
    rationale: str = Field(description="Why this one, grounded in the digest.")
    suggested_owner: str = Field(default="", description="The team best placed to own it, from the teams present in the digest.")


class SiteInsights(BaseModel):
    """Register-wide operational summary. Gemini interprets; every number in the
    digest it reasons over was computed deterministically in Python first."""

    headline: str = Field(description="One sentence on the state of the register right now, in plain operational language.")
    recurring_patterns: list[InsightPattern] = Field(default_factory=list, description="2-4 patterns that repeat across records.")
    focus_areas: list[InsightFocus] = Field(default_factory=list, description="2-4 recommended focus areas, most important first.")
    accountability: list[str] = Field(default_factory=list, description="0-4 short notes on teams or locations where corrective work is slipping.")
    blind_spots: list[str] = Field(default_factory=list, description="1-3 things this register cannot tell you, so the reader does not over-read it.")
    confidence: Confidence = Field(description="'confirmed' if the register holds enough records to support these reads, 'uncertain' if the sample is too small or too skewed.")
    confidence_note: str = Field(default="", description="One sentence on what limits confidence, especially when 'uncertain'.")


class RiskResult(BaseModel):
    likelihood: int
    severity: int
    score: int
    level: Literal["Low", "Medium", "High"]
    reviewer_override: Optional[str] = None
