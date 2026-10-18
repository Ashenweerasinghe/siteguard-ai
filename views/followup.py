"""Screens 7-8 - Follow-up / Verification -> closure decision -> Closure & Report."""

from __future__ import annotations

import random

import streamlit as st

from lib import data, gemini, nav, report, store, ui
from views.components import header_actions

ACTION_STATES = {"action_assigned", "reopened", "reviewer_confirmed"}


def render() -> None:
    closed_id = st.session_state.get("closure_done")
    if closed_id:
        _render_closed(closed_id)
        return

    target = st.session_state.get("followup_target")
    if target:
        h = store.get_hazard(target)
        if h and h.get("status") == "pending_closure_review":
            _render_decision(h)
            return

    ui.page_header("Follow-ups", "Upload evidence after the issue has been addressed, then decide on closure.",
                   actions=header_actions(False))
    hazards = data.hazards()
    pending = [h for h in hazards if h.get("status") == "pending_closure_review"]
    open_h = [h for h in hazards if h.get("status") in ACTION_STATES]

    if pending:
        with st.container(key="card_fu_pending"):
            ui.section(f"Awaiting closure decision ({len(pending)})")
            for h in pending:
                c1, c2, c3 = st.columns([1, 5, 1.6], vertical_alignment="center")
                c1.markdown(ui.thumb(h.get("source_photo_url"), w=64, h=50), unsafe_allow_html=True)
                c2.markdown(f'<p class="sg-row-title">{ui.esc(ui.hazard_title(h))}</p>'
                            f'<div class="sg-row-meta"><span>{ui.esc(h.get("site", ""))}</span><span>{ui.esc(ui.hazard_ref(h))}</span></div>',
                            unsafe_allow_html=True)
                c3.button("Decide", type="primary", key=f"fu_dec_{h['id']}", width="stretch",
                          on_click=nav.set_page, args=("followup",), kwargs={"followup_target": h["id"]})
        st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    if not open_h:
        ui.empty_state("No open hazards need follow-up evidence right now.", "task_alt")
        return

    ids = [h["id"] for h in open_h]
    by_id = {h["id"]: h for h in open_h}
    idx = ids.index(target) if target in ids else 0
    _render_submit(by_id, ids, idx)


