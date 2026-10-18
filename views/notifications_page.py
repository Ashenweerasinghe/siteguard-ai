"""Notifications - latest activity and due-date alerts."""

from __future__ import annotations

import streamlit as st

from lib import auth, data, nav, notifications, ui


def _open(hid: str) -> None:
    nav.open_hazard(hid)


def render() -> None:
    user = auth.current_user()
    me = st.session_state.get("reviewer", user["name"])
    feed = notifications.build(data.hazards())
    seen = notifications.last_seen(user["username"])
    unread = [n for n in feed if notifications.is_unread(n, seen, me)]

    def actions() -> None:
        st.button("Mark all as read", icon=":material/done_all:", key="nt_read", disabled=not unread,
                  on_click=notifications.mark_all_read, args=(user["username"],))

    ui.page_header("Notifications", f"{len(unread)} unread · latest activity across the hazard register.", actions=actions)
    view = st.segmented_control("Show", ["All", "Unread", "Alerts"], default="All", required=True, key="nt_view",
                                format_func=lambda v: f"{v} ({len(unread)})" if v == "Unread" else v,
                                label_visibility="collapsed") or "All"
    items = unread if view == "Unread" else [n for n in feed if n["kind"] == "alert"] if view == "Alerts" else feed
    if not items:
        ui.empty_state("You're all caught up." if view != "Alerts" else "No overdue or due-soon actions.", "notifications_off")
        return

    limit = st.session_state.get("nt_limit", 30)
    last_day = None
    for n in items[:limit]:
        d = ui.parse_iso(n["ts"])
        day = d.strftime("%A, %d %b %Y") if d else ""
        if day != last_day:
            today = ui.now_local().date()
            label = "Today" if d and d.date() == today else "Yesterday" if d and (today - d.date()).days == 1 else day
            st.markdown(f'<div class="sg-small" style="margin:.8rem 0 .3rem;font-weight:600">{label}</div>', unsafe_allow_html=True)
            last_day = day
        bg, fg = ui.PILL[n["color"]]
        dot = '<span class="sg-unread"></span>' if notifications.is_unread(n, seen, me) else ""
        with st.container(key=f"row_nt_{n['id'].replace(':', '_')}"):
            c1, c2, c3 = st.columns([0.6, 7, 1.3], vertical_alignment="center")
            c1.markdown(f'<div class="sg-nt-ic" style="background:{bg}"><span class="material-symbols-rounded" style="color:{fg}">'
                        f'{n["icon"]}</span></div>', unsafe_allow_html=True)
            who = "" if n["actor"] in ("system", "") else f' · {ui.esc("You" if n["actor"] == me else n["actor"])}'
            c2.markdown(f'<p class="sg-row-title">{ui.esc(n["title"])}{dot}</p>'
                        f'<p class="sg-row-desc" style="margin-top:.1rem">{ui.esc(n["body"])}</p>'
                        f'<div class="sg-small">{ui.rel_time(n["ts"])}{who}</div>', unsafe_allow_html=True)
            c3.button("Open", key=f"nt_open_{n['id']}", width="stretch", on_click=_open, args=(n["hazard_id"],))
    if len(items) > limit:
        st.button("Show older", key="nt_more", on_click=lambda: st.session_state.update(nt_limit=limit + 30))
