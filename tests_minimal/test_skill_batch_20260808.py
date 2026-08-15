"""Regression checks for batch Skill archive uploads."""

import io
import sys
import zipfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


def test_skill_batch_upload_route_accepts_post():
    from app.main import app

    route = next(route for route in app.routes if getattr(route, "path", None) == "/api/skills/batch-upload")
    assert "POST" in route.methods


def test_skill_archive_larger_than_20mb_is_accepted(tmp_path):
    from app.services.skill_service import safe_extract_zip

    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.writestr("large/SKILL.md", "---\nname: large\ndescription: large archive\n---\n")
        archive.writestr("large/assets/reference.bin", b"x" * (21 * 1024 * 1024))

    extracted = safe_extract_zip(payload.getvalue(), tmp_path)
    assert tmp_path / "large" / "SKILL.md" in extracted