def _render_submit(by_id: dict, ids: list[str], idx: int) -> None:
    with st.container(key="card_fu_submit"):
        st.markdown('<div class="sg-h3" style="font-size:1.3rem">Submit Corrective Evidence</div>'
                    '<p class="sg-muted" style="margin:.2rem 0 .3rem">Upload a photo after the issue has been resolved.</p>',
                    unsafe_allow_html=True)
        ui.required_legend()
        hid = st.selectbox(ui.req("Hazard"), ids, index=idx, key="fu_pick",
                           format_func=lambda i: f"{ui.hazard_ref(by_id[i])} · {ui.hazard_title(by_id[i])} · {by_id[i].get('site', '')}")
        h = by_id[hid]
        if h.get("status") == "reviewer_confirmed":
            st.markdown(ui.callout("No corrective action assigned yet",
                                   "You can still submit evidence, but consider assigning an action first.", "warn", "info"),
                        unsafe_allow_html=True)

        before, arrow, after = st.columns([1, 0.12, 1], vertical_alignment="center")
        with before:
            st.markdown('<div class="sg-flabel">Before</div>', unsafe_allow_html=True)
            ui.evidence_img(h.get("source_photo_url"), 260)
            st.caption(ui.fmt_dt(h["observed_at"]) if h.get("observed_at") else ui.fmt_date(h.get("date")))
        arrow.markdown('<div style="display:flex;justify-content:center"><div class="sg-arrow">'
                       '<span class="material-symbols-rounded">arrow_forward</span></div></div>', unsafe_allow_html=True)
        with after:
            st.markdown(f'<div class="sg-flabel">{ui.req_html("After")}</div>', unsafe_allow_html=True)
            photo = st.file_uploader("After photo", type=["jpg", "jpeg", "png"], key=f"fu_photo_{hid}",
                                     label_visibility="collapsed")
            if photo:
                st.markdown(ui.thumb(None, w="100%", h=170, radius=14, src=ui.bytes_uri(photo.getvalue(), photo.type or "image/jpeg")),
                            unsafe_allow_html=True)
                st.caption(ui.now_local().strftime("%d %b %Y, %I:%M %p"))

        note = st.text_area("Add a note (optional)", max_chars=500, height=90, key=f"fu_note_{hid}",
                            placeholder="e.g. Boxes have been relocated to the storage area.")
        submit = st.button("Submit for Verification", icon=":material/arrow_forward:", icon_position="right",
                           type="primary", width="stretch", key="fu_submit")

    if not submit:
        return
    if not photo:
        st.error("Please complete the required field(s): After photo", icon=":material/error:")
        return
    with st.spinner("SafeGuard AI is comparing before/after evidence..."):
        try:
            comparison = gemini.analyze_followup(
                original_image_bytes=store.read_evidence(h["source_photo_url"]),
                original_image_mime_type="image/jpeg",
                new_image_bytes=photo.getvalue(),
                new_image_mime_type=photo.type or "image/jpeg",
                original_finding_description=(h.get("ai_finding") or {}).get("description", ""),
                original_scenario=h.get("scenario", ""),
                reviewer_note=note.strip() or None,
            )
            if comparison is None:
                raise ValueError("the model returned an empty response")
        except gemini.genai_errors.ClientError as exc:
            st.error("Free-tier rate limit reached. Wait about a minute, then try again."
                     if "RESOURCE_EXHAUSTED" in str(exc) else "Gemini rejected this request. Please try again.")
            return
        except gemini.genai_errors.ServerError:
            st.error("Gemini is under heavy demand right now. Please try again in a moment.")
            return
        except Exception as exc:
            st.error(f"AI verification is unavailable ({type(exc).__name__}: {exc}).")
            return
        try:
            url = store.upload_evidence(photo.getvalue(), photo.name, photo.type or "image/jpeg")
            store.add_followup(hid, st.session_state.get("reviewer", "Reviewer"), url, comparison.model_dump(), note.strip())
        except Exception as exc:
            st.error(f"Could not save the evidence ({type(exc).__name__}: {exc}).")
            return
    st.session_state["followup_target"] = hid
    st.rerun()


