"""Local JSON-file backend (SITEGUARD_BACKEND=local, or automatic fallback).

Same primitives as FirestoreBackend, so the app runs with no Google Cloud
project at all -- handy for offline demos and for UI development. Data lives in
./data/ (git-ignored). Single-process prototype storage, not for production.
"""

from __future__ import annotations

import copy
import json
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

import requests

ROOT = Path(__file__).resolve().parent.parent / "data"
DB_FILE = ROOT / "hazards.json"
EVIDENCE_DIR = ROOT / "evidence"
LOCAL_PREFIX = "local:"

_lock = threading.Lock()


class LocalBackend:
    name = "Local demo storage"

    def __init__(self) -> None:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        if not DB_FILE.exists():
            self._write({"hazards": {}, "prefs": {}})

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(DB_FILE.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {"hazards": {}, "prefs": {}}

    def _write(self, data: dict[str, Any]) -> None:
        tmp = DB_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(DB_FILE)

    # ---- evidence -------------------------------------------------------
    def upload_evidence(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        name = f"{uuid.uuid4().hex}.{ext}"
        (EVIDENCE_DIR / name).write_bytes(file_bytes)
        return f"{LOCAL_PREFIX}{name}"

    def read_evidence(self, url: str) -> bytes:
        if url.startswith(LOCAL_PREFIX):
            return (EVIDENCE_DIR / url[len(LOCAL_PREFIX):]).read_bytes()
        return requests.get(url, timeout=30).content

    # ---- hazards --------------------------------------------------------
    def create(self, data: dict[str, Any]) -> str:
        with _lock:
            db = self._read()
            hazard_id = uuid.uuid4().hex[:20]
            db["hazards"][hazard_id] = copy.deepcopy(data)
            self._write(db)
        return hazard_id

    def get(self, hazard_id: str) -> Optional[dict[str, Any]]:
        data = self._read()["hazards"].get(hazard_id)
        if data is None:
            return None
        data = copy.deepcopy(data)
        data["id"] = hazard_id
        return data

    def list(self, scenario: Optional[str] = None) -> list[dict[str, Any]]:
        out = []
        for hid, data in self._read()["hazards"].items():
            if scenario and data.get("scenario") != scenario:
                continue
            item = copy.deepcopy(data)
            item["id"] = hid
            out.append(item)
        return out

    def update(self, hazard_id: str, updates: dict[str, Any]) -> None:
        with _lock:
            db = self._read()
            db["hazards"][hazard_id].update(copy.deepcopy(updates))
            self._write(db)

    def append(self, hazard_id: str, field: str, item: dict[str, Any]) -> None:
        with _lock:
            db = self._read()
            db["hazards"][hazard_id].setdefault(field, []).append(copy.deepcopy(item))
            self._write(db)

    # ---- per-user preferences --------------------------------------------
    def get_pref(self, user: str, key: str, default: Any = None) -> Any:
        return self._read().get("prefs", {}).get(user, {}).get(key, default)

    def set_pref(self, user: str, key: str, value: Any) -> None:
        with _lock:
            db = self._read()
            db.setdefault("prefs", {}).setdefault(user, {})[key] = value
            self._write(db)
