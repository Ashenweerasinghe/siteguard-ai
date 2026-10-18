"""Screens 3-5 - New Observation: Capture -> AI Analysis -> Review & Confirm -> Assign Action.

All draft state lives in st.session_state["obs"] (not in widgets) so moving back and
forth between steps never loses the photo, voice note or typed values. Nothing is
written to the register until the reviewer clicks "Save as Draft", "Not a hazard"
or "Confirm & Create Record" -- the AI only proposes.
"""

from __future__ import annotations

import datetime as dt
import uuid

import streamlit as st

from lib import auth, gemini, nav, store, ui
from lib.risk import compute_risk
from lib.schema import (
    DEFAULT_TEAMS,
    LIKELIHOOD_LABELS,
    PRIORITIES,
    SCENARIO_LABELS,
    SEVERITY_LABELS,
    GeminiFinding,
)
from views.components import header_actions

STEPS = ["Capture", "AI Analysis", "Review & Confirm", "Assign Action"]
DUE_DAYS = {"High": 1, "Medium": 3, "Low": 7}
PRIORITY_COLOR = {"High": "red", "Medium": "amber", "Low": "green"}
ESCALATION = {
    "High": "Escalate to site manager if not completed within 24h",
    "Medium": "Escalate to site manager if overdue 48h",
    "Low": "Review at weekly safety meeting if overdue",
}


def _new_obs() -> dict:
    now = ui.now_local()
    return {"step": 1, "nonce": uuid.uuid4().hex[:6], "date": now.date(),
            "time": now.time().replace(second=0, microsecond=0)}


def _obs() -> dict:
    if not st.session_state.get("obs"):
        st.session_state["obs"] = _new_obs()
    return st.session_state["obs"]


def _reset(page: str | None = None) -> None:
    st.session_state["obs"] = None
    if page:
        st.session_state["page"] = page


def render() -> None:
    obs = _obs()
    ui.page_header("New Observation", "See it, report it, and let SafeGuard AI help you assess it.",
                   actions=header_actions(False))
    badges = ui.demo_badges()
    if badges:
        st.markdown(badges, unsafe_allow_html=True)
    ui.stepper(STEPS, obs["step"])
    {1: _step_capture, 2: _step_analysis, 3: _step_review, 4: _step_done}[obs["step"]](obs)