def _render_decision(h: dict) -> None:
    st.button("Back to follow-ups", icon=":material/arrow_back:", type="tertiary", key="dec_back",
              on_click=lambda: st.session_state.update(followup_target=None))
    ui.page_header("Verify & Close", f"{ui.hazard_title(h)}  ·  {h.get('site', '')}  ·  {ui.hazard_ref(h)}",
                   actions=header_actions(False))
    latest = (h.get("followups") or [{}])[-1]
    comp = latest.get("ai_comparison") or {}

    with st.container(key="card_dec"):
        before, arrow, after = st.columns([1, 0.12, 1], vertical_alignment="center")
        with before:
            st.markdown('<div class="sg-flabel">Before</div>', unsafe_allow_html=True)
            ui.evidence_img(h.get("source_photo_url"), 260)
            st.caption(ui.fmt_date(h.get("date")))
        arrow.markdown('<div style="display:flex;justify-content:center"><div class="sg-arrow">'
                       '<span class="material-symbols-rounded">arrow_forward</span></div></div>', unsafe_allow_html=True)
        with after:
            st.markdown('<div class="sg-flabel">After</div>', unsafe_allow_html=True)
            ui.evidence_img(latest.get("photo_url"), 260)
            st.caption(ui.fmt_dt(latest.get("timestamp")))

        conf = ui.pill("Confirmed", "green") if comp.get("confidence") == "confirmed" else ui.pill("Inconclusive", "amber")
        st.markdown(f'<div class="sg-findings-h" style="margin-top:.8rem"><span class="material-symbols-rounded">'
                    f'auto_awesome</span>AI Verification Summary &nbsp;{conf}</div>', unsafe_allow_html=True)
        rows = [("Comparison", ui.esc(comp.get("comparison", ""))), ("Reasoning", f'<span class="sg-small">{ui.esc(comp.get("reasoning", ""))}</span>')]
        if latest.get("note"):
            rows.append(("Note from the team", ui.esc(latest["note"])))
        st.markdown(ui.kv_rows(rows), unsafe_allow_html=True)
        if comp.get("closure_supported"):
            st.markdown(ui.callout("Evidence suggests the hazard condition has been remediated",
                                   "Approve closure if you agree. The decision is yours.", "success", "check_circle"),
                        unsafe_allow_html=True)
        else:
            st.markdown(ui.callout("Evidence does not support closure yet",
                                   "The original condition may still be present, or the photo is inconclusive.", "warn", "warning"),
                        unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        actor = st.session_state.get("reviewer", "Reviewer")
        if c1.button("Reject - stays open", icon=":material/replay:", width="stretch", key="dec_reject"):
            store.resolve_closure(h["id"], actor, approve=False)
            st.session_state["followup_target"] = None
            ui.flash("Closure rejected. The hazard remains open.", "warning")
            st.rerun()
        if c2.button("Approve closure", icon=":material/task_alt:", type="primary", width="stretch", key="dec_approve"):
            store.resolve_closure(h["id"], actor, approve=True)
            st.session_state["followup_target"] = None
            st.session_state["closure_done"] = h["id"]
            st.rerun()


def _confetti() -> str:
    rnd = random.Random(7)
    colors = ["#0A6CFF", "#18B4F5", "#12B76A", "#F79009", "#E5484D", "#7A5AF8"]
    bits = []
    for _ in range(18):
        left = rnd.choice([rnd.randint(8, 34), rnd.randint(66, 92)])
        bits.append(f'<span class="sg-confetti" style="left:{left}%;top:{rnd.randint(4, 70)}%;'
                    f'background:{rnd.choice(colors)};transform:rotate({rnd.randint(0, 90)}deg)"></span>')
    return "".join(bits)


def _clear_closure(page: str = "home") -> None:
    st.session_state["closure_done"] = None
    st.session_state["page"] = page


def _view_record(hid: str) -> None:
    st.session_state["closure_done"] = None
    nav.open_hazard(hid)


def _render_closed(hid: str) -> None:
    h = store.get_hazard(hid)
    if not h:
        st.session_state["closure_done"] = None
        st.rerun()
    latest = (h.get("followups") or [{}])[-1]
    comp = latest.get("ai_comparison") or {}
    _, mid, _ = st.columns([1, 2, 1])
    with mid, st.container(key="card_closed"):
        st.markdown('<div class="sg-h3" style="font-size:1.3rem">Hazard Closed</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="sg-closed-hero">{_confetti()}<div class="sg-closed-check">'
                    '<span class="material-symbols-rounded">check</span></div>'
                    '<div class="sg-closed-h">Great work!</div>'
                    '<p class="sg-muted">The hazard has been verified and closed by the reviewer.</p></div>',
                    unsafe_allow_html=True)
        with st.container(key="row_closed_card"):
            t, info = st.columns([1, 3], vertical_alignment="center")
            t.markdown(ui.thumb(h.get("source_photo_url"), w="100%", h=96), unsafe_allow_html=True)
            info.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;gap:.5rem">'
                f'<p class="sg-row-title">{ui.esc(ui.hazard_title(h))}</p>{ui.pill("Closed", "green", dot=True)}</div>'
                + ui.kv_rows([("ID", ui.esc(ui.hazard_ref(h))), ("Location", ui.esc(h.get("site", ""))),
                              ("Closed by", ui.esc(h.get("closed_by", ""))), ("Closed on", ui.fmt_dt(h.get("closed_at")))]),
                unsafe_allow_html=True,
            )
        with st.container(horizontal=True, horizontal_alignment="center"):
            st.button("View Full Record", key="closed_view", on_click=_view_record, args=(hid,))
        if comp:
            st.markdown(ui.callout("AI Verification Summary", ui.esc(comp.get("comparison", "")), "success", "verified"),
                        unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.download_button("Download Report", report.hazard_report_html(h), file_name=f"{ui.hazard_ref(h)}.html",
                           mime="text/html", icon=":material/download:", width="stretch", key="closed_dl")
        c2.button("Back to Dashboard", type="primary", width="stretch", key="closed_home", on_click=_clear_closure)
