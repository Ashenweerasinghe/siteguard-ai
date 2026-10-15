"""Deterministic risk matrix. Not a Gemini call -- kept isolated and easy to defend."""

from .schema import RiskResult


def compute_risk(likelihood: int, severity: int, reviewer_override: str | None = None) -> RiskResult:
    """likelihood (1-3) x severity (1-3) = score. 1-3 Low, 4-6 Medium, 7-9 High."""
    if not 1 <= likelihood <= 3:
        raise ValueError(f"likelihood must be 1-3, got {likelihood}")
    if not 1 <= severity <= 3:
        raise ValueError(f"severity must be 1-3, got {severity}")

    score = likelihood * severity
    if score <= 3:
        level = "Low"
    elif score <= 6:
        level = "Medium"
    else:
        level = "High"

    return RiskResult(
        likelihood=likelihood,
        severity=severity,
        score=score,
        level=level,
        reviewer_override=reviewer_override,
    )
