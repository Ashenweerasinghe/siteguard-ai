"""Firestore + Cloud Storage backend for SafeGuard AI.

Only storage primitives live here; the hazard workflow rules (who can move a
hazard to which state, what gets written to history) live in lib/store.py so the
local demo backend behaves identically.
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Optional

import requests
from google.cloud import firestore, storage

HAZARDS_COLLECTION = "hazards"
PREFS_COLLECTION = "user_prefs"


class FirestoreBackend:
    name = "Firestore"

    def __init__(self) -> None:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.db = firestore.Client(project=project) if project else firestore.Client()
        self._bucket = None

    # ---- evidence -------------------------------------------------------
    def _get_bucket(self):
        if self._bucket is None:
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            bucket_name = os.environ.get("GCS_BUCKET")
            if not bucket_name:
                raise RuntimeError("GCS_BUCKET is not set. Add it to your .env file.")
            client = storage.Client(project=project) if project else storage.Client()
            self._bucket = client.bucket(bucket_name)
        return self._bucket

    def upload_evidence(self, file_bytes: bytes, filename: str, content_type: str) -> str:
        """Upload a photo/audio file to Cloud Storage, return its public URL."""
        bucket = self._get_bucket()
        ext = filename.rsplit(".", 1)[-1] if "." in filename else "bin"
        blob_path = f"evidence/{uuid.uuid4().hex}.{ext}"
        blob = bucket.blob(blob_path)
        blob.upload_from_string(file_bytes, content_type=content_type)
        return f"https://storage.googleapis.com/{bucket.name}/{blob_path}"

    def read_evidence(self, url: str) -> bytes:
        return requests.get(url, timeout=30).content

    # ---- hazards --------------------------------------------------------
    def create(self, data: dict[str, Any]) -> str:
        doc_ref = self.db.collection(HAZARDS_COLLECTION).document()
        doc_ref.set(data)
        return doc_ref.id

    def get(self, hazard_id: str) -> Optional[dict[str, Any]]:
        snap = self.db.collection(HAZARDS_COLLECTION).document(hazard_id).get()
        if not snap.exists:
            return None
        data = snap.to_dict()
        data["id"] = snap.id
        return data

    def list(self, scenario: Optional[str] = None) -> list[dict[str, Any]]:
        query = self.db.collection(HAZARDS_COLLECTION)
        if scenario:
            query = query.where("scenario", "==", scenario)
        results = []
        for d in query.stream():
            data = d.to_dict()
            data["id"] = d.id
            results.append(data)
        return results

    def update(self, hazard_id: str, updates: dict[str, Any]) -> None:
        self.db.collection(HAZARDS_COLLECTION).document(hazard_id).update(updates)

    def append(self, hazard_id: str, field: str, item: dict[str, Any]) -> None:
        self.db.collection(HAZARDS_COLLECTION).document(hazard_id).update({field: firestore.ArrayUnion([item])})

    # ---- per-user preferences (notification read state) ------------------
    def get_pref(self, user: str, key: str, default: Any = None) -> Any:
        snap = self.db.collection(PREFS_COLLECTION).document(user).get()
        return (snap.to_dict() or {}).get(key, default) if snap.exists else default

    def set_pref(self, user: str, key: str, value: Any) -> None:
        self.db.collection(PREFS_COLLECTION).document(user).set({key: value}, merge=True)
