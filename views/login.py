"""Screen 1 - Login / Welcome (username + password)."""

from __future__ import annotations

import time

import streamlit as st

from lib import auth, ui


def _brand_panel() -> str:
    return f"""
    <div class="sg-login-brand">
      {ui.brand()}
      <div class="sg-login-title">SiteGuard <span>AI</span></div>
      <p class="sg-lead">Safer Workplaces<br>Smarter Decisions</p>
      <div class="sg-login-steps"><span>See it</span><span>Report it</span><span>Resolve it</span><span>Verify it</span></div>
      <img class="sg-login-helmet" src="{ui.asset_uri('login_helmet.jpg')}" alt="">
      <div class="sg-login-quote">&ldquo;A safer workplace starts with what you see.&rdquo;</div>
    </div>"""


def render() -> None:
    ui.hide_sidebar()
    st.session_state.setdefault("login_attempts", 0)
    st.session_state.setdefault("lock_until", 0.0)

    left, right = st.columns([1.25, 1], gap="large", vertical_alignment="center")
    with left:
        st.markdown(_brand_panel(), unsafe_allow_html=True)

    with right, st.container(key="sg_login_card"):
        st.markdown('<div class="sg-login-h">Welcome back</div>', unsafe_allow_html=True)
        st.markdown('<p class="sg-muted">Sign in to report, track and verify workplace hazards.</p>', unsafe_allow_html=True)

        locked_for = int(st.session_state["lock_until"] - time.time())
        with st.form("login_form", border=False, enter_to_submit=True):
            username = st.text_input(ui.req("Username"), placeholder="Enter your username",
                                     autocomplete="username", max_chars=64)
            password = st.text_input(ui.req("Password"), type="password", placeholder="Enter your password",
                                     autocomplete="current-password", max_chars=128)
            remember = st.checkbox("Remember me", help="Keeps you signed in on this browser for 7 days.")
            submitted = st.form_submit_button("Sign in", type="primary", width="stretch",
                                              disabled=locked_for > 0)

        if locked_for > 0:
            st.error(f"Too many failed attempts. Try again in {locked_for} seconds.", icon=":material/lock_clock:")
        elif submitted:
            missing = [n for n, v in (("Username", username.strip()), ("Password", password)) if not v]
            if missing:
                st.error(f"Please enter your {' and '.join(missing).lower()}.", icon=":material/error:")
            else:
                user = auth.verify(username, password)
                if user:
                    auth.login(user, remember)
                    st.session_state["page"] = "home"
                    st.rerun()
                st.session_state["login_attempts"] += 1
                left_tries = auth.MAX_ATTEMPTS - st.session_state["login_attempts"]
                if left_tries <= 0:
                    st.session_state["lock_until"] = time.time() + auth.LOCKOUT_SECONDS
                    st.session_state["login_attempts"] = 0
                    st.error("Too many failed attempts. Sign-in is locked for 60 seconds.", icon=":material/lock_clock:")
                else:
                    st.error(f"Incorrect username or password. {left_tries} attempt(s) left.", icon=":material/error:")

        c1, c2 = st.columns(2, vertical_alignment="center")
        with c1:
            ui.required_legend()
        with c2, st.container(horizontal=True, horizontal_alignment="right"):
            with st.popover("Forgot password?", type="tertiary"):
                st.markdown("**Reset your password**")
                st.caption("Passwords are managed by your site administrator. Ask them to issue a new one "
                           "(admins: `python scripts/hash_password.py`).")
        if auth.using_demo_accounts():
            st.info(f"Demo account: **{auth.DEMO_HINT}**", icon=":material/key:")
