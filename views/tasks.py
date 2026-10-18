"""My Tasks - drafts to confirm, closure decisions, and open corrective actions."""

from __future__ import annotations

import streamlit as st

from lib import data, ui
from views.components import default_menu, hazard_row, header_actions


def render() -> None:
    ui.page_header("My Tasks", "Everything waiting on a person: confirmations, closure decisions and corrective actions.",
                   actions=header_actions(False))
    hazards = data.hazards()
    drafts = [h for h in hazards if h.get("status") == "flagged"]
    pending = [h for h in hazards if h.get("status") == "pending_closure_review"]
    actions = [h for h in hazards if h.get("status") in {"action_assigned", "reopened", "reviewer_confirmed"}]

    overdue = sum(1 for h in actions if ui.due_state((h.get("action") or {}).get("due_date")) == "overdue")
    from views.components import stat_grid

    stat_grid([
        ("Drafts to confirm", len(drafts), "edit_note", "gray"),
        ("Closure decisions", len(pending), "pending_actions", "violet"),
        ("Open actions", len(actions), "assignment_ind", "blue"),
        ("Overdue", overdue, "alarm", "red"),
    ])

    review = drafts + pending
    ui.section(f"Awaiting your review ({len(review)})")
    if not review:
        ui.empty_state("Nothing to review. Nice!", "task_alt")
    for h in review:
        hazard_row(h, "tsk_r", menu=default_menu)

    st.markdown('<div style="height:.8rem"></div>', unsafe_allow_html=True)
    a, b = st.columns([3, 1.3], vertical_alignment="bottom")
    a.markdown(f'<div class="sg-section"><div class="sg-h3">Open corrective actions ({len(actions)})</div></div>',
               unsafe_allow_html=True)
    owners = sorted({(h.get("action") or {}).get("owner") for h in actions if (h.get("action") or {}).get("owner")})
    team = b.selectbox("Team", ["All teams"] + owners, key="tsk_team", label_visibility="collapsed")
    rows = [h for h in actions if team == "All teams" or (h.get("action") or {}).get("owner") == team]
    rows.sort(key=lambda h: (h.get("action") or {}).get("due_date") or "9999")
    if not rows:
        ui.empty_state("No open corrective actions.", "inventory")
    for h in rows:
        hazard_row(h, "tsk_a", menu=default_menu)