def _card_title(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="sg-h3" style="font-size:1.3rem">{title}</div>'
                f'<p class="sg-muted" style="margin:.2rem 0 .3rem">{subtitle}</p>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Step 1 - Capture
# ---------------------------------------------------------------------------
def _step_capture(obs: dict) -> None:
    n = obs["nonce"]
    go = False
    with st.container(key="card_capture"):
        t, x = st.columns([8, 1], vertical_alignment="center")
        with t:
            _card_title("Capture a Hazard", "Take a photo, add a short note, and let AI analyse it.")
        with x, st.container(horizontal=True, horizontal_alignment="right"):
            st.button("", icon=":material/close:", key="cap_close", help="Cancel", type="tertiary",
                      on_click=_reset, args=("home",))
        ui.required_legend()

        left, right = st.columns([1.1, 1], gap="large")
        with left:
            # ---- Photo (mandatory) ----
            if obs.get("photo_bytes"):
                st.markdown(f'<div class="sg-flabel">{ui.req_html("Site photo")}</div>', unsafe_allow_html=True)
                st.markdown(ui.thumb(None, w="100%", h=300, radius=14,
                                     src=ui.bytes_uri(obs["photo_bytes"], obs["photo_mime"])), unsafe_allow_html=True)
                c1, c2 = st.columns([3, 1.4], vertical_alignment="center")
                c1.caption(obs.get("photo_name", "photo"))
                if c2.button("Change photo", icon=":material/photo_camera:", key="cap_change", width="stretch"):
                    for k in ("photo_bytes", "photo_mime", "photo_name"):
                        obs.pop(k, None)
                    obs["nonce"] = uuid.uuid4().hex[:6]
                    st.rerun()
            else:
                up_tab, cam_tab = st.tabs([":material/upload: Upload photo", ":material/photo_camera: Take photo"])
                with up_tab:
                    photo = st.file_uploader(ui.req("Site photo"), type=["jpg", "jpeg", "png"], key=f"cap_photo_{n}")
                with cam_tab:
                    shot = st.camera_input(ui.req("Site photo"), key=f"cap_cam_{n}")
                picked = photo or shot
                if picked:
                    obs.update(photo_bytes=picked.getvalue(), photo_mime=picked.type or "image/jpeg",
                               photo_name=getattr(picked, "name", "") or "camera.jpg")
                    st.rerun()

            # ---- Voice note (optional) ----
            st.markdown('<div style="height:.5rem"></div>', unsafe_allow_html=True)
            if obs.get("audio_bytes"):
                st.markdown('<div class="sg-flabel">Voice note</div>', unsafe_allow_html=True)
                a1, a2 = st.columns([5, 1], vertical_alignment="center")
                a1.audio(obs["audio_bytes"])
                if a2.button("", icon=":material/delete:", key="cap_audio_del", help="Remove voice note"):
                    obs.pop("audio_bytes", None)
                    obs.pop("audio_mime", None)
                    obs["nonce"] = uuid.uuid4().hex[:6]
                    st.rerun()
            else:
                rec_tab, upa_tab = st.tabs([":material/mic: Record a voice note", ":material/audio_file: Upload audio"])
                with rec_tab:
                    rec = st.audio_input("Voice note (optional)", key=f"cap_rec_{n}")
                with upa_tab:
                    upa = st.file_uploader("Voice note (optional)", type=["wav", "mp3", "m4a"], key=f"cap_upa_{n}")
                if rec:
                    obs.update(audio_bytes=rec.getvalue(), audio_mime="audio/wav")
                    st.rerun()
                if upa:
                    obs.update(audio_bytes=upa.getvalue(), audio_mime=upa.type or "audio/wav")
                    st.rerun()

        with right:
            obs["note"] = st.text_area("Or type a note", value=obs.get("note", ""), max_chars=500, height=122,
                                       placeholder="e.g. Boxes found in front of the fire extinguisher near loading dock B.",
                                       key=f"cap_note_{n}")
            obs["location"] = st.text_input(ui.req("Location"), value=obs.get("location", ""), max_chars=120,
                                            placeholder="e.g. Loading Dock B / Block C, Level 4",
                                            icon=":material/location_on:", key=f"cap_loc_{n}")
            d, tm = st.columns(2)
            obs["date"] = d.date_input(ui.req("Date"), value=obs["date"], max_value=ui.now_local().date(),
                                       format="YYYY/MM/DD", key=f"cap_date_{n}")
            obs["time"] = tm.time_input(ui.req("Time"), value=obs["time"], step=300, key=f"cap_time_{n}")
            obs["activity"] = st.text_input("Activity (optional)", value=obs.get("activity", ""), max_chars=120,
                                            placeholder="e.g. Material delivery", key=f"cap_act_{n}")
            st.markdown('<div style="height:.3rem"></div>', unsafe_allow_html=True)
            go = st.button("Analyze with AI", icon=":material/arrow_forward:", icon_position="right",
                           type="primary", width="stretch", key="cap_analyze")

    if go:
        missing = [label for label, ok in (
            ("Site photo", obs.get("photo_bytes")),
            ("Location", (obs.get("location") or "").strip()),
            ("Date", obs.get("date")),
            ("Time", obs.get("time")),
        ) if not ok]
        if missing:
            st.error("Please complete the required field(s): " + ", ".join(missing), icon=":material/error:")
            return
        _run_analysis(obs)

    if obs.get("ai_error"):
        st.error(obs["ai_error"], icon=":material/cloud_off:")
        st.caption("Try again, or continue and assess the hazard manually -- every record is reviewer-confirmed anyway.")
        if st.button("Continue with manual review", icon=":material/edit_note:", key="cap_manual"):
            obs["finding"] = GeminiFinding(
                scenario="none", title="", description="", confidence="uncertain", confidence_score=0,
                suggested_likelihood=2, suggested_severity=2,
                reasoning="No AI analysis -- assessed manually by the reviewer.",
            ).model_dump()
            obs["manual"] = True
            obs.pop("ai_error", None)
            obs.pop("review", None)
            obs["step"] = 3
            st.rerun()


def _run_analysis(obs: dict) -> None:
    obs.pop("ai_error", None)
    with st.spinner("SafeGuard AI is examining the evidence..."):
        try:
            finding = gemini.analyze_hazard(
                image_bytes=obs["photo_bytes"],
                image_mime_type=obs["photo_mime"],
                site=obs["location"].strip(),
                date=obs["date"].isoformat(),
                activity=(obs.get("activity") or "").strip(),
                audio_bytes=obs.get("audio_bytes"),
                audio_mime_type=obs.get("audio_mime"),
                reviewer_note=(obs.get("note") or "").strip() or None,
                image_name=obs.get("photo_name", ""),
            )
            if finding is None:
                raise ValueError("the model returned an empty response")
        except gemini.genai_errors.ClientError as exc:
            obs["ai_error"] = ("Free-tier rate limit reached. Wait about a minute, then try again."
                               if "RESOURCE_EXHAUSTED" in str(exc) else "Gemini rejected this request. Please try again.")
        except gemini.genai_errors.ServerError:
            obs["ai_error"] = "Gemini is under heavy demand right now. Please try again in a moment."
        except Exception as exc:  # missing key, network, parse errors
            obs["ai_error"] = f"AI analysis is unavailable ({type(exc).__name__}: {exc})."
        else:
            obs["finding"] = finding.model_dump()
            obs["manual"] = False
            obs.pop("review", None)
            obs["step"] = 2
    st.rerun()


# ---------------------------------------------------------------------------
# Step 2 - AI Analysis Result
# ---------------------------------------------------------------------------
def _step_analysis(obs: dict) -> None:
    f = obs["finding"]
    risk = compute_risk(f["suggested_likelihood"], f["suggested_severity"])
    score = f.get("confidence_score") or (85 if f["confidence"] == "confirmed" else 50)
    title = f.get("title") or SCENARIO_LABELS.get(f["scenario"], "Observation")
    when = dt.datetime.combine(obs["date"], obs["time"]).strftime("%d %b %Y, %I:%M %p")

    left, right = st.columns([1, 1.55], gap="large")
    with left, st.container(key="card_ai_photo"):
        st.markdown(ui.thumb(None, w="100%", h=230, radius=12, src=ui.bytes_uri(obs["photo_bytes"], obs["photo_mime"])),
                    unsafe_allow_html=True)
        low = " sg-conf-low" if f["confidence"] != "confirmed" else ""
        conf_pill = ui.pill("Confirmed", "green") if f["confidence"] == "confirmed" else ui.pill("Inconclusive", "amber")
        st.markdown(
            f'<div class="sg-row-title" style="white-space:normal;margin-top:.8rem;font-size:1.05rem">{ui.esc(title)}</div>'
            f'<div class="sg-row-meta" style="margin-top:.35rem"><span><span class="material-symbols-rounded">location_on</span>{ui.esc(obs["location"])}</span></div>'
            f'<div class="sg-row-meta"><span><span class="material-symbols-rounded">calendar_today</span>{when}</span></div>'
            f'<div class="sg-conf"><div style="display:flex;justify-content:space-between;align-items:center" class="sg-small">'
            f'<span>Confidence &nbsp;{conf_pill}</span><strong style="color:var(--sg-text)">{score}%</strong></div>'
            f'<div class="sg-conf-bar{low}"><div style="width:{score}%"></div></div></div>',
            unsafe_allow_html=True,
        )
        if obs.get("audio_bytes"):
            st.audio(obs["audio_bytes"])

    with right, st.container(key="card_ai_findings"):
        _card_title("AI Analysis Result", "Here is what SafeGuard AI found from your photo and note.")
        st.markdown('<div class="sg-findings-h"><span class="material-symbols-rounded">check_circle</span>AI Findings</div>',
                    unsafe_allow_html=True)

        def ul(items: list[str]) -> str:
            return "<ul>" + "".join(f"<li>{ui.esc(i)}</li>" for i in items) + "</ul>" if items else "-"

        rows = [
            ("Visible observation", ui.esc(f["description"])),
            ("Hazard category", ui.pill(SCENARIO_LABELS.get(f["scenario"], f["scenario"]), "amber")),
            ("Risk level (indicative)", f'{ui.risk_pill(risk.level)} <span class="sg-small">&nbsp;likelihood {risk.likelihood} x severity {risk.severity} = {risk.score}</span>'),
            ("Potential impact", ui.esc(f.get("potential_impact") or "-")),
            ("Suggested immediate action", ui.esc((f.get("suggested_actions") or ["-"])[0])),
            ("Suggested responsible team", ui.esc(f.get("responsible_team") or "-")),
            ("Additional evidence needed", ul(f.get("additional_evidence") or [])),
        ]
        st.markdown(ui.kv_rows(rows), unsafe_allow_html=True)
        st.caption(f"Model reasoning: {f.get('reasoning', '')}")
        if f["confidence"] != "confirmed":
            st.markdown(ui.callout("Evidence is inconclusive",
                                   "Angle, occlusion, lighting or audio quality prevented a clear read. Consider capturing again.",
                                   "warn", "warning"), unsafe_allow_html=True)
        if f["scenario"] == "none":
            st.markdown(ui.callout("No in-scope hazard detected",
                                   "The AI did not match this photo to a known hazard type. You can still record it after review, or reject it.",
                                   "warn", "help"), unsafe_allow_html=True)
        st.markdown(ui.callout("Important",
                               "This is an AI-generated observation to support your assessment. Please review and confirm before taking action.",
                               "info", "info"), unsafe_allow_html=True)

        b1, b2, b3 = st.columns([1, 1, 1.3])
        if b1.button("Capture Again", icon=":material/arrow_back:", width="stretch", key="ai_back"):
            obs["step"] = 1
            st.rerun()
        with b2.popover("Not a hazard", icon=":material/do_not_disturb_on:", width="stretch"):
            st.caption("The finding and photo are kept for audit, then closed as rejected.")
            reason = st.text_input("Reason (optional)", key="ai_reject_reason", max_chars=200)
            if st.button("Reject finding", type="primary", key="ai_reject", width="stretch"):
                _save(obs, mode="reject", reject_reason=reason)
        if b3.button("Proceed to Review", icon=":material/arrow_forward:", icon_position="right",
                     type="primary", width="stretch", key="ai_next"):
            obs["step"] = 3
            st.rerun()


# ---------------------------------------------------------------------------
# Step 3 - Review & Confirm (+ assignment)
# ---------------------------------------------------------------------------
def _review_defaults(obs: dict) -> dict:
    f = obs["finding"]
    risk = compute_risk(f["suggested_likelihood"], f["suggested_severity"])
    return {
        "title": f.get("title") or "",
        "scenario": f["scenario"] if f["scenario"] != "none" else None,
        "likelihood": f["suggested_likelihood"],
        "severity": f["suggested_severity"],
        "description": f.get("description", ""),
        "people": "",
        "tags": [],
        "actions": {a: True for a in (f.get("suggested_actions") or [])},
        "other_action": "",
        "owner": f.get("responsible_team") or None,
        "priority": risk.level,
        "due": ui.now_local().date() + dt.timedelta(days=DUE_DAYS[risk.level]),
        "notes": "",
    }


def _actions(rv: dict) -> list[str]:
    out = [a for a, on in rv["actions"].items() if on]
    if (rv.get("other_action") or "").strip():
        out.append(rv["other_action"].strip())
    return out


def _step_review(obs: dict) -> None:
    rv = obs.setdefault("review", _review_defaults(obs))

    left, right = st.columns([1.35, 1], gap="large")
    with left, st.container(key="card_review"):
        _card_title("Review &amp; Confirm", "Check the AI analysis, make changes if needed, and confirm the hazard record.")
        ui.required_legend()
        img, fields = st.columns([1, 2.4], gap="medium")
        with img:
            st.markdown(ui.thumb(None, w="100%", h=136, radius=10, src=ui.bytes_uri(obs["photo_bytes"], obs["photo_mime"])),
                        unsafe_allow_html=True)
            with st.popover("View full image", width="stretch"):
                st.image(obs["photo_bytes"], width="stretch")
        with fields:
            rv["title"] = st.text_input(ui.req("Observation title"), value=rv["title"], max_chars=80,
                                        placeholder="e.g. Boxes blocking fire extinguisher", key="rv_title")
            cats = [k for k in SCENARIO_LABELS if k != "none"]
            rv["scenario"] = st.selectbox(ui.req("Category"), cats,
                                          index=cats.index(rv["scenario"]) if rv["scenario"] in cats else None,
                                          format_func=SCENARIO_LABELS.get, placeholder="Select a category", key="rv_cat")

        lcol, scol, rcol = st.columns([1, 1, 0.8], vertical_alignment="bottom")
        rv["likelihood"] = lcol.selectbox(ui.req("Likelihood"), [1, 2, 3], index=rv["likelihood"] - 1,
                                          format_func=LIKELIHOOD_LABELS.get, key="rv_l")
        rv["severity"] = scol.selectbox(ui.req("Severity"), [1, 2, 3], index=rv["severity"] - 1,
                                        format_func=SEVERITY_LABELS.get, key="rv_s")
        risk = compute_risk(rv["likelihood"], rv["severity"])
        rcol.markdown(f'<div class="sg-flabel">Risk level</div>'
                      f'<div class="sg-riskbox">{ui.risk_pill(risk.level)} <span class="sg-small">score {risk.score}</span></div>',
                      unsafe_allow_html=True)

        rv["description"] = st.text_area(ui.req("Description"), value=rv["description"], max_chars=500, height=110,
                                         key="rv_desc")
        rv["people"] = st.text_input("People / operations exposed", value=rv["people"], max_chars=150,
                                     placeholder="e.g. Warehouse staff, visitors, emergency response", key="rv_people")
        base_tags = ["Fire Safety", "Housekeeping", "Egress", "PPE", "Work at height", "Electrical"]
        rv["tags"] = st.multiselect("Tags", options=list(dict.fromkeys(base_tags + rv["tags"])), default=rv["tags"],
                                    accept_new_options=True, placeholder="Add tag", key="rv_tags")

    with right, st.container(key="card_review_actions"):
        heading = "Corrective actions" if obs.get("manual") else "AI Suggested Actions"
        st.markdown(f'<div class="sg-findings-h"><span class="material-symbols-rounded">checklist</span>{heading}</div>'
                    f'<p class="sg-small" style="margin:0 0 .3rem">{ui.req_html("Select or add at least one action")}</p>',
                    unsafe_allow_html=True)
        for i, action in enumerate(list(rv["actions"].keys())):
            rv["actions"][action] = st.checkbox(action, value=rv["actions"][action], key=f"rv_act_{i}")
        rv["other_action"] = st.text_input("Other action", value=rv["other_action"], max_chars=200,
                                           placeholder="+ Add another corrective action", key="rv_other",
                                           label_visibility="collapsed")
        st.divider()
        teams = list(dict.fromkeys(([rv["owner"]] if rv["owner"] else []) + DEFAULT_TEAMS))
        rv["owner"] = st.selectbox(ui.req("Assign to"), teams, index=teams.index(rv["owner"]) if rv["owner"] in teams else None,
                                   accept_new_options=True, placeholder="Select or type a team", key="rv_owner")
        pcol, dcol = st.columns(2)
        rv["priority"] = pcol.selectbox(ui.req("Priority"), PRIORITIES, index=PRIORITIES.index(rv["priority"]), key="rv_prio")
        rv["due"] = dcol.date_input(ui.req("Target date"), value=rv["due"], min_value=ui.now_local().date(),
                                    format="YYYY/MM/DD", key="rv_due")
        rv["notes"] = st.text_area("Additional notes (optional)", value=rv["notes"], max_chars=300, height=80,
                                   placeholder="Add any additional notes...", key="rv_notes")

    b0, _, b1, b2 = st.columns([1, 1.2, 1, 1.5])
    if b0.button("Back", icon=":material/arrow_back:", width="stretch", key="rv_back"):
        obs["step"] = 1 if obs.get("manual") else 2
        st.rerun()
    draft = b1.button("Save as Draft", icon=":material/save:", width="stretch", key="rv_draft")
    confirm = b2.button("Confirm & Create Record", icon=":material/arrow_forward:", icon_position="right",
                        type="primary", width="stretch", key="rv_confirm")

    if draft:
        if not rv["title"].strip():
            st.error("Add an observation title before saving a draft.", icon=":material/error:")
        else:
            _save(obs, mode="draft")
    if confirm:
        missing = [label for label, ok in (
            ("Observation title", rv["title"].strip()),
            ("Category", rv["scenario"]),
            ("Description", rv["description"].strip()),
            ("At least one corrective action", _actions(rv)),
            ("Assign to", rv["owner"]),
            ("Priority", rv["priority"]),
            ("Target date", rv["due"]),
        ) if not ok]
        if missing:
            st.error("Please complete the required field(s): " + ", ".join(missing), icon=":material/error:")
        else:
            _save(obs, mode="confirm")


# ---------------------------------------------------------------------------
# Persist (the only place this flow writes to the register)
# ---------------------------------------------------------------------------
def _save(obs: dict, mode: str, reject_reason: str = "") -> None:
    actor = st.session_state.get("reviewer") or auth.current_user()["name"]
    f = obs["finding"]
    rv = obs.get("review") or _review_defaults(obs)
    ai_risk = compute_risk(f["suggested_likelihood"], f["suggested_severity"])
    scenario = rv.get("scenario") or f["scenario"]
    try:
        with st.spinner("Saving evidence..."):
            photo_url = store.upload_evidence(obs["photo_bytes"], obs.get("photo_name") or "photo.jpg", obs["photo_mime"])
            audio_url = None
            if obs.get("audio_bytes"):
                audio_url = store.upload_evidence(obs["audio_bytes"], "voice-note.wav", obs.get("audio_mime") or "audio/wav")

            extra = {
                "title": (rv.get("title") or f.get("title") or "").strip(),
                "observed_at": dt.datetime.combine(obs["date"], obs["time"]).isoformat(),
                "reporter_note": (obs.get("note") or "").strip(),
                "people_exposed": rv.get("people", ""),
                "tags": rv.get("tags", []),
                "priority": rv.get("priority"),
                "notes": rv.get("notes", ""),
                "manual_entry": bool(obs.get("manual")),
            }
            draft_risk = compute_risk(rv["likelihood"], rv["severity"])
            if mode == "draft":
                extra["draft_action"] = {
                    "actions": _actions(rv), "owner": rv.get("owner"), "priority": rv.get("priority"),
                    "due_date": rv["due"].isoformat() if rv.get("due") else None,
                }
            hid = store.create_hazard(
                scenario=scenario,
                site=obs["location"].strip(),
                date=obs["date"].isoformat(),
                activity=(obs.get("activity") or "").strip(),
                source_photo_url=photo_url,
                source_audio_url=audio_url,
                ai_finding={
                    "description": rv["description"] if mode == "draft" else f["description"],
                    "confidence": f["confidence"],
                    "confidence_score": f.get("confidence_score", 0),
                    "raw_model_output": f,
                },
                risk=(draft_risk if mode == "draft" else ai_risk).model_dump(),
                actor=actor,
                extra=extra,
                note=("Observation captured; manual assessment." if obs.get("manual")
                      else "Observation captured; AI analysis completed."),
            )

            if mode == "reject":
                store.reject_hazard(hid, actor, reject_reason.strip())
            elif mode == "draft":
                store.update_details(hid, actor, {}, "Saved as draft by reviewer; awaiting confirmation.")
            else:
                _confirm_and_assign(hid, actor, f, rv, ai_risk, draft_risk, scenario)
    except Exception as exc:
        st.error(f"Could not save the record ({type(exc).__name__}: {exc}). Nothing was lost -- try again.",
                 icon=":material/cloud_off:")
        return

    if mode == "reject":
        ui.flash("Finding rejected and logged for audit.", "info")
        _reset("home")
    elif mode == "draft":
        ui.flash("Draft saved. You'll find it under My Tasks.", "info")
        _reset("tasks")
    else:
        obs["saved_id"] = hid
        obs["step"] = 4
    st.rerun()


def _confirm_and_assign(hid, actor, f, rv, ai_risk, draft_risk, scenario) -> None:
    edited = (rv["description"].strip() != f["description"].strip()
              or (draft_risk.likelihood, draft_risk.severity) != (ai_risk.likelihood, ai_risk.severity)
              or scenario != f["scenario"])
    if edited:
        store.edit_finding(hid, actor, rv["description"].strip(), draft_risk.model_dump(), scenario=scenario)
    else:
        store.confirm_hazard(hid, actor)
    store.assign_action(
        hid, actor,
        description="; ".join(_actions(rv)),
        owner=rv["owner"],
        due_date=rv["due"].isoformat(),
        escalation_rule=ESCALATION[rv["priority"]],
        priority=rv["priority"],
    )


# ---------------------------------------------------------------------------
# Step 4 - Assigned
# ---------------------------------------------------------------------------
def _view_saved(hid: str) -> None:
    _reset()
    nav.open_hazard(hid)


def _step_done(obs: dict) -> None:
    h = store.get_hazard(obs["saved_id"]) or {"id": obs["saved_id"]}
    action = h.get("action") or {}
    _, mid, _ = st.columns([1, 2.2, 1])
    with mid, st.container(key="card_done"):
        st.markdown(
            '<div class="sg-closed-hero"><div class="sg-closed-check" style="background:var(--sg-grad);box-shadow:0 0 0 10px #E8F1FF">'
            '<span class="material-symbols-rounded">assignment_turned_in</span></div>'
            '<div class="sg-closed-h" style="color:var(--sg-blue)">Record created &amp; action assigned</div>'
            '<p class="sg-muted">The hazard is confirmed and the responsible team has a corrective action.</p></div>',
            unsafe_allow_html=True,
        )
        st.markdown(ui.kv_rows([
            ("Record ID", f"<strong>{ui.esc(ui.hazard_ref(h))}</strong>"),
            ("Observation", ui.esc(ui.hazard_title(h))),
            ("Location", ui.esc(h.get("site", ""))),
            ("Risk level", ui.risk_pill((h.get("risk") or {}).get("level"))),
            ("Assigned to", ui.esc(action.get("owner", ""))),
            ("Priority", ui.pill(action.get("priority", "-"), PRIORITY_COLOR.get(action.get("priority"), "gray"))),
            ("Target date", ui.fmt_date(action.get("due_date"))),
            ("Corrective action", ui.esc(action.get("description", ""))),
        ]), unsafe_allow_html=True)
        st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.button("View record", icon=":material/visibility:", width="stretch", key="done_view",
                  on_click=_view_saved, args=(h["id"],))
        c2.button("Report another", icon=":material/add_a_photo:", width="stretch", key="done_new", on_click=_reset)
        c3.button("Back to Dashboard", type="primary", width="stretch", key="done_home", on_click=_reset, args=("home",))
