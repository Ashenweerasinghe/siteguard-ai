"""Cached reads shared by all pages. The cache key includes store.version(), so
any write in this process refreshes it immediately; the TTL picks up writes made
by other Cloud Run instances."""

from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from . import store


@st.cache_data(show_spinner=False, ttl=60)
def _all(version: int, backend_name: str) -> list[dict[str, Any]]:
    return store.list_hazards()


def hazards() -> list[dict[str, Any]]:
    return _all(store.version(), store.backend_name())


def hazard(hazard_id: str) -> Optional[dict[str, Any]]:
    return store.get_hazard(hazard_id)
