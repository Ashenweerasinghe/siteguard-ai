"""Settings - profile, system status, demo data."""

from __future__ import annotations

import shutil

import streamlit as st

from lib import auth, demo_seed, gemini, store, ui
from views.components import header_actions


def render() -> None:
    user = auth.current_user()
    ui.page_header("Settings", "Your profile and system status.", actions=header_actions(False))
    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(key="card_set_profile"):
        ui.section("Profile")
        ui.required_legend()
        with st.form("profile_form", border=False):
            name = st.text_input(ui.req("Display name"), value=st.session_state.get("reviewer", user["name"]), max_chars=60,
                                 help="Recorded as the actor in every history entry you create.")
            st.text_input("Username", value=user["username"], disabled=True)
            st.text_input("Role", value=user["role"], disabled=True)
            if st.form_submit_button("Save profile", type="primary"):
                if not name.strip():
                    st.error("Display name is required.")
                else:
                    st.session_state["reviewer"] = name.strip()
                    ui.flash("Profile saved.")
                    st.rerun()

    with c2, st.container(key="card_set_system"):
        ui.section("System")
        st.markdown(ui.kv_rows([
            ("Storage", ui.esc(store.backend_name())),
            ("AI model", ui.esc("Demo AI (mock)" if gemini.mock_enabled() else gemini.MODEL_NAME)),
            ("Time zone", ui.esc(str(ui.TZ))),
            ("Accounts", "Built-in demo accounts" if auth.using_demo_accounts() else "Configured users"),
        ]), unsafe_allow_html=True)
        st.markdown('<div style="height:.6rem"></div>', unsafe_allow_html=True)
        ui.section("Demo data")
        st.caption("Adds fabricated records covering every workflow state (marked as seeded).")
        if st.button("Load demo data", icon=":material/dataset:", key="set_seed"):
            with st.spinner("Seeding..."):
                n = len(demo_seed.seed(st.session_state.get("reviewer", "seed-script")))
            ui.flash(f"Added {n} demo records.")
            st.rerun()
        if store.is_local():
            with st.popover("Reset local data", icon=":material/delete_forever:"):
                st.caption("Deletes every record and evidence file in ./data. This cannot be undone.")
                if st.button("Delete everything", type="primary", key="set_reset"):
                    from lib import local_store

                    shutil.rmtree(local_store.ROOT, ignore_errors=True)
                    store._backend = None
                    store._bump()
                    ui.flash("Local data cleared.", "info")
                    st.rerun()
