"""Analytics - simple register trends."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from lib import data, ui
from lib.schema import SCENARIO_LABELS, STATUS_GROUP
from views.components import header_actions


def render() -> None:
    ui.page_header("Analytics", "Where hazards come from and how fast they are closed.", actions=header_actions(False))
    hazards = [h for h in data.hazards() if not h.get("rejected")]
    if not hazards:
        ui.empty_state("Analytics appear once observations are recorded.", "monitoring")
        return
    df = pd.DataFrame([{
        "Status": STATUS_GROUP.get(h.get("status"), "Open"),
        "Category": SCENARIO_LABELS.get(h.get("scenario"), h.get("scenario")),
        "Risk": (h.get("risk") or {}).get("level", "n/a"),
        "Location": h.get("site", ""),
        "Date": (h.get("date") or "")[:10],
    } for h in hazards])

    c1, c2 = st.columns(2, gap="large")
    with c1, st.container(key="card_an_status"):
        ui.section("By status")
        s = df["Status"].value_counts().reindex(["Open", "In Progress", "Closed"], fill_value=0).rename_axis("Status").reset_index(name="Count")
        st.bar_chart(s, x="Status", y="Count", color="#0A6CFF", height=240, sort=False)
    with c2, st.container(key="card_an_risk"):
        ui.section("Open hazards by risk level")
        live = df[df["Status"] != "Closed"]
        r = live["Risk"].value_counts().reindex(["High", "Medium", "Low"], fill_value=0).rename_axis("Risk").reset_index(name="Count")
        st.bar_chart(r, x="Risk", y="Count", color="#E5484D", height=240, sort=False)

    c3, c4 = st.columns(2, gap="large")
    with c3, st.container(key="card_an_cat"):
        ui.section("By category")
        c = df["Category"].value_counts().rename_axis("Category").reset_index(name="Count")
        st.bar_chart(c, x="Category", y="Count", color="#18B4F5", height=240, horizontal=True)
    with c4, st.container(key="card_an_trend"):
        ui.section("Observations - last 14 days")
        today = ui.now_local().date()
        days = [(today - dt.timedelta(days=i)).isoformat() for i in range(13, -1, -1)]
        t = df["Date"].value_counts().reindex(days, fill_value=0).rename_axis("Date").reset_index(name="Observations")
        t["Date"] = pd.to_datetime(t["Date"]).dt.strftime("%d %b")
        st.line_chart(t, x="Date", y="Observations", color="#12B76A", height=240)

    with st.container(key="card_an_loc"):
        ui.section("Top locations")
        loc = df.groupby("Location").agg(Total=("Status", "size"),
                                         Open=("Status", lambda x: int((x != "Closed").sum()))).sort_values("Total", ascending=False)
        st.dataframe(loc.head(10), width="stretch")
