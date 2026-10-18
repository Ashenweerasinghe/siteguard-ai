"""Screen 6 - Hazard Register (All / Open / In Progress / Closed) + record detail."""

from __future__ import annotations

import datetime as dt

import streamlit as st

from lib import data, nav, report, store, ui
from lib.schema import DEFAULT_TEAMS, PRIORITIES, SCENARIO_LABELS, STATUS_GROUP
from views.components import default_menu, hazard_row, header_actions

TABS = ["All", "Open", "In Progress", "Closed"]
PAGE_SIZE = 20


def render() -> None:
    hid = st.session_state.get("selected_hazard_id")
    if hid:
        render_detail(hid)
        return

    ui.page_header("Hazard Register", "Every observation, its corrective action and its audit trail.",
                   actions=header_actions(False))
    try:
        hazards = data.hazards()
    except Exception as exc:
        st.error(f"Could not load the hazard register ({type(exc).__name__}).")
        return

    s, f = st.columns([6, 1], vertical_alignment="bottom")
    query = s.text_input("Search", placeholder="Search hazards, location, or ID...", icon=":material/search:",
                         label_visibility="collapsed", key="reg_q").strip().lower()
    with f.popover("Filters", icon=":material/tune:", width="stretch"):
        cats = st.multiselect("Category", [k for k in SCENARIO_LABELS], format_func=SCENARIO_LABELS.get, key="reg_cat")
        risks = st.multiselect("Risk level", ["High", "Medium", "Low"], key="reg_risk")
        owners = sorted({(h.get("action") or {}).get("owner") for h in hazards if (h.get("action") or {}).get("owner")})
        owner = st.multiselect("Assigned to", owners, key="reg_owner")
        sort = st.selectbox("Sort by", ["Newest first", "Oldest first", "Due date", "Highest risk"], key="reg_sort")
        show_rejected = st.toggle("Show rejected findings", value=False, key="reg_rej")

    def match(h: dict) -> bool:
        if h.get("rejected") and not show_rejected:
            return False
        if cats and h.get("scenario") not in cats:
            return False
        if risks and (h.get("risk") or {}).get("level") not in risks:
            return False
        if owner and (h.get("action") or {}).get("owner") not in owner:
            return False
        if query:
            hay = " ".join(str(x) for x in (ui.hazard_ref(h), ui.hazard_title(h), h.get("site"), h.get("activity"),
                                            (h.get("ai_finding") or {}).get("description"), (h.get("action") or {}).get("owner"),
                                            " ".join(h.get("tags") or []))).lower()
            if query not in hay:
                return False
        return True

    filtered = [h for h in hazards if match(h)]
    counts = {t: (len(filtered) if t == "All" else sum(1 for h in filtered if STATUS_GROUP.get(h.get("status")) == t)) for t in TABS}
    tab = st.segmented_control("Status", TABS, default="All", required=True, key="reg_tab",
                               format_func=lambda t: f"{t} ({counts[t]})", label_visibility="collapsed") or "All"
    rows = filtered if tab == "All" else [h for h in filtered if STATUS_GROUP.get(h.get("status")) == tab]

    if sort == "Oldest first":
        rows = list(reversed(rows))
    elif sort == "Due date":
        rows.sort(key=lambda h: (h.get("action") or {}).get("due_date") or "9999")
    elif sort == "Highest risk":
        rows.sort(key=lambda h: -(h.get("risk") or {}).get("score", 0))

    if not rows:
        ui.empty_state("No hazards match these filters." if hazards else "The register is empty. Capture your first observation.",
                       "search_off" if hazards else "add_a_photo")
        return

    limit = st.session_state.get("reg_limit", PAGE_SIZE)
    for h in rows[:limit]:
        hazard_row(h, "reg", menu=default_menu)
    st.caption(f"Showing {min(limit, len(rows))} of {len(rows)}")
    if len(rows) > limit:
        st.button("Show more", key="reg_more", on_click=lambda: st.session_state.update(reg_limit=limit + PAGE_SIZE))


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
def render_detail(hazard_id: str) -> None:
    h = store.get_hazard(hazard_id)
    if not h:
        st.error("Hazard not found.")
        st.session_state["selected_hazard_id"] = None
        return
    actor = st.session_state.get("reviewer", "Reviewer")

    st.button("Back to register", icon=":material/arrow_back:", type="tertiary", key="det_back",
              on_click=nav.set_page, args=("register",), kwargs={"selected_hazard_id": None})
    risk = h.get("risk") or {}
    ui.page_header(ui.hazard_title(h), f"{h.get('site', '')}  ·  {ui.fmt_date(h.get('date'))}  ·  {ui.hazard_ref(h)}",
                   actions=header_actions(False))
    st.markdown(f'{ui.status_pill(h)} &nbsp;{ui.risk_pill(risk.get("level"))} &nbsp;'
                f'{ui.pill(SCENARIO_LABELS.get(h.get("scenario", ""), h.get("scenario", "")), "amber")}',
                unsafe_allow_html=True)
    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    left, right = st.columns([1, 1.3], gap="large")
    with left, st.container(key="card_det_evidence"):
        followups = h.get("followups") or []
        if followups:
            b, a = st.columns(2)
            with b:
                st.markdown('<div class="sg-flabel">Before</div>', unsafe_allow_html=True)
                ui.evidence_img(h.get("source_photo_url"), 200)
                st.caption(ui.fmt_date(h.get("date")))
            with a:
                st.markdown('<div class="sg-flabel">After (latest)</div>', unsafe_allow_html=True)
                ui.evidence_img(followups[-1].get("photo_url"), 200)
                st.caption(ui.fmt_dt(followups[-1].get("timestamp")))
        else:
            ui.evidence_img(h.get("source_photo_url"), 300)
        with st.popover("View full image", icon=":material/open_in_full:", width="stretch"):
            ui.full_image(h.get("source_photo_url"))
        if h.get("source_audio_url"):
            st.markdown('<div class="sg-flabel">Voice note</div>', unsafe_allow_html=True)
            try:
                st.audio(h["source_audio_url"] if h["source_audio_url"].startswith("http") else store.read_evidence(h["source_audio_url"]))
            except Exception:
                st.caption("Audio unavailable.")

    with right, st.container(key="card_det_info"):
        finding = h.get("ai_finding") or {}
        conf = finding.get("confidence", "uncertain")
        conf_html = (ui.pill("Confirmed", "green") if conf == "confirmed" else ui.pill("Inconclusive", "amber"))
        if finding.get("confidence_score"):
            conf_html += f' <span class="sg-small">{finding["confidence_score"]}%</span>'
        raw = finding.get("raw_model_output") or {}
        rows = [
            ("Description", ui.esc(finding.get("description", ""))),
            ("Risk", f'{ui.risk_pill(risk.get("level"))} <span class="sg-small">likelihood {risk.get("likelihood")} x severity {risk.get("severity")} = {risk.get("score")}</span>'),
            ("AI confidence", conf_html),
            ("Observed", ui.esc(ui.fmt_dt(h["observed_at"]) if h.get("observed_at") else ui.fmt_date(h.get("date")))),
            ("Activity", ui.esc(h.get("activity") or "-")),
            ("Reported by", ui.esc(h.get("created_by", "-"))),
            ("People exposed", ui.esc(h.get("people_exposed") or "-")),
            ("Tags", " ".join(ui.pill(t, "blue") for t in (h.get("tags") or [])) or "-"),
        ]
        if h.get("reporter_note"):
            rows.append(("Reporter's note", ui.esc(h["reporter_note"])))
        if raw.get("reasoning"):
            rows.append(("AI reasoning", f'<span class="sg-small">{ui.esc(raw["reasoning"])}</span>'))
        if h.get("notes"):
            rows.append(("Notes", ui.esc(h["notes"])))
        st.markdown(ui.kv_rows(rows), unsafe_allow_html=True)

    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)
    act, hist = st.columns([1.3, 1], gap="large")
    with act, st.container(key="card_det_action"):
        _action_panel(h, actor)
    with hist, st.container(key="card_det_hist"):
        ui.section("History")
        items = "".join(
            f'<div class="sg-tl-item"><div class="sg-tl-t">{ui.esc(e.get("event", "").replace("_", " ").capitalize())}</div>'
            f'<div class="sg-tl-m">{ui.esc(e.get("note", ""))}</div>'
            f'<div class="sg-small">{ui.esc(e.get("actor", ""))} · {ui.fmt_dt(e.get("timestamp"))}</div></div>'
            for e in reversed(h.get("history", []))
        )
        st.markdown(f'<div class="sg-tl">{items}</div>', unsafe_allow_html=True)


