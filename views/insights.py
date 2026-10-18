"""Site Insights - one Gemini call over the whole register, not one photo.

The counts come from lib/insights.build_digest in plain Python; the model only
interprets them. Nothing here changes a record: it is a briefing a site lead
reads, and every recommendation stays a recommendation.
"""

from __future__ import annotations

import streamlit as st

from lib import data, gemini, insights, ui
from views.components import header_actions, stat_grid

_KEY = "insights_result"
_KEY_META = "insights_meta"


def _trend_sentence(d: dict) -> str:
    now, prev = d["observations_last_14_days"], d["observations_previous_14_days"]
    if not prev:
        return f"{now} observation(s) in the last 14 days, with no earlier period to compare against."
    delta = round((now - prev) / prev * 100)
    if abs(delta) < 5:
        return f"Reporting is level with the previous 14 days ({now} vs {prev})."
    return f"Reporting is {'up' if delta > 0 else 'down'} {abs(delta)}% on the previous 14 days ({now} vs {prev})."


def _card(title: str, body_html: str, key: str) -> None:
    with st.container(key=key):
        st.markdown(f'<div class="sg-h3" style="margin-bottom:.45rem">{ui.esc(title)}</div>{body_html}',
                    unsafe_allow_html=True)


def render() -> None:
    ui.page_header(
        "Site Insights",
        "What the whole register says, not what one photo says.",
        actions=header_actions(False),
    )

    hazards = data.hazards()
    digest = insights.build_digest(hazards)
    n = digest["total_records"]

    if n == 0:
        ui.empty_state("Insights appear once the register has records. Try Settings - Load demo data.", "insights")
        return

    stat_grid([
        ("Confirmed records", n, "fact_check", "blue"),
        ("Still open", sum(v for k, v in digest["by_status"].items() if k != "Closed"), "pending_actions", "amber"),
        ("Overdue actions", len(digest["overdue_actions"]), "alarm", "red"),
        ("Avg. days to close", digest["avg_days_to_close"] or 0, "schedule", "green"),
    ])

    st.markdown(
        ui.callout(
            "The figures above are computed, not generated.",
            "Gemini is given this aggregated digest and asked to interpret it. It never counts, and every "
            "number it quotes can be checked against the register. Recommendations are recommendations: "
            "nothing on this page changes a record.",
            kind="info", icon="function",
        ),
        unsafe_allow_html=True,
    )

    left, right = st.columns([3, 1.4], vertical_alignment="center")
    left.markdown(
        f'<p class="sg-muted" style="margin:.6rem 0 0">{_trend_sentence(digest)} '
        f'{digest["reopened_count"]} record(s) reopened after a rejected closure; '
        f'{digest["uncertain_findings"]} finding(s) the model itself flagged uncertain.</p>',
        unsafe_allow_html=True,
    )
    with right, st.container(key="sg_insights_btn"):
        go = st.button(
            "Generate site insights", icon=":material/auto_awesome:", type="primary",
            width="stretch", disabled=n < insights.MIN_RECORDS,
        )

    if n < insights.MIN_RECORDS:
        st.markdown(
            ui.callout(
                "Not enough records yet",
                f"A register-wide read needs at least {insights.MIN_RECORDS} confirmed records. "
                f"There {'is' if n == 1 else 'are'} {n}. Add observations, or load the demo data from Settings.",
                kind="warn", icon="info",
            ),
            unsafe_allow_html=True,
        )
        return

    if go:
        try:
            with st.spinner("SiteGuard AI is reading the whole register..."):
                st.session_state[_KEY] = gemini.analyze_site_insights(insights.digest_text(digest), n)
                st.session_state[_KEY_META] = {"at": ui.now_local().isoformat(timespec="minutes"), "n": n}
        except Exception as exc:  # noqa: BLE001 - surfaced to the reviewer, never swallowed
            st.session_state[_KEY] = None
            st.markdown(
                ui.callout(
                    "Gemini could not be reached",
                    f"{ui.esc(str(exc)[:220])} The figures above are unaffected -- they are computed in the app, "
                    "not by the model. Try again in a moment.",
                    kind="warn", icon="error",
                ),
                unsafe_allow_html=True,
            )

    result = st.session_state.get(_KEY)
    if not result:
        st.markdown(
            '<div class="sg-empty"><span class="material-symbols-rounded">auto_awesome</span>'
            '<p>Generate a briefing to see recurring patterns, where corrective work is slipping, '
            'and what to focus on next.</p></div>',
            unsafe_allow_html=True,
        )
        return

    meta = st.session_state.get(_KEY_META, {})
    conf_ok = result.confidence == "confirmed"
    st.markdown(
        f'<div class="sg-findings-h"><span class="material-symbols-rounded">auto_awesome</span>'
        f'Gemini briefing {ui.pill("Confirmed" if conf_ok else "Inconclusive", "green" if conf_ok else "amber")}'
        f'</div><p class="sg-small">{gemini.MODEL_NAME} · read {meta.get("n", n)} records · '
        f'{ui.fmt_dt(meta.get("at"))}</p>',
        unsafe_allow_html=True,
    )
    st.markdown(f'<p style="font-size:1.08rem;font-weight:600;margin:.3rem 0 .9rem">{ui.esc(result.headline)}</p>',
                unsafe_allow_html=True)

    if result.confidence_note:
        st.markdown(
            ui.callout("Confidence", ui.esc(result.confidence_note),
                       kind="success" if conf_ok else "warn", icon="shield_question"),
            unsafe_allow_html=True,
        )

    if result.focus_areas:
        ui.section("Recommended focus areas")
        cols = st.columns(min(len(result.focus_areas), 2), gap="medium")
        for i, f in enumerate(result.focus_areas):
            owner = f'{ui.pill(f.suggested_owner, "blue")}' if f.suggested_owner else ""
            with cols[i % len(cols)]:
                _card(
                    f.area,
                    f'<p style="font-weight:600;margin:0 0 .35rem">{ui.esc(f.recommendation)}</p>'
                    f'<p class="sg-muted" style="margin:0 0 .5rem">{ui.esc(f.rationale)}</p>{owner}',
                    key=f"card_focus_{i}",
                )

    if result.recurring_patterns:
        ui.section("Recurring patterns")
        for i, p in enumerate(result.recurring_patterns):
            _card(
                p.pattern,
                f'<p class="sg-muted" style="margin:0 0 .3rem"><b>In the data:</b> {ui.esc(p.evidence)}</p>'
                f'<p class="sg-muted" style="margin:0"><b>Why it matters:</b> {ui.esc(p.why_it_matters)}</p>',
                key=f"card_pattern_{i}",
            )

    c1, c2 = st.columns(2, gap="large")
    if result.accountability:
        with c1, st.container(key="card_insight_acct"):
            ui.section("Where work is slipping")
            st.markdown("".join(f'<p class="sg-muted" style="margin:.2rem 0">• {ui.esc(a)}</p>'
                                for a in result.accountability), unsafe_allow_html=True)
    if result.blind_spots:
        with c2, st.container(key="card_insight_blind"):
            ui.section("What this register cannot tell you")
            st.markdown("".join(f'<p class="sg-muted" style="margin:.2rem 0">• {ui.esc(b)}</p>'
                                for b in result.blind_spots), unsafe_allow_html=True)

    st.markdown(
        ui.callout(
            "A briefing, not a decision",
            "Nothing here has changed a record. Acting on a focus area means opening the hazards behind it "
            "and assigning the work, with a reviewer's name on each change.",
            kind="info", icon="how_to_reg",
        ),
        unsafe_allow_html=True,
    )
