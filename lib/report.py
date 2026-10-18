"""Self-contained HTML hazard report (opens in any browser, prints to PDF)."""

from __future__ import annotations

import csv
import io
from typing import Any

from . import ui
from .schema import SCENARIO_LABELS


def hazard_report_html(h: dict[str, Any]) -> str:
    e = ui.esc
    risk = h.get("risk") or {}
    action = h.get("action") or {}
    finding = h.get("ai_finding") or {}
    followups = h.get("followups") or []
    latest = followups[-1] if followups else {}
    comp = latest.get("ai_comparison") or {}
    before = ui.img_src(h.get("source_photo_url"), 900)
    after = ui.img_src(latest.get("photo_url"), 900) if latest else ""

    def row(k: str, v: str) -> str:
        return f"<tr><th>{e(k)}</th><td>{v}</td></tr>"

    hist = "".join(
        f"<tr><td>{e(ui.fmt_dt(x.get('timestamp')))}</td><td>{e(x.get('actor'))}</td>"
        f"<td>{e(x.get('event', '').replace('_', ' '))}</td><td>{e(x.get('note'))}</td></tr>"
        for x in h.get("history", [])
    )
    imgs = ""
    if before:
        imgs += f'<figure><img src="{before}"><figcaption>Before - {e(ui.fmt_date(h.get("date")))}</figcaption></figure>'
    if after:
        imgs += f'<figure><img src="{after}"><figcaption>After - {e(ui.fmt_dt(latest.get("timestamp")))}</figcaption></figure>'

    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>{e(ui.hazard_ref(h))} - {e(ui.hazard_title(h))}</title>
<style>
 body{{font-family:Inter,Segoe UI,Arial,sans-serif;color:#0F1B2D;max-width:900px;margin:32px auto;padding:0 20px}}
 header{{display:flex;justify-content:space-between;align-items:center;border-bottom:3px solid #0A6CFF;padding-bottom:12px}}
 h1{{font-size:22px;margin:0}} h2{{font-size:16px;margin:26px 0 8px;color:#0A6CFF}}
 .brand{{font-weight:800;letter-spacing:.04em}} .brand span{{color:#18B4F5}}
 table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{text-align:left;padding:7px 8px;border-bottom:1px solid #E3E8F0;vertical-align:top}}
 th{{width:32%;color:#5B6B80;font-weight:600}} .imgs{{display:flex;gap:14px}} figure{{margin:0;flex:1}}
 img{{width:100%;height:260px;object-fit:cover;border-radius:10px}} figcaption{{font-size:12px;color:#5B6B80;margin-top:4px}}
 .note{{background:#EAF2FF;color:#1849A9;padding:10px 12px;border-radius:8px;font-size:12px;margin-top:22px}}
 @media print{{body{{margin:0}}}}
</style></head><body>
<header><div><div class="brand">SAFEGUARD <span>AI</span></div><div style="font-size:12px;color:#5B6B80">Ceylon Innvoai - Hazard record report</div></div>
<div style="text-align:right"><h1>{e(ui.hazard_ref(h))}</h1><div style="font-size:12px">Status: <b>{e(ui.status_label(h))}</b></div></div></header>
<h2>{e(ui.hazard_title(h))}</h2>
<table>
{row("Category", e(SCENARIO_LABELS.get(h.get("scenario", ""), h.get("scenario", ""))))}
{row("Location", e(h.get("site")))}
{row("Observed", e(ui.fmt_dt(h.get("observed_at")) if h.get("observed_at") else ui.fmt_date(h.get("date"))))}
{row("Activity", e(h.get("activity") or "-"))}
{row("Reported by", e(h.get("created_by", "-")))}
{row("Description", e(finding.get("description")))}
{row("Risk", e(f"{risk.get('level')} (likelihood {risk.get('likelihood')} x severity {risk.get('severity')} = {risk.get('score')})"))}
{row("AI confidence", e(("Confirmed" if finding.get("confidence") == "confirmed" else "Inconclusive") + (f" ({finding.get('confidence_score')}%)" if finding.get("confidence_score") else "")))}
{row("People exposed", e(h.get("people_exposed") or "-"))}
{row("Tags", e(", ".join(h.get("tags") or []) or "-"))}
</table>
<h2>Corrective action</h2>
<table>
{row("Action", e(action.get("description", "-")))}
{row("Assigned to", e(action.get("owner", "-")))}
{row("Priority", e(action.get("priority") or h.get("priority") or "-"))}
{row("Target date", e(ui.fmt_date(action.get("due_date"))))}
{row("Escalation", e(action.get("escalation_rule") or "-"))}
</table>
<h2>Evidence</h2><div class="imgs">{imgs or "<p>No images.</p>"}</div>
{"<h2>AI verification summary</h2><table>" + row("Comparison", e(comp.get("comparison"))) + row("Reasoning", e(comp.get("reasoning"))) + row("Reviewer note", e(latest.get("note") or "-")) + row("Reviewer decision", e(latest.get("reviewer_decision") or "pending")) + "</table>" if comp else ""}
<h2>Closure</h2><table>
{row("Closed by", e(h.get("closed_by", "-")))}
{row("Closed on", e(ui.fmt_dt(h.get("closed_at"))))}
</table>
<h2>Audit trail</h2><table><tr><th style="width:24%">When</th><th style="width:18%">Who</th><th style="width:20%">Event</th><th>Note</th></tr>{hist}</table>
<p class="note">AI findings are proposals that support the reviewer's assessment. Every state change in this record was approved by a person.
Generated {e(ui.now_local().strftime("%d %b %Y, %I:%M %p"))}.</p>
</body></html>"""


def register_csv(hazards: list[dict[str, Any]]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["ID", "Title", "Category", "Location", "Date", "Status", "Risk", "Score", "Owner", "Due", "Priority",
                "Closed by", "Closed on", "Description"])
    for h in hazards:
        a = h.get("action") or {}
        r = h.get("risk") or {}
        w.writerow([ui.hazard_ref(h), ui.hazard_title(h), SCENARIO_LABELS.get(h.get("scenario", ""), ""), h.get("site", ""),
                    h.get("date", ""), ui.status_label(h), r.get("level", ""), r.get("score", ""), a.get("owner", ""),
                    a.get("due_date", ""), a.get("priority") or h.get("priority", ""), h.get("closed_by", ""),
                    (h.get("closed_at") or "")[:16], (h.get("ai_finding") or {}).get("description", "")])
    return buf.getvalue().encode("utf-8-sig")
