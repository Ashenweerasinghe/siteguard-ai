"""SiteGuard AI design system: theme CSS, brand, pills, cards and formatting helpers.

Visual language follows the Ceylon InnovAI design: navy sidebar, white cards on a
cool-grey canvas, blue->cyan gradient primary buttons, soft coloured status pills.

Alignment rule used everywhere: thumbnails are rendered with a fixed box and
object-fit: cover (never at their natural aspect ratio), and list rows use
st.columns(..., vertical_alignment="center"), so rows and cards line up no matter
what photo a reviewer uploads.
"""

from __future__ import annotations

import base64
import datetime as dt
import html
import io
import os
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import streamlit as st

from . import store
from .schema import RISK_COLOR, SCENARIO_LABELS, STATUS_LABELS, STATUS_PILL_COLOR

ASSETS = Path(__file__).resolve().parent.parent / "assets"
BRAND = ASSETS / "brand"
TZ = ZoneInfo(os.environ.get("SITEGUARD_TZ", "Asia/Colombo"))

PILL = {
    "red": ("#FDECEC", "#C8231A"),
    "amber": ("#FFF3DF", "#B54708"),
    "green": ("#E6F7EE", "#067647"),
    "blue": ("#E8F1FF", "#175CD3"),
    "violet": ("#F1EBFF", "#6941C6"),
    "gray": ("#EEF1F5", "#475467"),
}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def esc(text) -> str:
    return html.escape(str(text if text is not None else ""))


def req(label: str) -> str:
    """Label for a mandatory field: adds a red star (Streamlit markdown colour)."""
    return f"{label} :red[\\*]"


def required_legend() -> None:
    st.markdown('<p class="sg-legend"><span class="sg-star">*</span> Required field</p>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def _file_b64(path: str) -> str:
    return base64.b64encode(Path(path).read_bytes()).decode()


def asset_uri(name: str) -> str:
    path = BRAND / name
    mime = "image/png" if name.endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{_file_b64(str(path))}"


@st.cache_data(show_spinner=False, max_entries=512)
def _thumb_uri(url: str, max_px: int) -> str:
    from PIL import Image

    raw = store.read_evidence(url)
    im = Image.open(io.BytesIO(raw)).convert("RGB")
    im.thumbnail((max_px, max_px))
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def img_src(url: Optional[str], max_px: int = 480) -> str:
    """Browser-usable src for an evidence URL (public GCS URL or local file)."""
    if not url:
        return ""
    if url.startswith("http"):
        return url
    try:
        return _thumb_uri(url, max_px)
    except Exception:
        return ""


def bytes_uri(data: bytes, mime: str = "image/jpeg") -> str:
    return f"data:{mime};base64," + base64.b64encode(data).decode()


def thumb(url: Optional[str], w: int | str = 88, h: int = 66, radius: int = 10, src: Optional[str] = None) -> str:
    """Fixed-size cover thumbnail. Width may be a CSS string such as '100%'."""
    width = f"{w}px" if isinstance(w, int) else w
    s = src or img_src(url, max_px=max(h * 3, 240))
    if not s:
        return (
            f'<div class="sg-thumb sg-thumb-empty" style="width:{width};height:{h}px;border-radius:{radius}px">'
            '<span class="material-symbols-rounded">image</span></div>'
        )
    return f'<img class="sg-thumb" src="{s}" style="width:{width};height:{h}px;border-radius:{radius}px;object-fit:cover" alt="evidence">'


def pill(text: str, color: str = "gray", dot: bool = False) -> str:
    bg, fg = PILL.get(color, PILL["gray"])
    d = f'<span class="sg-dot" style="background:{fg}"></span>' if dot else ""
    return f'<span class="sg-pill" style="background:{bg};color:{fg}">{d}{esc(text)}</span>'


def risk_pill(level: Optional[str]) -> str:
    level = level or "n/a"
    return pill(level, RISK_COLOR.get(level, "gray"), dot=True)


def status_label(h: dict) -> str:
    if h.get("status") == "closed" and h.get("rejected"):
        return "Rejected"
    return STATUS_LABELS.get(h.get("status", ""), h.get("status", ""))


def status_pill(h: dict) -> str:
    color = "gray" if h.get("rejected") else STATUS_PILL_COLOR.get(h.get("status", ""), "gray")
    return pill(status_label(h), color)


def hazard_title(h: dict) -> str:
    return h.get("title") or SCENARIO_LABELS.get(h.get("scenario", ""), "Observation")


def hazard_ref(h: dict) -> str:
    return h.get("ref") or f"SG-{(h.get('date') or '0000')[:4]}-{h.get('id', '')[:5].upper()}"


def category_label(scenario: str) -> str:
    return SCENARIO_LABELS.get(scenario, scenario)


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------
def now_local() -> dt.datetime:
    return dt.datetime.now(TZ)


def parse_iso(value: Optional[str]) -> Optional[dt.datetime]:
    if not value:
        return None
    try:
        d = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=TZ)
    return d.astimezone(TZ)


