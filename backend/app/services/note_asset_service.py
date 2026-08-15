"""Materialize legacy inline note images as durable NoteAsset records."""
from __future__ import annotations

import base64
import hashlib
import re
import uuid
from pathlib import Path

from ..cloud_db import table

ASSETS = Path(__file__).resolve().parents[3] / "storage" / "note-assets"
DATA_IMAGE = re.compile(
    r"""(?:src=["'])data:(image/[a-zA-Z0-9.+-]+);base64,([^"'\s>]+)""",
    re.IGNORECASE,
)


def materialize_inline_note_images(note: dict | None, user: dict) -> int:
    """Persist base64 images left by the browser Word importer, once per note."""
    if not note:
        return 0
    matches = list(DATA_IMAGE.finditer(note.get("content") or ""))
    if not matches:
        return 0
    existing = table("note_assets", user).list({"note_id": note["id"]})
    if existing:
        return 0
    user_key = hashlib.sha256(str(user["id"]).encode("utf-8")).hexdigest()[:24]
    target_dir = ASSETS / user_key
    target_dir.mkdir(parents=True, exist_ok=True)
    created = 0
    for index, match in enumerate(matches, 1):
        media_type, encoded = match.groups()
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        if not data or len(data) > 10 * 1024 * 1024:
            continue
        extension = {"image/jpeg": "jpg", "image/svg+xml": "svg"}.get(media_type.lower(), media_type.split("/")[-1])
        filename = f"word-image-{index}.{extension}"
        target = target_dir / f"{uuid.uuid4().hex}-{filename}"
        target.write_bytes(data)
        table("note_assets", user).create({
            "note_id": note["id"], "filename": filename, "media_type": media_type,
            "storage_path": str(target), "source_anchor": f"block-{index}",
            "size_bytes": len(data),
        })
        created += 1
    return created
