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
    "unprotected_edge": "Unprotected Edge",
    "obstructed_walkway": "Obstructed Walkway",
    "ppe_concern": "PPE Concern",
    "none": "No Hazard Detected",
}

STATUS_LABELS = {
    "flagged": "Open",
    "reviewer_confirmed": "Open",
    "action_assigned": "Open",
    "pending_closure_review": "Pending Review",
    "closed": "Closed",
    "reopened": "Open",
}

STATUS_PILL_COLOR = {
    "flagged": "amber",
    "reviewer_confirmed": "amber",
    "action_assigned": "amber",
    "pending_closure_review": "blue",
    "closed": "green",
    "reopened": "amber",
}


class GeminiFinding(BaseModel):
    """Structured output requested from Gemini for an initial hazard analysis."""

    scenario: Scenario = Field(description="Which of the in-scope hazard scenarios this matches, or 'none'.")
    description: str = Field(description="Plain-language description of what the evidence shows.")
    confidence: Confidence = Field(description="'confirmed' if clearly visible/audible, 'uncertain' if angle, occlusion, or audio quality prevents a clear read.")
    suggested_likelihood: int = Field(ge=1, le=3, description="1-3 likelihood estimate for the deterministic risk matrix.")
    suggested_severity: int = Field(ge=1, le=3, description="1-3 severity estimate for the deterministic risk matrix.")
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