def _action_panel(h: dict, actor: str) -> None:
    status = h.get("status")
    action = h.get("action") or {}

    if status == "flagged":
        ui.section("Awaiting reviewer confirmation")
        st.markdown('<p class="sg-muted">This draft has not been confirmed. Confirm it to open a corrective action, '
                    'or reject it if no hazard is present.</p>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        if c1.button("Confirm finding", type="primary", icon=":material/verified:", width="stretch", key="det_confirm"):
            store.confirm_hazard(h["id"], actor)
            ui.flash("Hazard confirmed. Now assign a corrective action.")
            st.rerun()
        with c2.popover("Reject finding", icon=":material/do_not_disturb_on:", width="stretch"):
            reason = st.text_input("Reason (optional)", key="det_rej_reason", max_chars=200)
            if st.button("Reject", type="primary", key="det_reject", width="stretch"):
                store.reject_hazard(h["id"], actor, reason.strip())
                ui.flash("Finding rejected and logged for audit.", "info")
                st.rerun()
        return

    if status in {"reviewer_confirmed", "reopened"}:
        if status == "reopened" and action:
            st.markdown(ui.callout("Closure was rejected", "The hazard is open again. Reassign or submit new evidence.",
                                   "warn", "replay"), unsafe_allow_html=True)
            st.button("Submit new evidence", icon=":material/published_with_changes:", key="det_fu_re", width="stretch",
                      on_click=nav.set_page, args=("followup",), kwargs={"followup_target": h["id"], "selected_hazard_id": None})
        _assign_form(h, actor)
        return

    ui.section("Corrective action")
    rows = [
        ("Action", ui.esc(action.get("description", "-"))),
        ("Assigned to", ui.esc(action.get("owner", "-"))),
        ("Priority", ui.esc(action.get("priority") or h.get("priority") or "-")),
        ("Target date", ui.fmt_date(action.get("due_date"))),
    ]
    if action.get("escalation_rule"):
        rows.append(("Escalation", f'<span class="sg-small">{ui.esc(action["escalation_rule"])}</span>'))
    st.markdown(ui.kv_rows(rows), unsafe_allow_html=True)
    st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)

    if status == "action_assigned":
        st.button("Submit corrective evidence", type="primary", icon=":material/published_with_changes:", width="stretch",
                  key="det_fu", on_click=nav.set_page, args=("followup",),
                  kwargs={"followup_target": h["id"], "selected_hazard_id": None})
    elif status == "pending_closure_review":
        st.markdown(ui.callout("Evidence submitted", "A follow-up photo is waiting for your closure decision.", "info",
                               "pending_actions"), unsafe_allow_html=True)
        st.button("Review closure decision", type="primary", width="stretch", key="det_decide",
                  on_click=nav.set_page, args=("followup",), kwargs={"followup_target": h["id"], "selected_hazard_id": None})
    elif status == "closed":
        if h.get("rejected"):
            st.markdown(ui.callout("Finding rejected", f"Rejected by {ui.esc(h.get('closed_by', '-'))} on {ui.fmt_dt(h.get('closed_at'))}.",
                                   "info", "do_not_disturb_on"), unsafe_allow_html=True)
        else:
            st.markdown(ui.callout("Hazard closed", f"Closure approved by {ui.esc(h.get('closed_by', '-'))} on {ui.fmt_dt(h.get('closed_at'))}.",
                                   "success", "task_alt"), unsafe_allow_html=True)
        st.download_button("Download report", report.hazard_report_html(h), file_name=f"{ui.hazard_ref(h)}.html",
                           mime="text/html", icon=":material/download:", width="stretch", key="det_dl")


