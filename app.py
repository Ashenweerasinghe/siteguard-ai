"""SafeGuard AI -- Streamlit entry point.

Login gate -> custom navy sidebar -> page router (views/*).

Non-negotiable across every screen: the AI proposes, a human approves every state
change. Nothing in the UI writes "safe", "compliant", or "fixed".
"""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import streamlit as st  # noqa: E402

from lib import auth, data, nav, notifications, ui  # noqa: E402
from views import (  # noqa: E402
    analytics,
    dashboard,
    followup,
    login,
    notifications_page,
    observe,
    register,
    reports,
    settings,
    tasks,
)

st.set_page_config(
    page_title="SafeGuard AI | Ceylon Innvoai",
    page_icon=str(ui.BRAND / "logo_head.png"),
    layout="wide",
    initial_sidebar_state="auto",
)
ui.inject_css()
auth.restore_session()

user = auth.current_user()
if not user:
    login.render()
    st.stop()

# The reviewer recorded in every history entry is the signed-in user.
st.session_state.setdefault("reviewer", user["name"])

ROUTES = {
    "home": dashboard.render,
    "observe": observe.render,
    "register": register.render,
    "tasks": tasks.render,
    "followup": followup.render,
    "reports": reports.render,
    "analytics": analytics.render,
    "notifications": notifications_page.render,
    "settings": settings.render,
}

page = nav.current()
try:
    feed = notifications.build(data.hazards())
    unread = notifications.unread_count(feed, user["username"], st.session_state["reviewer"])
except Exception:  # storage unreachable: still render the shell
    feed, unread = [], 0
st.session_state["_unread"] = unread

with st.sidebar:
    st.markdown(ui.brand(compact=True), unsafe_allow_html=True)
    with st.container(key="sg_nav"):
        for key, label, icon in nav.PAGES:
            text = f"{label}  ({unread})" if key == "notifications" and unread else label
            st.button(
                text, icon=icon, key=f"nav_{key}", width="stretch",
                type="primary" if page == key else "secondary",
                on_click=nav.set_page, args=(key,),
                kwargs={"selected_hazard_id": None} if key == "register" else {},
            )
    st.divider()
    with st.container(key="sg_nav_bottom"):
        st.button("Settings", icon=":material/settings:", key="nav_settings", width="stretch",
                  type="primary" if page == "settings" else "secondary", on_click=nav.set_page, args=("settings",))
        initials = "".join(p[0] for p in st.session_state["reviewer"].split()[:2]).upper() or "U"
        st.markdown(
            f'<div class="sg-user"><div class="sg-avatar">{ui.esc(initials)}</div><div>'
            f'<div class="sg-user-name">{ui.esc(st.session_state["reviewer"])}</div>'
            f'<div class="sg-user-role">{ui.esc(user["role"])}</div></div></div>',
            unsafe_allow_html=True,
        )
        if st.button("Sign out", icon=":material/logout:", key="nav_logout", width="stretch"):
            auth.logout()
            st.rerun()
    st.markdown('<div class="sg-side-foot">The AI proposes. You approve every state change.</div>', unsafe_allow_html=True)

ui.show_flash()
ROUTES.get(page, dashboard.render)()
