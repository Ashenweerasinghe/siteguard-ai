"""SiteGuard AI -- Streamlit entry point. 3-view router: Capture, Hazard Register, Follow-up.

Non-negotiable across every screen: the AI proposes, a human approves every state
change. Nothing in this file writes "safe", "compliant", or "fixed" to the UI.
"""

from __future__ import annotations

import datetime as dt
import os

import requests
import streamlit as st
from dotenv import load_dotenv

from lib import firestore as fs
from lib import gemini
from lib.risk import compute_risk
from lib.schema import SCENARIO_LABELS, STATUS_LABELS, STATUS_PILL_COLOR

load_dotenv()

st.set_page_config(page_title="SiteGuard AI", page_icon=":material/engineering:", layout="wide")

_PILL_HEX = {"amber": "#B45309", "blue": "#1D4ED8", "green": "#15803D"}
_PILL_BG = {"amber": "#FEF3C7", "blue": "#DBEAFE", "green": "#DCFCE7"}

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .sg-pill {
        display: inline-block; padding: 2px 10px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600; margin-bottom: 4px;
    }
    .sg-summary { color: #57534E; font-size: 0.9rem; margin: 2px 0 0 0; }
    .sg-confidence-uncertain {
        background: #FEE2E2; color: #B91C1C; padding: 2px 10px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600; display: inline-block;
    }
    .sg-confidence-confirmed {
        background: #DCFCE7; color: #15803D; padding: 2px 10px; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600; display: inline-block;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def status_pill(status: str) -> str:
    color = STATUS_PILL_COLOR.get(status, "amber")
    label = STATUS_LABELS.get(status, status)
    return (
        f'<span class="sg-pill" style="background:{_PILL_BG[color]};color:{_PILL_HEX[color]}">'
        f"{label}</span>"
    )


def confidence_badge(confidence: str) -> str:
    cls = "sg-confidence-confirmed" if confidence == "confirmed" else "sg-confidence-uncertain"
    label = "Confirmed" if confidence == "confirmed" else "Inconclusive"
    return f'<span class="{cls}">{label}</span>'


if "reviewer" not in st.session_state:
    st.session_state["reviewer"] = "Demo Reviewer"
if "selected_hazard_id" not in st.session_state:
    st.session_state["selected_hazard_id"] = None
if "pending_finding" not in st.session_state:
    st.session_state["pending_finding"] = None
if "followup_pending_id" not in st.session_state:
    st.session_state["followup_pending_id"] = None

with st.sidebar:
    st.title(":material/engineering: SiteGuard AI")
    st.caption("AI-assisted hazard evidence review")
    view = st.radio("View", ["Capture", "Hazard Register", "Follow-up"], label_visibility="collapsed")
    st.divider()
    st.session_state["reviewer"] = st.text_input("Reviewer name", value=st.session_state["reviewer"])
    st.caption("The AI proposes. You approve every state change.")


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------
def render_capture() -> None:
    st.header("Capture")
    st.caption("Upload a photo and voice note, then let Gemini flag potential hazards for your review.")

    col1, col2 = st.columns(2)
    with col1:
        photo = st.file_uploader("Site photo", type=["jpg", "jpeg", "png"], key="capture_photo")
        if photo:
            st.image(photo, use_container_width=True)
    with col2:
        audio_tab, upload_tab = st.tabs(["Record voice note", "Upload voice note"])
        audio_bytes = None
        audio_mime = None
        with audio_tab:
            recorded = st.audio_input("Record a short note", key="capture_audio_record")
            if recorded:
                audio_bytes = recorded.getvalue()
                audio_mime = "audio/wav"
        with upload_tab:
            uploaded_audio = st.file_uploader("Or upload an audio file", type=["wav", "mp3", "m4a"], key="capture_audio_upload")
            if uploaded_audio:
                audio_bytes = uploaded_audio.getvalue()
                audio_mime = uploaded_audio.type or "audio/wav"
        if audio_bytes:
            st.audio(audio_bytes)

    site_col, date_col, activity_col = st.columns(3)
    with site_col:
        site = st.text_input("Site", placeholder="e.g. Block C, Level 4")
    with date_col:
        date = st.date_input("Date", value=dt.date.today()).isoformat()
    with activity_col:
        activity = st.text_input("Activity", placeholder="e.g. Formwork stripping")

    analyze_disabled = not (photo and site and activity)
    if st.button("Analyze", type="primary", disabled=analyze_disabled):
        with st.spinner("Gemini is examining the evidence..."):
            photo_bytes = photo.getvalue()
            try:
                finding = gemini.analyze_hazard(
                    image_bytes=photo_bytes,
                    image_mime_type=photo.type or "image/jpeg",
                    site=site,
                    date=date,
                    activity=activity,
                    audio_bytes=audio_bytes,
                    audio_mime_type=audio_mime,
                )
            except gemini.genai_errors.ClientError as exc:
                if "RESOURCE_EXHAUSTED" in str(exc):
                    st.error("Free-tier rate limit reached. Wait about a minute, then try Analyze again.")
                else:
                    st.error("Gemini rejected this request. Please try again.")
                st.stop()
            except gemini.genai_errors.ServerError:
                st.error("Gemini is under heavy demand right now. Please try Analyze again in a moment.")
                st.stop()
        st.session_state["pending_finding"] = {
            "finding": finding,
            "photo_bytes": photo_bytes,
            "photo_mime": photo.type or "image/jpeg",
            "photo_name": photo.name,
            "audio_bytes": audio_bytes,
            "audio_mime": audio_mime,
            "site": site,
            "date": date,
            "activity": activity,
        }

    pending = st.session_state["pending_finding"]
    if pending:
        finding = pending["finding"]
        st.divider()
        with st.container(border=True):
            st.subheader(SCENARIO_LABELS.get(finding.scenario, finding.scenario))
            st.markdown(confidence_badge(finding.confidence), unsafe_allow_html=True)
            st.write(finding.description)
            st.caption(f"Model reasoning: {finding.reasoning}")
            risk = compute_risk(finding.suggested_likelihood, finding.suggested_severity)
            st.write(f"**Suggested risk:** {risk.level} (likelihood {risk.likelihood} x severity {risk.severity} = {risk.score})")
            if finding.confidence == "uncertain":
                st.warning("Evidence is inconclusive -- angle, occlusion, or audio quality prevented a clear read.")

            edit_mode = st.session_state.get("capture_edit_mode", False)

            if not edit_mode:
                c1, c2, c3 = st.columns(3)
                if c1.button("Confirm", type="primary", use_container_width=True):
                    _save_finding(pending, finding.description, risk.likelihood, risk.severity, confirm=True)
                if c2.button("Reject", use_container_width=True):
                    _save_finding(pending, finding.description, risk.likelihood, risk.severity, confirm=False)
                if c3.button("Edit", use_container_width=True):
                    st.session_state["capture_edit_mode"] = True
                    st.rerun()
            else:
                new_desc = st.text_area("Edit description", value=finding.description)
                l_col, s_col = st.columns(2)
                new_likelihood = l_col.slider("Likelihood", 1, 3, risk.likelihood)
                new_severity = s_col.slider("Severity", 1, 3, risk.severity)
                if st.button("Save & Confirm", type="primary"):
                    _save_finding(pending, new_desc, new_likelihood, new_severity, confirm=True, edited=True)
                    st.session_state["capture_edit_mode"] = False


def _save_finding(pending: dict, description: str, likelihood: int, severity: int, confirm: bool, edited: bool = False) -> None:
    reviewer = st.session_state["reviewer"]
    with st.spinner("Saving evidence..."):
        photo_url = fs.upload_evidence(pending["photo_bytes"], pending["photo_name"], pending["photo_mime"])
        audio_url = None
        if pending["audio_bytes"]:
            audio_url = fs.upload_evidence(pending["audio_bytes"], "voice-note.wav", pending["audio_mime"] or "audio/wav")

        finding = pending["finding"]
        risk = compute_risk(likelihood, severity)
        hazard_id = fs.create_hazard(
            scenario=finding.scenario,
            site=pending["site"],
            date=pending["date"],
            activity=pending["activity"],
            source_photo_url=photo_url,
            source_audio_url=audio_url,
            ai_finding={
                "description": description,
                "confidence": finding.confidence,
                "raw_model_output": finding.model_dump(),
            },
            risk=risk.model_dump(),
            actor=reviewer,
        )
        if edited:
            fs.edit_finding(hazard_id, reviewer, description, risk.model_dump())
        elif confirm:
            fs.confirm_hazard(hazard_id, reviewer)
        else:
            fs.reject_hazard(hazard_id, reviewer)

    st.session_state["pending_finding"] = None
    st.session_state["capture_edit_mode"] = False
    if confirm:
        st.success(f"Hazard confirmed and saved (ID: {hazard_id}).")
    else:
        st.info(f"Finding rejected and logged for audit (ID: {hazard_id}).")
    st.rerun()


# ---------------------------------------------------------------------------
# Hazard Register
# ---------------------------------------------------------------------------
def render_register() -> None:
    st.header("Hazard Register")

    if st.session_state["selected_hazard_id"]:
        _render_hazard_detail(st.session_state["selected_hazard_id"])
        return

    f1, f2 = st.columns(2)
    status_filter = f1.selectbox("Filter by status", ["All", "Open", "Pending Review", "Closed"])
    scenario_filter = f2.selectbox("Filter by scenario", ["All"] + list(SCENARIO_LABELS.keys()), format_func=lambda s: SCENARIO_LABELS.get(s, s))

    hazards = fs.list_hazards(scenario=None if scenario_filter == "All" else scenario_filter)
    if status_filter != "All":
        hazards = [h for h in hazards if STATUS_LABELS.get(h["status"]) == status_filter]

    if not hazards:
        st.info("No hazards match these filters yet.")
        return

    cols = st.columns(3)
    for i, hazard in enumerate(hazards):
        with cols[i % 3]:
            with st.container(border=True):
                if hazard.get("source_photo_url"):
                    st.image(hazard["source_photo_url"], use_container_width=True)
                st.markdown(status_pill(hazard["status"]), unsafe_allow_html=True)
                st.markdown(f"**{SCENARIO_LABELS.get(hazard['scenario'], hazard['scenario'])}**")
                st.markdown(f'<p class="sg-summary">{hazard["site"]} &middot; {hazard["date"]}</p>', unsafe_allow_html=True)
                if st.button("View", key=f"view_{hazard['id']}", use_container_width=True):
                    st.session_state["selected_hazard_id"] = hazard["id"]
                    st.rerun()


def _render_hazard_detail(hazard_id: str) -> None:
    hazard = fs.get_hazard(hazard_id)
    if not hazard:
        st.error("Hazard not found.")
        st.session_state["selected_hazard_id"] = None
        return

    if st.button(":material/arrow_back: Back to register"):
        st.session_state["selected_hazard_id"] = None
        st.rerun()

    st.markdown(status_pill(hazard["status"]), unsafe_allow_html=True)
    st.subheader(SCENARIO_LABELS.get(hazard["scenario"], hazard["scenario"]))
    st.caption(f"{hazard['site']} · {hazard['date']} · {hazard['activity']}")

    img_col, info_col = st.columns([1, 1])
    with img_col:
        if hazard.get("source_photo_url"):
            st.image(hazard["source_photo_url"], use_container_width=True)
        if hazard.get("source_audio_url"):
            st.audio(hazard["source_audio_url"])
    with info_col:
        finding = hazard.get("ai_finding", {})
        st.markdown(confidence_badge(finding.get("confidence", "uncertain")), unsafe_allow_html=True)
        st.write(finding.get("description", ""))
        risk = hazard.get("risk", {})
        st.write(f"**Risk:** {risk.get('level', 'n/a')} (likelihood {risk.get('likelihood')} x severity {risk.get('severity')} = {risk.get('score')})")

        if hazard["status"] == "reviewer_confirmed":
            st.markdown("##### Assign corrective action")
            with st.form("assign_action_form"):
                desc = st.text_area("Action description")
                owner = st.text_input("Owner")
                due = st.date_input("Due date", value=dt.date.today() + dt.timedelta(days=7)).isoformat()
                escalation = st.text_input("Escalation rule", placeholder="e.g. Escalate to site manager if overdue 48h")
                if st.form_submit_button("Assign", type="primary"):
                    fs.assign_action(hazard_id, st.session_state["reviewer"], desc, owner, due, escalation)
                    st.rerun()
        elif hazard.get("action"):
            action = hazard["action"]
            st.markdown("##### Corrective action")
            st.write(f"**Owner:** {action['owner']}")
            st.write(f"**Due:** {action['due_date']}")
            st.write(f"**Description:** {action['description']}")
            if action.get("escalation_rule"):
                st.caption(f"Escalation: {action['escalation_rule']}")

    st.divider()
    st.markdown("##### History")
    for entry in reversed(hazard.get("history", [])):
        st.markdown(f"- `{entry['timestamp']}` **{entry['actor']}** -- {entry['event']}: {entry['note']}")


# ---------------------------------------------------------------------------
# Follow-up
# ---------------------------------------------------------------------------
def render_followup() -> None:
    st.header("Follow-up")

    pending_id = st.session_state.get("followup_pending_id")
    if pending_id:
        _render_followup_decision(pending_id)
        return

    st.caption("Pick an open hazard, upload new evidence, and review the AI's closure recommendation.")

    open_statuses = {"reviewer_confirmed", "action_assigned", "reopened"}
    open_hazards = [h for h in fs.list_hazards() if h["status"] in open_statuses]

    if not open_hazards:
        st.info("No open hazards to follow up on yet.")
        return

    options = {f"{SCENARIO_LABELS.get(h['scenario'], h['scenario'])} -- {h['site']} ({h['date']})": h["id"] for h in open_hazards}
    choice = st.selectbox("Open hazard", list(options.keys()))
    hazard_id = options[choice]
    hazard = fs.get_hazard(hazard_id)

    before_col, after_col = st.columns(2)
    with before_col:
        st.markdown("**Before**")
        if hazard.get("source_photo_url"):
            st.image(hazard["source_photo_url"], use_container_width=True)
    with after_col:
        st.markdown("**After**")
        new_photo = st.file_uploader("Upload new evidence", type=["jpg", "jpeg", "png"], key="followup_photo")
        if new_photo:
            st.image(new_photo, use_container_width=True)

    if new_photo and st.button("Analyze Follow-up", type="primary"):
        with st.spinner("Gemini is comparing before/after evidence..."):
            original_bytes = requests.get(hazard["source_photo_url"], timeout=30).content
            new_bytes = new_photo.getvalue()
            try:
                comparison = gemini.analyze_followup(
                    original_image_bytes=original_bytes,
                    original_image_mime_type="image/jpeg",
                    new_image_bytes=new_bytes,
                    new_image_mime_type=new_photo.type or "image/jpeg",
                    original_finding_description=hazard["ai_finding"]["description"],
                    original_scenario=hazard["scenario"],
                )
            except gemini.genai_errors.ClientError as exc:
                if "RESOURCE_EXHAUSTED" in str(exc):
                    st.error("Free-tier rate limit reached. Wait about a minute, then try Analyze Follow-up again.")
                else:
                    st.error("Gemini rejected this request. Please try again.")
                st.stop()
            except gemini.genai_errors.ServerError:
                st.error("Gemini is under heavy demand right now. Please try Analyze Follow-up again in a moment.")
                st.stop()
        photo_url = fs.upload_evidence(new_bytes, new_photo.name, new_photo.type or "image/jpeg")
        fs.add_followup(hazard_id, st.session_state["reviewer"], photo_url, comparison.model_dump())
        st.session_state["followup_pending_id"] = hazard_id
        st.rerun()


def _render_followup_decision(hazard_id: str) -> None:
    hazard = fs.get_hazard(hazard_id)
    if st.button(":material/arrow_back: Back to open hazards"):
        st.session_state["followup_pending_id"] = None
        st.rerun()

    st.subheader(SCENARIO_LABELS.get(hazard["scenario"], hazard["scenario"]))
    before_col, after_col = st.columns(2)
    followups = hazard.get("followups", [])
    latest = followups[-1]
    with before_col:
        st.markdown("**Before**")
        st.image(hazard["source_photo_url"], use_container_width=True)
    with after_col:
        st.markdown("**After**")
        st.image(latest["photo_url"], use_container_width=True)

    comparison = latest["ai_comparison"]
    st.divider()
    with st.container(border=True):
        st.markdown(confidence_badge(comparison["confidence"]), unsafe_allow_html=True)
        st.write(comparison["comparison"])
        st.caption(comparison["reasoning"])
        if comparison["closure_supported"]:
            st.success("Evidence suggests the hazard has been remediated.")
        else:
            st.warning("Evidence does not support closure yet.")

        c1, c2 = st.columns(2)
        if c1.button("Approve closure", type="primary", use_container_width=True):
            fs.resolve_closure(hazard_id, st.session_state["reviewer"], approve=True)
            st.session_state["followup_pending_id"] = None
            st.success("Hazard closed.")
            st.rerun()
        if c2.button("Reject -- stays open", use_container_width=True):
            fs.resolve_closure(hazard_id, st.session_state["reviewer"], approve=False)
            st.session_state["followup_pending_id"] = None
            st.info("Hazard remains open.")
            st.rerun()


if view == "Capture":
    render_capture()
elif view == "Hazard Register":
    render_register()
else:
    render_followup()
