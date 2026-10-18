"""Reports - closed records with downloadable reports, register export."""

from __future__ import annotations

import streamlit as st

from lib import data, report, ui
from views.components import hazard_row, header_actions, stat_grid


def _menu(h: dict) -> None:
    from lib import nav

    st.button("View record", icon=":material/visibility:", key=f"rp_v_{h['id']}", type="tertiary", width="stretch",
              on_click=nav.open_hazard, args=(h["id"],))
    st.download_button("Download report", report.hazard_report_html(h), file_name=f"{ui.hazard_ref(h)}.html",
                       mime="text/html", icon=":material/download:", key=f"rp_d_{h['id']}", type="tertiary", width="stretch")


def render() -> None:
    ui.page_header("Reports", "Closure reports and register exports.", actions=header_actions(False))
    hazards = data.hazards()
    closed = [h for h in hazards if h.get("status") == "closed" and not h.get("rejected")]
    durations = []
    for h in closed:
        a, b = ui.parse_iso(h.get("created_at")), ui.parse_iso(h.get("closed_at"))
        if a and b:
            durations.append((b - a).total_seconds() / 86400)
    avg = f"{sum(durations) / len(durations):.1f}" if durations else "-"
    stat_grid([
        ("Total records", len(hazards), "inventory_2", "blue"),
        ("Closed", len(closed), "task_alt", "green"),
        ("Avg. days to close", avg, "timer", "amber"),
        ("Rejected findings", sum(1 for h in hazards if h.get("rejected")), "do_not_disturb_on", "gray"),
    ])

    a, b = st.columns([3, 1.3], vertical_alignment="center")
    a.markdown('<div class="sg-section"><div class="sg-h3">Closed hazards</div></div>', unsafe_allow_html=True)
    b.download_button("Export register (CSV)", report.register_csv(hazards), file_name="siteguard_register.csv",
                      mime="text/csv", icon=":material/table_view:", width="stretch", key="rp_csv")
    if not closed:
        ui.empty_state("No closed hazards yet. Closure reports appear here once a reviewer approves closure.", "description")
    for h in sorted(closed, key=lambda x: x.get("closed_at", ""), reverse=True):
        hazard_row(h, "rp", menu=_menu)