def _assign_form(h: dict, actor: str) -> None:
    draft = h.get("draft_action") or {}
    action = h.get("action") or {}
    level = (h.get("risk") or {}).get("level", "Medium")
    ui.section("Assign corrective action")
    with st.form("assign_action_form", border=False):
        st.markdown('<p class="sg-legend"><span class="sg-star">*</span> Required field</p>', unsafe_allow_html=True)
        desc = st.text_area(ui.req("Action description"), value=action.get("description") or "; ".join(draft.get("actions") or []),
                            max_chars=500, height=90)
        default_owner = action.get("owner") or draft.get("owner")
        teams = list(dict.fromkeys(([default_owner] if default_owner else []) + DEFAULT_TEAMS))
        owner = st.selectbox(ui.req("Assign to"), teams, index=0 if default_owner else None, accept_new_options=True,
                             placeholder="Select or type a team")
        c1, c2 = st.columns(2)
        prio_default = action.get("priority") or draft.get("priority") or h.get("priority") or level
        priority = c1.selectbox(ui.req("Priority"), PRIORITIES, index=PRIORITIES.index(prio_default) if prio_default in PRIORITIES else 1)
        due_default = draft.get("due_date") or action.get("due_date")
        try:
            due_val = max(dt.date.fromisoformat(due_default), ui.now_local().date()) if due_default else None
        except ValueError:
            due_val = None
        due = c2.date_input(ui.req("Target date"), value=due_val or ui.now_local().date() + dt.timedelta(days=7),
                            min_value=ui.now_local().date(), format="YYYY/MM/DD")
        escalation = st.text_input("Escalation rule (optional)", value=action.get("escalation_rule", ""),
                                   placeholder="e.g. Escalate to site manager if overdue 48h", max_chars=200)
        submitted = st.form_submit_button("Assign action", type="primary", width="stretch")
    if submitted:
        missing = [n for n, v in (("Action description", desc.strip()), ("Assign to", owner), ("Priority", priority), ("Target date", due)) if not v]
        if missing:
            st.error("Please complete the required field(s): " + ", ".join(missing), icon=":material/error:")
            return
        store.assign_action(h["id"], actor, desc.strip(), owner, due.isoformat(), escalation.strip(), priority)
        ui.flash(f"Action assigned to {owner}.")
        st.rerun()
