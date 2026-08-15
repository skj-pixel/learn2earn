"""DOCX, asset and user skill workspace endpoints."""
from __future__ import annotations

import re
import hashlib
import os
import shutil
import tempfile
import unicodedata
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel

from ..auth import get_current_user, security
from ..cloud_db import table
from ..database import SessionLocal
from ..models import InstalledSkill, NoteAsset
from ..services.docx_service import export_product_docx
from ..services.note_asset_service import materialize_inline_note_images
from ..services.skill_service import (
    discover_skills,
    safe_extract_zip,
    recommend_skill_names,
    filter_installed_for_product_type,
    product_type_ids_for_skill,
)

router = APIRouter(prefix="/api", tags=["workspace"])
STORAGE = Path(__file__).resolve().parents[3] / "storage"
ASSETS = STORAGE / "note-assets"
SKILLS = STORAGE / "skills"
MAX_DOCX_BYTES = 30 * 1024 * 1024
# 预置 Skills 包路径（三级回退，确保换机器也能预置）：
#   1) 环境变量 LEARN2EARN_BUNDLED_SKILLS（部署时可指向任意位置）
#   2) 仓库内置副本 backend/bundled_skills/workbuddy_skills_all.zip（自包含，随仓库走）
#   3) 本地 BaiduSyncdisk 原始副本（开发机兜底）
_BUNDLED_REPO = Path(__file__).resolve().parents[3] / "backend" / "bundled_skills" / "workbuddy_skills_all.zip"
_BUNDLED_EXTERNAL = Path(r"D:\BaiduSyncdisk\15375399884\简历fy项目\知识付费Skills包\workbuddy_skills_all.zip")
def _resolve_bundled_skills() -> Path:
    env_path = os.environ.get("LEARN2EARN_BUNDLED_SKILLS")
    for cand in (env_path, str(_BUNDLED_REPO), str(_BUNDLED_EXTERNAL)):
        if cand and Path(cand).is_file():
            return Path(cand)
    return _BUNDLED_REPO
BUNDLED_SKILLS = _resolve_bundled_skills()
BUNDLED_CATEGORY = "知识付费 Skills 包"


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", Path(name).name)[:180] or "file"


def _user_storage_key(user: dict) -> str:
    """Create a stable cross-platform directory name for local or cloud user IDs."""
    return hashlib.sha256(str(user["id"]).encode("utf-8")).hexdigest()[:24]