def fmt_date(value: Optional[str]) -> str:
    if not value:
        return "-"
    try:
        return dt.date.fromisoformat(str(value)[:10]).strftime("%d %b %Y")
    except ValueError:
        return str(value)


def fmt_dt(value: Optional[str]) -> str:
    d = parse_iso(value)
    return d.strftime("%d %b %Y, %I:%M %p") if d else "-"


def rel_time(value: Optional[str]) -> str:
    d = parse_iso(value)
    if not d:
        return ""
    secs = (now_local() - d).total_seconds()
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{int(secs // 60)} min ago"
    if secs < 86400:
        return f"{int(secs // 3600)} h ago"
    if secs < 86400 * 7:
        days = int(secs // 86400)
        return "yesterday" if days == 1 else f"{days} days ago"
    return d.strftime("%d %b %Y")


def greeting() -> str:
    hour = now_local().hour
    return "Good morning" if hour < 12 else "Good afternoon" if hour < 17 else "Good evening"


def due_state(due: Optional[str]) -> str:
    """'overdue' | 'soon' (within 2 days) | 'ok' | ''"""
    if not due:
        return ""
    try:
        days = (dt.date.fromisoformat(due[:10]) - now_local().date()).days
    except ValueError:
        return ""
    return "overdue" if days < 0 else "soon" if days <= 2 else "ok"


# ---------------------------------------------------------------------------
# Layout pieces
# ---------------------------------------------------------------------------
def brand(compact: bool = False, dark: bool = True) -> str:
    cls = "sg-brand sg-brand-compact" if compact else "sg-brand"
    tone = "" if dark else " sg-brand-light"
    tagline = "" if compact else '<div class="sg-brand-tag">REAL PROBLEMS. SMARTER SOLUTIONS.</div><div class="sg-brand-sub">SRI LANKA</div>'
    return (
        f'<div class="{cls}{tone}"><img src="{asset_uri("logo_head.png")}" alt="Ceylon InnovAI logo">'
        f'<div><div class="sg-brand-name">CEYLON <span>INNOVAI</span></div>{tagline}</div></div>'
    )


def page_header(title: str, subtitle: str = "", eyebrow: str = "", actions=None) -> None:
    """Title block on the left, optional action widgets (callable) on the right."""
    left, right = st.columns([5, 2], vertical_alignment="center")
    with left:
        eb = f'<div class="sg-eyebrow">{esc(eyebrow)}</div>' if eyebrow else ""
        sub = f'<p class="sg-subtitle">{esc(subtitle)}</p>' if subtitle else ""
        st.markdown(f'<div class="sg-header">{eb}<div class="sg-h1">{esc(title)}</div>{sub}</div>', unsafe_allow_html=True)
    with right:
        if actions:
            with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center"):
                actions()


def section(title: str, right_html: str = "") -> None:
    st.markdown(
        f'<div class="sg-section"><div class="sg-h3">{esc(title)}</div>{right_html}</div>',
        unsafe_allow_html=True,
    )


def stepper(steps: list[str], current: int) -> None:
    items = []
    for i, label in enumerate(steps, start=1):
        state = "done" if i < current else "active" if i == current else "todo"
        mark = '<span class="material-symbols-rounded">check</span>' if state == "done" else str(i)
        items.append(f'<div class="sg-step sg-step-{state}"><span class="sg-step-num">{mark}</span><span>{esc(label)}</span></div>')
    st.markdown(f'<div class="sg-stepper">{"<div class=sg-step-line></div>".join(items)}</div>', unsafe_allow_html=True)


def kv_rows(rows: list[tuple[str, str]]) -> str:
    """Two-column definition table (label / value-html) used on the AI result."""
    body = "".join(f'<div class="sg-kv-k">{esc(k)}</div><div class="sg-kv-v">{v}</div>' for k, v in rows)
    return f'<div class="sg-kv">{body}</div>'


def callout(title: str, body: str, kind: str = "info", icon: str = "info") -> str:
    return (
        f'<div class="sg-callout sg-callout-{kind}"><span class="material-symbols-rounded">{icon}</span>'
        f'<div><strong>{esc(title)}</strong><p>{body}</p></div></div>'
    )


def empty_state(text: str, icon: str = "inbox") -> None:
    st.markdown(
        f'<div class="sg-empty"><span class="material-symbols-rounded">{icon}</span><p>{esc(text)}</p></div>',
        unsafe_allow_html=True,
    )


def demo_badges() -> str:
    from . import gemini

    out = []
    if store.is_local():
        out.append(pill("Local demo storage", "gray"))
    if gemini.mock_enabled():
        out.append(pill("Demo AI (mock)", "violet"))
    return " ".join(out)


# ---------------------------------------------------------------------------
# Theme CSS
# ---------------------------------------------------------------------------
def inject_css() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


def hide_sidebar() -> None:
    st.markdown(
        """<style>
        section[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
        [data-testid="stExpandSidebarButton"], header[data-testid="stHeader"] { display:none !important; }
        .block-container, [data-testid="stMainBlockContainer"] { padding-top: 1.5rem !important; max-width: 1180px; }
        </style>""",
        unsafe_allow_html=True,
    )


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,400,0..1,0&display=swap');

:root {
  --sg-navy: #0B1A2C; --sg-navy-2: #10243B; --sg-blue: #0A6CFF; --sg-cyan: #18B4F5;
  --sg-bg: #F4F7FB; --sg-card: #FFFFFF; --sg-line: #E3E8F0; --sg-text: #0F1B2D; --sg-muted: #5B6B80;
  --sg-grad: linear-gradient(90deg, #0A6CFF 0%, #18B4F5 100%);
  --sg-shadow: 0 1px 2px rgba(16,36,59,.05), 0 4px 16px rgba(16,36,59,.06);
}
html, body, [class*="css"], .stApp, button, input, textarea, select { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: var(--sg-bg); }
.material-symbols-rounded { font-family: 'Material Symbols Rounded'; font-weight: normal; font-style: normal;
  font-size: 20px; line-height: 1; display: inline-block; vertical-align: middle; -webkit-font-smoothing: antialiased; }
header[data-testid="stHeader"] { background: transparent; }
.block-container, [data-testid="stMainBlockContainer"] { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1280px; }

/* ---------- Sidebar ---------- */
section[data-testid="stSidebar"] { background: linear-gradient(180deg, var(--sg-navy) 0%, var(--sg-navy-2) 100%); border-right: 0; }
section[data-testid="stSidebar"] * { color: #C9D6E8; }
section[data-testid="stSidebar"] [data-testid="stSidebarContent"] { padding-top: .25rem; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.08); margin: .6rem 0; }
.st-key-sg_nav button, .st-key-sg_nav_bottom button {
  width: 100%; justify-content: flex-start; background: transparent; border: 0; color: #C9D6E8;
  padding: .55rem .8rem; border-radius: 10px; min-height: 0; font-weight: 500; box-shadow: none;
}
.st-key-sg_nav button p, .st-key-sg_nav_bottom button p { font-size: .92rem; }
.st-key-sg_nav button:hover, .st-key-sg_nav_bottom button:hover { background: rgba(255,255,255,.06); color: #fff; }
.st-key-sg_nav button[kind="primary"], .st-key-sg_nav [data-testid^="stBaseButton-primary"] {
  background: linear-gradient(90deg, rgba(10,108,255,.95), rgba(24,180,245,.75)); color: #fff;
}
.st-key-sg_nav [data-testid^="stBaseButton-primary"] * { color: #fff !important; }
.st-key-sg_nav_bottom [data-testid^="stBaseButton-primary"] { background: linear-gradient(90deg, rgba(10,108,255,.95), rgba(24,180,245,.75)); color:#fff; }
.st-key-sg_nav_bottom [data-testid^="stBaseButton-primary"] * { color: #fff !important; }
.st-key-sg_nav [data-testid="stVerticalBlock"], .st-key-sg_nav_bottom [data-testid="stVerticalBlock"] { gap: .2rem; }
.sg-user { display:flex; align-items:center; gap:.7rem; padding:.7rem .6rem; border-radius:12px; background: rgba(255,255,255,.05); }
.sg-avatar { width:38px; height:38px; border-radius:50%; background: var(--sg-grad); color:#fff !important;
  display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.85rem; flex-shrink:0; }
.sg-user-name { color:#fff !important; font-weight:600; font-size:.88rem; line-height:1.2; }
.sg-user-role { font-size:.76rem; opacity:.75; }
.sg-side-foot { font-size:.72rem; opacity:.6; padding:.2rem .6rem; }

/* ---------- Brand ---------- */
.sg-brand { display:flex; align-items:center; gap:.7rem; padding:.4rem .2rem .9rem; }
.sg-brand img { width:58px; height:auto; filter: drop-shadow(0 0 10px rgba(24,180,245,.35)); }
.sg-brand-compact img { width:44px; }
.sg-brand-name { color:#fff !important; font-weight:700; letter-spacing:.04em; font-size:1.06rem; line-height:1.1; }
.sg-brand-name span { color:#22C3F7 !important; }
.sg-brand-compact .sg-brand-name { font-size:.95rem; }
.sg-brand-tag { color:#DCE7F5 !important; font-size:.62rem; letter-spacing:.06em; margin-top:.2rem; }
.sg-brand-sub { color:#8FA6C2 !important; font-size:.58rem; letter-spacing:.2em; text-align:right; }

/* ---------- Headers ---------- */
.sg-h1 { font-size: 1.65rem; font-weight: 800; color: var(--sg-text); margin: 0; padding: 0; letter-spacing: -.01em; }
.sg-eyebrow { color: var(--sg-muted); font-size: .95rem; margin-bottom: .1rem; }
.sg-subtitle { color: var(--sg-muted); margin: .25rem 0 0; font-size: .95rem; }
.sg-section { display:flex; align-items:center; justify-content:space-between; margin: .2rem 0 .5rem; }
.sg-h3 { font-size: 1.05rem; font-weight: 700; margin: 0; padding: 0; color: var(--sg-text); }
.sg-legend { color: var(--sg-muted); font-size: .8rem; margin: 0; }
.sg-star { color: #E5484D; font-weight: 700; }
.sg-muted { color: var(--sg-muted); font-size: .86rem; }
.sg-small { font-size: .8rem; color: var(--sg-muted); }

/* ---------- Cards / containers ---------- */
[class*="st-key-card_"] { background: var(--sg-card); border-radius: 16px !important;
  border: 1px solid var(--sg-line) !important; box-shadow: var(--sg-shadow); padding: 1.1rem 1.2rem !important; }
[class*="st-key-row_"] { background: var(--sg-card); border: 1px solid var(--sg-line) !important; border-radius: 14px !important;
  padding: .7rem .9rem !important; box-shadow: 0 1px 2px rgba(16,36,59,.04); transition: border-color .15s, box-shadow .15s; }
[class*="st-key-row_"]:hover { border-color: #BCD3F5 !important; box-shadow: var(--sg-shadow); }

/* ---------- Pills, thumbs ---------- */
.sg-pill { display:inline-flex; align-items:center; gap:.35rem; padding: 3px 10px; border-radius: 999px;
  font-size: .76rem; font-weight: 600; white-space: nowrap; line-height: 1.4; }
.sg-dot { width:6px; height:6px; border-radius:50%; display:inline-block; }
.sg-thumb { object-fit: cover !important; display:block; background:#E9EEF5; flex-shrink:0; }
.sg-thumb-empty { display:flex; align-items:center; justify-content:center; color:#98A6B8; }
.sg-row-title { font-weight: 650; color: var(--sg-text); font-size: .95rem; line-height:1.3; margin:0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sg-row-meta { color: var(--sg-muted); font-size: .8rem; margin: .15rem 0 0; display:flex; flex-wrap:wrap; gap:.25rem .8rem; align-items:center; }
.sg-row-meta .material-symbols-rounded { font-size: 15px; margin-right: 2px; }
.sg-row-desc { color: #344256; font-size: .84rem; margin: .3rem 0 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sg-row-right { display:flex; flex-direction:column; align-items:flex-end; gap:.35rem; }
.sg-overdue { color:#C8231A !important; font-weight:600; }
.sg-soon { color:#B54708 !important; font-weight:600; }

/* ---------- Hero ---------- */
.st-key-sg_hero { background: linear-gradient(110deg, #0A3FA8 0%, #0A6CFF 55%, #20B8F5 100%); border-radius: 18px;
  padding: 1.4rem 1.6rem !important; overflow: hidden; box-shadow: 0 8px 24px rgba(10,108,255,.25); position: relative; }
.sg-hero-h { color:#fff; font-size: 1.75rem; font-weight: 800; line-height: 1.15; margin: 0 0 .5rem; padding:0; }
.st-key-sg_hero .sg-hero-p { color: #E3F0FF; margin: 0 0 .9rem; font-size: .95rem; }
.st-key-sg_hero button { background: #fff !important; color: var(--sg-blue) !important; border: 0 !important; border-radius: 999px !important;
  font-weight: 700 !important; padding: .5rem 1.2rem !important; }
.st-key-sg_hero button * { color: var(--sg-blue) !important; }
.sg-hero-img { width:100%; height: 190px; object-fit: cover !important; object-position: center top; border-radius: 14px; display:block; }

/* ---------- Stats ---------- */
.sg-stats { display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: .8rem; margin: .9rem 0 1rem; }
.sg-stat { background: var(--sg-card); border:1px solid var(--sg-line); border-radius: 14px; padding: .85rem 1rem;
  display:flex; align-items:center; gap:.75rem; box-shadow: 0 1px 2px rgba(16,36,59,.04); min-height: 74px; }
.sg-stat-ic { width:38px; height:38px; border-radius: 10px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.sg-stat-n { font-size: 1.45rem; font-weight: 800; color: var(--sg-text); line-height: 1; }
.sg-stat-l { font-size: .78rem; color: var(--sg-muted); margin-top: .2rem; }
@media (max-width: 900px) { .sg-stats { grid-template-columns: repeat(2, minmax(0,1fr)); } }

/* ---------- Stepper ---------- */
.sg-stepper { display:flex; align-items:center; gap:.5rem; background: var(--sg-card); border:1px solid var(--sg-line);
  border-radius: 14px; padding: .7rem 1rem; margin: .6rem 0 1rem; overflow-x:auto; }
.sg-step { display:flex; align-items:center; gap:.5rem; font-size:.86rem; font-weight:600; color: var(--sg-muted); white-space: nowrap; }
.sg-step-num { width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center;
  font-size:.8rem; border:1.5px solid #C5D0DE; background:#fff; }
.sg-step-num .material-symbols-rounded { font-size: 16px; }
.sg-step-active { color: var(--sg-blue); }
.sg-step-active .sg-step-num { background: var(--sg-grad); color:#fff; border:0; }
.sg-step-done { color: #067647; }
.sg-step-done .sg-step-num { background:#E6F7EE; color:#067647; border-color:#A6E3C0; }
.sg-step-line { flex:1; min-width: 18px; height:2px; background: var(--sg-line); border-radius:2px; }

/* ---------- Key/value, callouts ---------- */
.sg-kv { display:grid; grid-template-columns: minmax(130px, 34%) 1fr; border-top:1px solid var(--sg-line); }
.sg-kv-k, .sg-kv-v { padding: .62rem .2rem; border-bottom:1px solid var(--sg-line); font-size:.87rem; }
.sg-kv-k { font-weight: 600; color: var(--sg-text); }
.sg-kv-v { color: #344256; }
.sg-kv-v ul { margin: 0; padding-left: 1.1rem; }
.sg-callout { display:flex; gap:.7rem; border-radius: 12px; padding: .8rem 1rem; margin: .6rem 0; align-items:flex-start; }
.sg-callout p { margin: .15rem 0 0; font-size: .84rem; }
.sg-callout strong { font-size: .9rem; }
.sg-callout-info { background:#EAF2FF; color:#1849A9; }
.sg-callout-success { background:#E9F8EF; color:#05603A; }
.sg-callout-warn { background:#FFF6E5; color:#93370D; }
.sg-findings-h { display:flex; align-items:center; gap:.45rem; background:#E9F8EF; color:#05603A; font-weight:700;
  padding:.55rem .8rem; border-radius:10px; margin: .2rem 0 .4rem; font-size:.92rem; }
.sg-conf { margin-top:.5rem; }
.sg-conf-bar { height:8px; border-radius:99px; background:#E6ECF3; overflow:hidden; margin-top:.3rem; }
.sg-conf-bar > div { height:100%; background: linear-gradient(90deg,#12B76A,#32D583); border-radius:99px; }
.sg-conf-low > div { background: linear-gradient(90deg,#F79009,#FDB022); }

/* ---------- Buttons & inputs ---------- */
[data-testid="stMain"] [data-testid^="stBaseButton-primary"] { background: var(--sg-grad); border: 0; font-weight: 650;
  box-shadow: 0 4px 12px rgba(10,108,255,.22); border-radius: 10px; }
[data-testid="stMain"] [data-testid^="stBaseButton-primary"]:hover { filter: brightness(1.05); }
[data-testid="stMain"] [data-testid="stBaseButton-secondary"] { border-radius: 10px; font-weight: 600; border-color: #D3DCE8; background:#fff; }
[data-testid="stMain"] [data-testid="stBaseButton-tertiary"] { color: var(--sg-blue); font-weight: 600; }
[data-testid="stTextInputRootElement"], [data-baseweb="select"] > div, [data-testid="stDateInputField"],
[data-baseweb="textarea"], [data-baseweb="input"] { border-radius: 10px !important; }
[data-testid="stWidgetLabel"] p { font-weight: 600; font-size: .86rem; color: var(--sg-text); }
[data-testid="stFileUploaderDropzone"] { border-radius: 14px; border: 1.5px dashed #9EC2F7; background: #F6FAFF; }

/* ---------- Timeline, notifications ---------- */
.sg-tl { border-left: 2px solid var(--sg-line); margin-left: .5rem; padding-left: 1.1rem; }
.sg-tl-item { position: relative; padding: 0 0 .9rem; }
.sg-tl-item::before { content:""; position:absolute; left:-1.48rem; top:.3rem; width:10px; height:10px; border-radius:50%;
  background:#fff; border: 2px solid var(--sg-blue); }
.sg-tl-t { font-weight:600; font-size:.88rem; color: var(--sg-text); }
.sg-tl-m { font-size:.8rem; color: var(--sg-muted); }
.sg-nt-ic { width:40px; height:40px; border-radius:12px; display:flex; align-items:center; justify-content:center; }
.sg-unread { width:8px; height:8px; border-radius:50%; background: var(--sg-blue); display:inline-block; margin-left:.35rem; vertical-align: middle; }
.sg-empty { text-align:center; padding: 2.2rem 1rem; color: var(--sg-muted); background: var(--sg-card); border:1px dashed #CDD7E4; border-radius: 14px; }
.sg-empty .material-symbols-rounded { font-size: 36px; color: #9AB0CC; }

/* ---------- Closure ---------- */
.sg-closed-hero { text-align:center; padding: 1rem 0 .4rem; position:relative; }
.sg-closed-check { width:76px; height:76px; border-radius:50%; margin: 0 auto .6rem; background: linear-gradient(135deg,#12B76A,#32D583);
  display:flex; align-items:center; justify-content:center; box-shadow: 0 0 0 10px #E6F7EE; }
.sg-closed-check .material-symbols-rounded { color:#fff; font-size: 44px; }
.sg-closed-h { color: #067647; font-weight: 800; margin: .7rem 0 .1rem; padding: 0; font-size: 1.6rem; }
.sg-confetti { position:absolute; width:8px; height:8px; border-radius:2px; opacity:.85; }

/* ---------- Login ---------- */
.sg-login-brand { position: relative; min-height: 600px; border-radius: 22px; overflow: hidden; padding: 2rem 2.2rem;
  background: radial-gradient(1200px 500px at 0% 0%, #163A63 0%, #0B1A2C 55%, #08131F 100%); color:#fff; }
.sg-login-title { font-size: 2.9rem; font-weight: 800; color: #fff; margin: 2.2rem 0 .3rem; padding:0; letter-spacing:-.01em; }
.sg-login-title span { color: #22C3F7; }
.sg-login-brand .sg-lead { font-size: 1.35rem; color: #9FD8FF; line-height: 1.3; margin: 0 0 1.2rem; }
.sg-login-steps { display:flex; flex-wrap:wrap; gap:.4rem .9rem; color:#E7F0FA; font-weight:600; font-size: 1rem; }
.sg-login-steps span + span { border-left: 1.5px solid #4A6788; padding-left: .9rem; }
.sg-login-helmet { position:absolute; right:-10px; bottom:0; width: 62%; max-width: 420px; border-top-left-radius: 30px;
  -webkit-mask-image: linear-gradient(to left, #000 60%, transparent); mask-image: linear-gradient(to left, #000 60%, transparent); opacity:.95; }
.sg-login-quote { position:absolute; left:2.2rem; bottom:1.6rem; color:#D7E4F3; font-style: italic; font-size:.95rem; max-width: 45%; }
.st-key-sg_login_card { background: #FFFFFF; border:1px solid var(--sg-line); border-radius: 20px; padding: 1.8rem 1.8rem 1.4rem !important;
  box-shadow: 0 12px 40px rgba(11,26,44,.10); }
.st-key-sg_login_card [data-testid^="stBaseButton-primary"] { background: var(--sg-grad); border: 0; height: 2.9rem; font-size: 1rem; font-weight: 700; border-radius: 12px; }
.sg-login-h { font-size: 1.5rem; font-weight: 800; margin: 0; padding: 0; color: var(--sg-text); }
@media (max-width: 900px) { .sg-login-brand { min-height: 360px; } .sg-login-helmet { width: 55%; } .sg-login-quote { display:none; } }

/* ---------- Additions ---------- */
.sg-thumb { max-width: 100%; }
.sg-flabel { font-weight: 600; font-size: .86rem; color: var(--sg-text); margin-bottom: .35rem; }
.sg-riskbox { padding: .42rem .2rem; min-height: 2.5rem; display:flex; align-items:center; gap:.4rem; }
.sg-arrow { width: 38px; height: 38px; border-radius: 50%; background: var(--sg-grad); display:flex; align-items:center;
  justify-content:center; box-shadow: 0 4px 12px rgba(10,108,255,.3); }
.sg-arrow .material-symbols-rounded { color: #fff; }
/* Sidebar nav: left-aligned, compact */
.st-key-sg_nav button > div, .st-key-sg_nav_bottom button > div { justify-content: flex-start !important; width: 100%; }
.st-key-sg_nav [data-testid="stElementContainer"], .st-key-sg_nav_bottom [data-testid="stElementContainer"] { margin: 0 !important; }
.st-key-sg_nav { gap: .15rem !important; }
.st-key-sg_nav_bottom { gap: .35rem !important; }
/* Rows: kill Streamlit's default markdown bottom margin so thumbnails are not clipped */
[class*="st-key-row_"] [data-testid="stMarkdownContainer"] p:last-child { margin-bottom: 0; }
[class*="st-key-row_"] [data-testid="stMarkdown"], [class*="st-key-row_"] .stMarkdown { margin-bottom: 0 !important; }
[class*="st-key-row_"] [data-testid="stPopover"] button { border: 0; background: transparent; box-shadow: none; padding: .2rem .4rem; min-height: 0; }
.st-key-sg_bell button { border-radius: 999px !important; background:#fff !important; border:1px solid var(--sg-line) !important;
  min-height: 2.3rem; padding: .2rem .75rem !important; box-shadow: 0 1px 2px rgba(16,36,59,.05); }
.st-key-sg_bell button p { font-weight: 700; color: #C8231A; }
</style>
"""


# ---------------------------------------------------------------------------
# Flash messages (survive a page change / rerun)
# ---------------------------------------------------------------------------
def flash(message: str, kind: str = "success") -> None:
    st.session_state["_flash"] = (message, kind)


def show_flash() -> None:
    item = st.session_state.pop("_flash", None)
    if item:
        msg, kind = item
        icon = {"success": ":material/check_circle:", "info": ":material/info:", "warning": ":material/warning:"}.get(kind)
        st.toast(msg, icon=icon)


def evidence_img(url: Optional[str], height: int = 260, radius: int = 14) -> None:
    """Large evidence photo in a fixed-height frame (keeps side-by-side layouts aligned)."""
    st.markdown(thumb(url, w="100%", h=height, radius=radius, src=img_src(url, 1200) if url else None),
                unsafe_allow_html=True)


def full_image(url: Optional[str]) -> None:
    """Natural-size image (for 'View full image')."""
    if not url:
        return
    if url.startswith("http"):
        st.image(url, width="stretch")
    else:
        try:
            st.image(store.read_evidence(url), width="stretch")
        except Exception:
            st.caption("Image unavailable.")


def req_html(label: str) -> str:
    """HTML version of req() for labels drawn with markdown."""
    return f'<span class="sg-flabel-t">{esc(label)}</span> <span class="sg-star">*</span>'
