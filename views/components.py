"""Reusable widgets built on lib/ui.py."""

from __future__ import annotations

from typing import Any, Callable, Optional

import streamlit as st

from lib import nav, ui


def bell(key: str = "sg_bell") -> None:
    """Notification bell with unread count; opens the notifications page."""
    n = st.session_state.get("_unread", 0)
    with st.container(key=key):
        st.button(
            f"{n}" if n else " ", icon=":material/notifications:", key=f"{key}_btn",
            help=f"{n} unread notification(s)" if n else "Notifications",
            on_click=nav.set_page, args=("notifications",),
        )


def header_actions(show_date: bool = True) -> Callable[[], None]:
    def _render() -> None:
        if show_date:
            st.markdown(f'<span class="sg-small">{ui.now_local().strftime("%a, %d %b %Y")}</span>', unsafe_allow_html=True)
        bell()

    return _render


def stat_grid(stats: list[tuple[str, int, str, str]]) -> None:
    """stats: (label, value, material icon, colour key). One HTML grid => equal heights."""
    cells = []
    for label, value, icon, color in stats:
        bg, fg = ui.PILL[color]
        cells.append(
            f'<div class="sg-stat"><div class="sg-stat-ic" style="background:{bg};color:{fg}">'
            f'<span class="material-symbols-rounded" style="color:{fg}">{icon}</span></div>'
            f'<div><div class="sg-stat-n">{value}</div><div class="sg-stat-l">{ui.esc(label)}</div></div></div>'
        )
    st.markdown(f'<div class="sg-stats">{"".join(cells)}</div>', unsafe_allow_html=True)


def _meta(h: dict[str, Any]) -> str:
    return (
        f'<span><span class="material-symbols-rounded">location_on</span>{ui.esc(h.get("site", "-"))}</span>'
        f'<span>{ui.fmt_date(h.get("date"))}</span>'
        f'<span class="sg-small">{ui.esc(ui.hazard_ref(h))}</span>'
    )


def hazard_row(
    h: dict[str, Any],
    key: str,
    compact: bool = False,
    menu: Optional[Callable[[dict[str, Any]], None]] = None,
) -> None:
    """One list row: fixed thumbnail | title + meta | pills + action. Always vertically centred."""
    risk = (h.get("risk") or {}).get("level")
    action = h.get("action") or {}
    with st.container(key=f"row_{key}_{h['id']}"):
        if compact:
            c1, c2, c3, c4 = st.columns([1.05, 5, 1.6, 0.55], vertical_alignment="center", gap="small")
            c1.markdown(ui.thumb(h.get("source_photo_url"), w=64, h=52), unsafe_allow_html=True)
            c2.markdown(
                f'<p class="sg-row-title">{ui.esc(ui.hazard_title(h))}</p><div class="sg-row-meta">{_meta(h)}</div>',
                unsafe_allow_html=True,
            )
            c3.markdown(f'<div class="sg-row-right">{ui.risk_pill(risk)}</div>', unsafe_allow_html=True)
            c4.button("", icon=":material/chevron_right:", key=f"open_{key}_{h['id']}", type="tertiary",
                      help="Open record", on_click=nav.open_hazard, args=(h["id"],))
            return

        c1, c2, c3 = st.columns([1.25, 5.2, 2.3], vertical_alignment="center", gap="medium")
        c1.markdown(ui.thumb(h.get("source_photo_url"), w=96, h=76), unsafe_allow_html=True)
        desc = action.get("description") or (h.get("ai_finding") or {}).get("description", "")
        foot = [ui.risk_pill(risk)]
        if action.get("owner"):
            foot.append(f'<span><span class="material-symbols-rounded">groups</span>{ui.esc(action["owner"])}</span>')
        if action.get("due_date") and h.get("status") != "closed":
            ds = ui.due_state(action["due_date"])
            cls = {"overdue": "sg-overdue", "soon": "sg-soon"}.get(ds, "")
            label = "Overdue" if ds == "overdue" else "Due"
            foot.append(f'<span class="{cls}"><span class="material-symbols-rounded">event</span>{label} {ui.fmt_date(action["due_date"])}</span>')
        elif h.get("closed_at"):
            foot.append(f'<span><span class="material-symbols-rounded">task_alt</span>Closed {ui.fmt_date(h["closed_at"])}</span>')
        c2.markdown(
            f'<p class="sg-row-title">{ui.esc(ui.hazard_title(h))}</p>'
            f'<div class="sg-row-meta">{_meta(h)}</div>'
            f'<p class="sg-row-desc">{ui.esc(desc)}</p>'
            f'<div class="sg-row-meta" style="margin-top:.4rem">{"".join(foot)}</div>',
            unsafe_allow_html=True,
        )
        with c3:
            with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small"):
                st.markdown(ui.status_pill(h), unsafe_allow_html=True)
                if menu:
                    with st.popover("", icon=":material/more_vert:", key=f"menu_{key}_{h['id']}"):
                        menu(h)
                else:
                    st.button("Open", key=f"open_{key}_{h['id']}", on_click=nav.open_hazard, args=(h["id"],))


def default_menu(h: dict[str, Any]) -> None:
    st.button("View details", icon=":material/visibility:", key=f"m_view_{h['id']}", width="stretch",
              type="tertiary", on_click=nav.open_hazard, args=(h["id"],))
    if h.get("status") in {"action_assigned", "reopened", "pending_closure_review"}:
        st.button("Follow-up / verify", icon=":material/published_with_changes:", key=f"m_fu_{h['id']}",
                  width="stretch", type="tertiary", on_click=nav.set_page, args=("followup",),
                  kwargs={"followup_target": h["id"]})