@router.post("/notes/{note_id}/images")
async def upload_note_image(note_id: int, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if not table("notes", user).get(note_id):
        raise HTTPException(404, "笔记不存在")
    if not (file.content_type or "").startswith("image/"):
        raise HTTPException(400, "仅支持图片文件")
    data = await file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(413, "图片不能超过 10MB")
    target_dir = ASSETS / _user_storage_key(user)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{uuid.uuid4().hex}-{_safe_name(file.filename or 'image')}"
    target.write_bytes(data)
    return table("note_assets", user).create({
        "note_id": note_id, "filename": file.filename or "image",
        "media_type": file.content_type, "storage_path": str(target),
        "source_anchor": "editor-upload", "size_bytes": len(data),
    })


def _asset_user(
    access_token: str | None = Query(None),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    if not credentials and access_token:
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)
    return get_current_user(credentials)


@router.get("/assets/{asset_id}")
def get_asset(asset_id: int, user: dict = Depends(_asset_user)):
    with SessionLocal() as db:
        asset = db.get(NoteAsset, asset_id)
        if not asset or asset.user_id != user["id"]:
            raise HTTPException(404, "资源不存在")
        if not Path(asset.storage_path).is_file():
            raise HTTPException(404, "资源文件不存在")
        return FileResponse(asset.storage_path, media_type=asset.media_type, filename=asset.filename)

@router.get("/products/{product_id}/source-assets")
def product_source_assets(product_id: int, user: dict = Depends(get_current_user)):
    product = table("products", user).get(product_id)
    if not product:
        raise HTTPException(404, "产品不存在")
    note_id = product.get("note_id")
    if not note_id:
        return []
    materialize_inline_note_images(table("notes", user).get(note_id), user)
    with SessionLocal() as db:
        rows = db.query(NoteAsset).filter(
            NoteAsset.user_id == user["id"], NoteAsset.note_id == note_id,
        ).order_by(NoteAsset.id).all()
        return [row.to_dict() for row in rows if Path(row.storage_path).is_file()]


@router.get("/products/{product_id}/export.docx")
def export_word_product(product_id: int, user: dict = Depends(get_current_user)):
    product = table("products", user).get(product_id)
    if not product:
        raise HTTPException(404, "产品不存在")
    note = table("notes", user).get(product.get("note_id")) if product.get("note_id") else None
    assets = []
    if product.get("note_id"):
        with SessionLocal() as db:
            rows = db.query(NoteAsset).filter(NoteAsset.user_id == user["id"], NoteAsset.note_id == product["note_id"]).order_by(NoteAsset.id).all()
            assets = [{"filename": row.filename, "storage_path": row.storage_path, "source_anchor": row.source_anchor} for row in rows]
    data = export_product_docx(product, note, assets)
    filename = _safe_name(product.get("title", "product")) + ".docx"
    return Response(data, media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


class SkillUpdate(BaseModel):
    enabled: bool | None = None
    category: str | None = None


def _skill_name_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(name or ""))
    return " ".join(normalized.split()).casefold()


def _dedupe_skills(skills: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique = []
    for skill in skills:
        key = _skill_name_key(skill.get("name", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(skill)
    return unique


def seed_bundled_skills(user: dict, category: str = BUNDLED_CATEGORY) -> int:
    """把内置「知识付费 Skills 包」预置进当前用户的技能库（按名称去重，幂等）。

    这样用户首次打开 Skills 仓库或生成产品时，就能直接选用这些 skill，
    而无需手动点击「导入知识付费包」。返回本次实际安装的 skill 数。
    """
    if not BUNDLED_SKILLS.is_file():
        return 0
    root = SKILLS / _user_storage_key(user) / uuid.uuid4().hex
    try:
        safe_extract_zip(BUNDLED_SKILLS.read_bytes(), root)
        discovered = discover_skills(root)
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        return 0
    if not discovered:
        shutil.rmtree(root, ignore_errors=True)
        return 0
    existing = {_skill_name_key(item["name"]) for item in table("installed_skills", user).list()}
    created = 0
    for skill in discovered:
        key = _skill_name_key(skill["name"])
        if key in existing:
            continue
        table("installed_skills", user).create({
            "name": skill["name"], "description": skill["description"],
            "category": category, "instructions": skill["instructions"],
            "storage_path": skill["path"], "enabled": True,
        })
        existing.add(key)
        created += 1
    return created


@router.get("/skills")
def list_skills(
    user: dict = Depends(get_current_user),
    q: str | None = Query(None, description="按名称/描述/分类搜索 skill 的功能"),
    category: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    # GET 必须是无副作用的快速读取。安装、解压和扫描 Skill 包只能由显式安装流程触发，
    # 否则每次搜索都可能在后台生成期间争抢 CPU 与 SQLite，并返回短暂的错误列表。
    skills_table = table("installed_skills", user)
    if hasattr(skills_table, "list_skill_summaries"):
        existing = skills_table.list_skill_summaries(q or "", category)
        q = None
        category = None
    else:
        existing = skills_table.list()
    results = _dedupe_skills(existing)
    if category:
        results = [item for item in results if (item.get("category") or "") == category]
    if q:
        needle = q.strip().lower()
        if needle:
            results = [
                item for item in results
                if needle in (item.get("name") or "").lower()
                or needle in (item.get("description") or "").lower()
                or needle in (item.get("category") or "").lower()
                or needle in (item.get("instructions") or "").lower()
            ]
    if limit is not None:
        results = results[offset:offset + limit]
    elif offset:
        results = results[offset:]
    return [{**item, "product_type_ids": product_type_ids_for_skill(item.get("name", ""), item.get("description", ""))} for item in results]


@router.get("/skills/recommendations")
def skill_recommendations(
    product_type: str = Query(..., description="产品类型键，如 article / ppt / sop"),
    user: dict = Depends(get_current_user),
):
    """按产品类型推荐已安装的技能（F07：产品类型→技能映射）。

    先确保内置「知识付费 Skills 包」已预置，再从已安装技能中筛出与该产品类型
    匹配的 skill，并返回覆盖缺口（推荐技能是否有未安装的）。
    """
    # 复用 list_skills 的预置逻辑：保证 skill 仓库默认不为空
    try:
        existing = table("installed_skills", user).list()
        if not any(item.get("category") == BUNDLED_CATEGORY for item in existing):
            if seed_bundled_skills(user) > 0:
                existing = table("installed_skills", user).list()
    except Exception:
        existing = table("installed_skills", user).list()
    recommended = filter_installed_for_product_type(product_type, existing)
    recommended_names = {s.get("name") for s in recommended}
    missing = [n for n in recommend_skill_names(product_type) if n not in recommended_names]
    return {
        "product_type": product_type,
        "skills": recommended,
        "recommended_total": len(recommend_skill_names(product_type)),
        "matched_total": len(recommended),
        "coverage_gap": bool(missing),
        "missing_skills": missing,
    }


def _install_skill_archive(data: bytes, archive_label: str, category: str, user: dict) -> dict:
    """解压一个 zip 字节流，提取所有 SKILL.md 并入库。返回 {installed, skills, error}。

    🔍 [作用] 2026-08 feat/28：抽出来给单文件 / 多文件 共用，保证批量上传与单文件行为一致
    """
    root = SKILLS / _user_storage_key(user) / uuid.uuid4().hex
    try:
        safe_extract_zip(data, root)
        discovered = discover_skills(root)
    except Exception as exc:
        shutil.rmtree(root, ignore_errors=True)
        return {"installed": 0, "skills": [], "duplicates": [], "error": str(exc), "archive": archive_label}
    if not discovered:
        shutil.rmtree(root, ignore_errors=True)
        return {"installed": 0, "skills": [], "duplicates": [], "error": "压缩包中没有找到 SKILL.md", "archive": archive_label}
    existing = {_skill_name_key(item["name"]) for item in table("installed_skills", user).list()}
    created = []
    duplicates = []
    for skill in discovered:
        key = _skill_name_key(skill["name"])
        if not key or key in existing:
            duplicates.append(skill["name"])
            continue
        created.append(table("installed_skills", user).create({
            "name": skill["name"], "description": skill["description"],
            "category": category[:100], "instructions": skill["instructions"],
            "storage_path": skill["path"], "enabled": True,
        }))
        existing.add(key)
    if not created:
        shutil.rmtree(root, ignore_errors=True)
    return {"installed": len(created), "skills": created, "duplicates": duplicates, "error": None, "archive": archive_label}


@router.post("/skills/upload")
async def upload_skills(file: UploadFile = File(...), category: str = Form("知识产品"), user: dict = Depends(get_current_user)):
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(400, "请上传包含 SKILL.md 的 ZIP 压缩包")
    data = await file.read()
    result = _install_skill_archive(data, file.filename, category, user)
    if result["error"]:
        raise HTTPException(400, result["error"])
    return {"installed": result["installed"], "skills": result["skills"], "duplicates": result["duplicates"]}


# 🔍 [语法] @router.post + List[UploadFile]
# 🔍 [作用] 2026-08 feat/28：批量上传 skill 压缩包（前端可一次选多个 zip）
# 🔍 [陷阱] FastAPI 多文件必须用 `files: List[UploadFile] = File(...)` 显式声明；同一字段名 files
@router.post("/skills/batch-upload")
async def batch_upload_skills(files: list[UploadFile] = File(...), category: str = Form("知识产品"), user: dict = Depends(get_current_user)):
    if not files:
        raise HTTPException(400, "请选择至少一个 .zip 压缩包")
    # 🔍 [作用] 单次批量最多 50 个压缩包，避免上传体积过大或被恶意拖死
    if len(files) > 50:
        raise HTTPException(400, "单次最多批量上传 50 个压缩包，请分批")
    # 🔍 [作用] 过滤掉非 zip 的文件，给出明确错误而不是 500
    valid_files = [f for f in files if f.filename and f.filename.lower().endswith(".zip")]
    invalid = [f.filename for f in files if not (f.filename and f.filename.lower().endswith(".zip"))]
    if not valid_files:
        raise HTTPException(400, f"所选文件均非 .zip 格式：{', '.join(invalid) or '(空)'}")
    total_installed = 0
    all_created: list[dict] = []
    per_archive: list[dict] = []
    failures: list[dict] = []
    duplicates: list[str] = []
    for f in valid_files:
        data = await f.read()
        result = _install_skill_archive(data, f.filename or "(未命名)", category, user)
        per_archive.append({
            "archive": result["archive"],
            "installed": result["installed"],
            "duplicates": result["duplicates"],
            "error": result["error"],
        })
        if result["error"]:
            failures.append({"archive": result["archive"], "error": result["error"]})
        else:
            total_installed += result["installed"]
            all_created.extend(result["skills"])
            duplicates.extend(result["duplicates"])
    return {
        "received": len(valid_files),
        "invalid_filenames": invalid,
        "installed": total_installed,
        "skills": all_created,
        "duplicates": list(dict.fromkeys(duplicates)),
        "per_archive": per_archive,
        "failures": failures,
        "success": len(failures) == 0,
    }


@router.post("/skills/import-bundled")
def import_bundled_skills(user: dict = Depends(get_current_user)):
    if not BUNDLED_SKILLS.is_file():
        raise HTTPException(404, "未找到本机知识付费 Skills 包")
    root = SKILLS / _user_storage_key(user) / uuid.uuid4().hex
    try:
        safe_extract_zip(BUNDLED_SKILLS.read_bytes(), root)
        discovered = discover_skills(root)
    except Exception as exc:
        shutil.rmtree(root, ignore_errors=True)
        raise HTTPException(400, str(exc)) from exc
    existing = {_skill_name_key(item["name"]) for item in table("installed_skills", user).list()}
    created = []
    for skill in discovered:
        key = _skill_name_key(skill["name"])
        if key in existing:
            continue
        created.append(table("installed_skills", user).create({
            "name": skill["name"], "description": skill["description"],
            "category": "知识付费 Skills 包", "instructions": skill["instructions"],
            "storage_path": skill["path"], "enabled": True,
        }))
        existing.add(key)
    return {"installed": len(created), "discovered": len(discovered), "skills": created}


@router.put("/skills/{skill_id}")
def update_skill(skill_id: int, data: SkillUpdate, user: dict = Depends(get_current_user)):
    skill = table("installed_skills", user).update(skill_id, data.model_dump(exclude_none=True))
    if not skill:
        raise HTTPException(404, "Skill 不存在")
    return skill


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, user: dict = Depends(get_current_user)):
    with SessionLocal() as db:
        skill = db.get(InstalledSkill, skill_id)
        if not skill or skill.user_id != user["id"]:
            raise HTTPException(404, "Skill 不存在")
        path = Path(skill.storage_path)
        db.delete(skill)
        db.commit()
        if path.exists() and SKILLS.resolve() in path.resolve().parents:
            shutil.rmtree(path, ignore_errors=True)
    return {"ok": True}
