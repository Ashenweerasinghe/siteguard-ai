"""Screen 2 - Dashboard / Home."""

from __future__ import annotations

import streamlit as st

from lib import auth, data, nav, notifications, ui
from lib.schema import STATUS_GROUP
from views.components import hazard_row, header_actions, stat_grid


def counts(hazards: list[dict]) -> dict[str, int]:
    live = [h for h in hazards if h.get("status") != "closed"]
    return {
        "high": sum(1 for h in live if (h.get("risk") or {}).get("level") == "High"),
        "open": sum(1 for h in hazards if STATUS_GROUP.get(h.get("status")) == "Open"),
        "progress": sum(1 for h in hazards if STATUS_GROUP.get(h.get("status")) == "In Progress"),
        "closed": sum(1 for h in hazards if h.get("status") == "closed"),
    }


def render() -> None:
    user = auth.current_user()
    name = st.session_state.get("reviewer", user["name"])
    ui.page_header(name, "Together we make a safer workplace.", eyebrow=f"{ui.greeting()},", actions=header_actions())

    try:
        hazards = data.hazards()
    except Exception as exc:
        st.error(f"Could not load the hazard register ({type(exc).__name__}). Check your storage settings.")
        hazards = []

    main, side = st.columns([2.15, 1], gap="large")
    with main:
        with st.container(key="sg_hero"):
            t, img = st.columns([1.35, 1], vertical_alignment="center", gap="medium")
            with t:
                st.markdown("<div class='sg-hero-h'>Spot it early,<br>Prevent it always.</div>"
                            "<p class='sg-hero-p'>Turn observations into action with the power of AI.</p>", unsafe_allow_html=True)
                st.button("New Observation", icon=":material/add:", key="hero_new", on_click=nav.set_page,
                          args=("observe",), kwargs={"obs": None})
            img.markdown(f'<img class="sg-hero-img" src="{ui.asset_uri("hero_worker.jpg")}" alt="Worker in safety vest">',
                         unsafe_allow_html=True)

        c = counts(hazards)
        stat_grid([
            ("High Risk", c["high"], "warning", "red"),
            ("Open", c["open"], "schedule", "amber"),
            ("In Progress", c["progress"], "autorenew", "blue"),
            ("Closed", c["closed"], "check_circle", "green"),
        ])

        h1, h2 = st.columns([3, 1], vertical_alignment="center")
        h1.markdown('<div class="sg-section"><div class="sg-h3">Recent Observations</div></div>', unsafe_allow_html=True)
        with h2, st.container(horizontal=True, horizontal_alignment="right"):
            st.button("View all", icon=":material/arrow_forward:", icon_position="right", type="tertiary",
                      key="dash_view_all", on_click=nav.set_page, args=("register",), kwargs={"selected_hazard_id": None})
        recent = [h for h in hazards if not h.get("rejected")][:5]
        if not recent:
            ui.empty_state("No observations yet. Tap New Observation to capture your first hazard.", "add_a_photo")
        for h in recent:
            hazard_row(h, "dash", compact=True)

    with side:
        _side_notifications(hazards, user)
        _side_due(hazards)


def _side_notifications(hazards: list[dict], user: dict) -> None:
    feed = notifications.build(hazards)
    seen = notifications.last_seen(user["username"])
    me = st.session_state.get("reviewer", "")
    with st.container(key="card_dash_notif"):
        a, b = st.columns([3, 1.4], vertical_alignment="center")
        a.markdown('<div class="sg-section"><div class="sg-h3">Latest notifications</div></div>', unsafe_allow_html=True)
        with b, st.container(horizontal=True, horizontal_alignment="right"):
            st.button("See all", type="tertiary", key="dash_notif_all", on_click=nav.set_page, args=("notifications",))
        if not feed:
            st.markdown('<p class="sg-muted">You\'re all caught up.</p>', unsafe_allow_html=True)
        for n in feed[:4]:
            bg, fg = ui.PILL[n["color"]]
            dot = '<span class="sg-unread"></span>' if notifications.is_unread(n, seen, me) else ""
            st.markdown(
                f'<div style="display:flex;gap:.7rem;align-items:flex-start;padding:.45rem 0;border-bottom:1px solid var(--sg-line)">'
                f'<div class="sg-nt-ic" style="background:{bg};width:34px;height:34px;flex-shrink:0">'
                f'<span class="material-symbols-rounded" style="color:{fg};font-size:18px">{n["icon"]}</span></div>'
                f'<div style="min-width:0"><div class="sg-tl-t">{ui.esc(n["title"])}{dot}</div>'
                f'<div class="sg-tl-m" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{ui.esc(n["body"])}</div>'
                f'<div class="sg-small">{ui.rel_time(n["ts"])}</div></div></div>',
                unsafe_allow_html=True,
            )


def _side_due(hazards: list[dict]) -> None:
    open_actions = [h for h in hazards if h.get("status") in {"action_assigned", "reopened"} and (h.get("action") or {}).get("due_date")]
    open_actions.sort(key=lambda h: h["action"]["due_date"])
    review = [h for h in hazards if h.get("status") in {"flagged", "pending_closure_review"}]
    with st.container(key="card_dash_due"):
        st.markdown('<div class="sg-section"><div class="sg-h3">Actions due</div></div>', unsafe_allow_html=True)
        if not open_actions:
            st.markdown('<p class="sg-muted">No open corrective actions.</p>', unsafe_allow_html=True)
        for h in open_actions[:4]:
            ds = ui.due_state(h["action"]["due_date"])
            cls = {"overdue": "sg-overdue", "soon": "sg-soon"}.get(ds, "sg-small")
            label = "Overdue" if ds == "overdue" else "Due"
            st.markdown(
                f'<div style="padding:.4rem 0;border-bottom:1px solid var(--sg-line)"><div class="sg-tl-t">{ui.esc(ui.hazard_title(h))}</div>'
                f'<div class="sg-row-meta"><span>{ui.esc(h["action"].get("owner", ""))}</span>'
                f'<span class="{cls}">{label} {ui.fmt_date(h["action"]["due_date"])}</span></div></div>',
                unsafe_allow_html=True,
            )
        if review:
            st.markdown(ui.callout(f"{len(review)} record(s) awaiting your decision",
                                   "Drafts to confirm and follow-ups waiting for a closure decision.", "warn", "pending_actions"),
                        unsafe_allow_html=True)
            st.button("Go to My Tasks", key="dash_tasks", width="stretch", on_click=nav.set_page, args=("tasks",))
