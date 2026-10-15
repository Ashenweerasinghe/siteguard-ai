"""Gemini calls for hazard analysis and follow-up closure comparison.

Non-negotiable: the model proposes, it never gets to assert "safe", "compliant",
or "fixed" -- the prompts below force "evidence suggests" / "appears present" /
"inconclusive" framing, and every response carries an explicit confidence flag
that the UI must surface, never drop.
"""

from __future__ import annotations

import os
import time

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from .schema import GeminiFinding, GeminiFollowup

MODEL_NAME = "gemini-3.5-flash"
_MAX_RETRIES = 4
_RETRY_DELAYS_SECONDS = (2, 5, 10)


def _generate_with_retry(client: genai.Client, **kwargs):
    """The model is under heavy public demand right now and returns transient
    503s; retry with backoff before surfacing anything to the reviewer."""
    last_error = None
    for attempt in range(_MAX_RETRIES):
        try:
            return client.models.generate_content(**kwargs)
        except genai_errors.ServerError as exc:
            last_error = exc
            if attempt < len(_RETRY_DELAYS_SECONDS):
                time.sleep(_RETRY_DELAYS_SECONDS[attempt])
    raise last_error

_SYSTEM_INSTRUCTION = """You are a construction-site safety evidence analyst. You NEVER say \
"safe", "compliant", "fixed", or give a certification verdict -- you only describe what the \
evidence shows, using language like "evidence suggests", "appears present", or "inconclusive". \
You are evaluating evidence for a human reviewer who makes the actual safety determination. \
If the photo angle, occlusion, lighting, or audio quality prevents a clear read, you MUST set \
confidence to "uncertain" rather than guessing -- never silently pick a side when the evidence \
does not support it."""

_SCENARIOS = """Three hazard scenarios are in scope:
(A) unprotected_edge -- a fall edge, floor opening, or drop-off without guardrail, barrier, or cover.
(B) obstructed_walkway -- a designated walkway or egress path blocked by materials, debris, or equipment.
(C) ppe_concern -- a worker visibly missing required PPE (hard hat, high-vis, harness at height, etc.) for the activity shown.
If none of these are present, use scenario "none"."""


def _client() -> genai.Client:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")
    return genai.Client(api_key=api_key)


def analyze_hazard(
    image_bytes: bytes,
    image_mime_type: str,
    site: str,
    date: str,
    activity: str,
    audio_bytes: bytes | None = None,
    audio_mime_type: str | None = None,
    voice_note_transcript_hint: str | None = None,
) -> GeminiFinding:
    """Single multimodal call: photo (+ optional voice note) in, structured finding out."""
    client = _client()

    prompt = f"""{_SCENARIOS}

Site: {site}
Date: {date}
Activity: {activity}

Examine the attached photo{" and voice note" if audio_bytes else ""} for evidence of any of the \
three in-scope hazard scenarios. Report your finding as structured data. Provide a suggested \
likelihood (1-3: how likely this leads to an incident) and severity (1-3: how bad the outcome \
would be) for a deterministic risk matrix a reviewer will apply -- these are your estimates, \
not a final risk rating."""

    parts: list = [types.Part.from_bytes(data=image_bytes, mime_type=image_mime_type)]
    if audio_bytes:
        parts.append(types.Part.from_bytes(data=audio_bytes, mime_type=audio_mime_type or "audio/wav"))
    parts.append(prompt)

    response = _generate_with_retry(
        client,
        model=MODEL_NAME,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=GeminiFinding,
        ),
    )
    return response.parsed


def analyze_followup(
    original_image_bytes: bytes,
    original_image_mime_type: str,
    new_image_bytes: bytes,
    new_image_mime_type: str,
    original_finding_description: str,
    original_scenario: str,
) -> GeminiFollowup:
    """Compare original + new evidence for one hazard and judge whether closure is supported."""
    client = _client()

    prompt = f"""This is a follow-up inspection for a previously flagged hazard.

Original scenario: {original_scenario}
Original finding: {original_finding_description}

The first image is the ORIGINAL evidence. The second image is NEW evidence from a later visit. \
Compare them specifically for whether the original hazard condition has been remediated. Do not \
perform a generic re-analysis -- answer specifically whether the new evidence supports closing \
this particular hazard, remains inconclusive, or shows the hazard is still present."""

    parts = [
        types.Part.from_bytes(data=original_image_bytes, mime_type=original_image_mime_type),
        types.Part.from_bytes(data=new_image_bytes, mime_type=new_image_mime_type),
        prompt,
    ]

    response = _generate_with_retry(
        client,
        model=MODEL_NAME,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=GeminiFollowup,
        ),
    )
    return response.parsed
