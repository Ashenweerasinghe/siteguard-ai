"""Page routing via session_state (custom sidebar matching the design)."""

from __future__ import annotations

import streamlit as st

PAGES = [
    ("home", "Home", ":material/home:"),
    ("observe", "New Observation", ":material/add_a_photo:"),
    ("register", "Hazard Register", ":material/fact_check:"),
    ("tasks", "My Tasks", ":material/assignment_ind:"),
    ("followup", "Follow-ups", ":material/published_with_changes:"),
    ("reports", "Reports", ":material/description:"),
    ("analytics", "Analytics", ":material/monitoring:"),
    ("notifications", "Notifications", ":material/notifications:"),
]


def current() -> str:
    return st.session_state.setdefault("page", "home")


def set_page(page: str, **state) -> None:
    """Use as an on_click callback (no explicit rerun needed)."""
    if page != st.session_state.get("page"):
        st.session_state["closure_done"] = None
    st.session_state["page"] = page
    for k, v in state.items():
        st.session_state[k] = v


def goto(page: str, **state) -> None:
    """Use inline after a button returns True."""
    set_page(page, **state)
    st.rerun()


def open_hazard(hazard_id: str) -> None:
    set_page("register", selected_hazard_id=hazard_id)
