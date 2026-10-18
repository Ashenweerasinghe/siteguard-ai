"""Username/password login for SafeGuard AI.

Passwords are stored only as salted PBKDF2-SHA256 hashes. Users come from (first
match wins):
  1. SITEGUARD_USERS env var (JSON)  -- handy for Cloud Run
  2. .streamlit/secrets.toml [users.<username>] tables
  3. the built-in demo accounts below (for the hackathon demo)

Each user: {"name": "...", "role": "...", "password_hash": "pbkdf2$<iter>$<salt_hex>$<hash_hex>"}
Create a hash with:  python scripts/hash_password.py

"Remember me" keeps the user signed in across browser reloads through a signed,
expiring token in the URL (?session=...). Set SITEGUARD_SECRET in production so
tokens can't be forged.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Optional

import streamlit as st

_ITERATIONS = 200_000
_REMEMBER_DAYS = 7
MAX_ATTEMPTS = 5
LOCKOUT_SECONDS = 60

# Demo accounts (hackathon only). Passwords: demo -> Safeguard@123, admin -> Admin@2026
DEMO_USERS: dict[str, dict[str, str]] = {
    "demo": {
        "name": "Demo Reviewer",
        "role": "Safety Officer",
        "password_hash": "pbkdf2$200000$a627d79c8debaca82caf9b9a5af71a06$0d1fc3d28ce91919d937923ad7d0089efaa97e23506311dbcd1e8d93a38f919c",
    },
    "admin": {
        "name": "Site Administrator",
        "role": "Administrator",
        "password_hash": "pbkdf2$200000$03436ab2f34a30e738f18b51679946c7$fdca111ec07dba14010b36338c54d94dbcb0e93fdd11b2b9193ea023ae6dd6b9",
    },
}
DEMO_HINT = "demo / Safeguard@123"


def hash_password(password: str, salt_hex: Optional[str] = None, iterations: int = _ITERATIONS) -> str:
    salt_hex = salt_hex or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), iterations)
    return f"pbkdf2${iterations}${salt_hex}${digest.hex()}"


def _verify_hash(password: str, stored: str) -> bool:
    try:
        scheme, iters, salt_hex, _ = stored.split("$", 3)
        if scheme != "pbkdf2":
            return False
        return hmac.compare_digest(hash_password(password, salt_hex, int(iters)), stored)
    except (ValueError, TypeError):
        return False


@st.cache_resource(show_spinner=False)
def _load_users() -> dict[str, dict[str, str]]:
    raw = os.environ.get("SITEGUARD_USERS")
    if raw:
        try:
            return {k.lower(): v for k, v in json.loads(raw).items()}
        except json.JSONDecodeError:
            pass
    try:
        if "users" in st.secrets:
            return {k.lower(): dict(v) for k, v in st.secrets["users"].items()}
    except Exception:  # no secrets.toml
        pass
    return DEMO_USERS


def using_demo_accounts() -> bool:
    return _load_users() is DEMO_USERS


def verify(username: str, password: str) -> Optional[dict[str, Any]]:
    username = (username or "").strip().lower()
    info = _load_users().get(username)
    if not info or not _verify_hash(password or "", info.get("password_hash", "")):
        return None
    return {"username": username, "name": info.get("name", username), "role": info.get("role", "Reviewer")}


# ---------------------------------------------------------------------------
# Remember-me token
# ---------------------------------------------------------------------------
def _secret() -> bytes:
    return (os.environ.get("SITEGUARD_SECRET") or "safeguard-ai-dev-secret-change-me").encode()


def make_token(username: str) -> str:
    payload = f"{username}|{int(time.time()) + _REMEMBER_DAYS * 86400}"
    sig = hmac.new(_secret(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    return base64.urlsafe_b64encode(f"{payload}|{sig}".encode()).decode()


def read_token(token: str) -> Optional[str]:
    try:
        username, expiry, sig = base64.urlsafe_b64decode(token.encode()).decode().split("|")
    except Exception:
        return None
    expected = hmac.new(_secret(), f"{username}|{expiry}".encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected) or int(expiry) < time.time():
        return None
    return username if username in _load_users() else None


# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
def current_user() -> Optional[dict[str, Any]]:
    return st.session_state.get("user")


def login(user: dict[str, Any], remember: bool) -> None:
    st.session_state["user"] = user
    st.session_state["login_attempts"] = 0
    if remember:
        st.query_params["session"] = make_token(user["username"])


def restore_session() -> None:
    if current_user():
        return
    token = st.query_params.get("session")
    if token:
        username = read_token(token)
        if username:
            info = _load_users()[username]
            st.session_state["user"] = {"username": username, "name": info.get("name", username), "role": info.get("role", "Reviewer")}
        else:
            del st.query_params["session"]


def logout() -> None:
    st.session_state.clear()
    if "session" in st.query_params:
        del st.query_params["session"]
