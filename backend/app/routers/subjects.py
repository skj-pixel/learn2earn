# 🔍 [语法] FastAPI 导入
# 🔍 [作用] APIRouter/Depends/HTTPException
from fastapi import APIRouter, Depends, HTTPException

# 🔍 [语法] Pydantic BaseModel
# 🔍 [作用] 请求体验证
from pydantic import BaseModel

# 🔍 [语法] 相对导入
from ..auth import get_current_user
from ..cloud_db import table


# 🔍 [语法] APIRouter 实例化
# 🔍 [作用] 科目路由：URL 前缀 /api/subjects
router = APIRouter(prefix="/api/subjects", tags=["subjects"])


# 🔍 [语法] Pydantic BaseModel
# 🔍 [作用] 创建科目请求体（基础字段）
class SubjectCreate(BaseModel):
    # 🔍 [语法] str 必填
    # 🔍 [作用] 科目名称（如 "Python编程"）
    name: str

    # 🔍 [语法] str 默认 📚
    # 🔍 [作用] emoji 图标
    icon: str = "📚"

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 描述（学习目标）
    description: str = ""

    # 🔍 [语法] str 默认 #6366f1
    # 🔍 [作用] 主题色（HEX）
    color: str = "#6366f1"


# 🔍 [语法] BaseModel
# 🔍 [作用] 更新科目请求体（含统计字段）
class SubjectUpdate(BaseModel):
    # 🔍 [语法] 所有 Optional
    # 🔍 [作用] 部分更新
    name: str | None = None
    icon: str | None = None
    description: str | None = None
    color: str | None = None

    # 🔍 [语法] float 可选
    # 🔍 [作用] 学习时长统计字段
    total_hours: float | None = None


def _unique_subject_name(requested_name: str, user: dict, exclude_id: int | None = None) -> str:
    requested_name = requested_name.strip()
    existing_names = {
        str(subject.get("name", "")).strip()
        for subject in table("subjects", user).list()
        if exclude_id is None or int(subject["id"]) != exclude_id
    }
    unique_name = requested_name
    suffix = 1
    while unique_name in existing_names:
        unique_name = f"{requested_name}-{suffix}"
        suffix += 1
    return unique_name


# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/subjects 列表
@router.get("")
def list_subjects(user: dict = Depends(get_current_user)):
    # 🔍 [语法] 双模式数据访问
    # 🔍 [作用] 当前用户的所有科目
    subjects = table("subjects", user).list()
    # 🔍 [作用] 2026-08 fix/27：note_count 在这里重算，避免依赖 Subject.to_dict 里的 len(self.notes) 懒加载
    # Subject.to_dict 中的懒加载对外键孤儿 / user_id 隔离并不健壮，且 lazy load 在多 Session 下会读到陈旧数据。
    # 主动遍历 notes 表按 subject_id 计数，结果可靠；同时给前端兜底。
    notes = table("notes", user).list()
    counts: dict[int, int] = {}
    for note in notes:
        subject_id = note.get("subject_id")
        if subject_id is None:
            continue
        # 🔍 [作用] subject_id 可能是 string（云端 schema 偶发）— 统一 int 化兜底
        try:
            sid = int(subject_id)
        except (TypeError, ValueError):
            continue
        counts[sid] = counts.get(sid, 0) + 1
    for subject in subjects:
        try:
            subject["note_count"] = counts.get(int(subject["id"]), 0)
        except (TypeError, ValueError):
            subject["note_count"] = 0
    return subjects


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/subjects 创建科目
@router.post("")
def create_subject(
    data: SubjectCreate,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] dict 字面量
    # 🔍 [作用] 创建科目（不含 total_hours，默认 0）
    payload = data.model_dump()
    payload["name"] = _unique_subject_name(payload["name"], user)
    return table("subjects", user).create(payload)


# 🔍 [语法] @router.get + path
# 🔍 [作用] GET /api/subjects/{subject_id}
@router.get("/{subject_id}")
def get_subject(
    subject_id: int,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] 单条查询
    # 🔍 [作用] 返回科目详情
    subject = table("subjects", user).get(subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    # 🔍 [作用] 2026-08 fix/27：科目详情也实时重算 note_count（不再依赖懒加载）
    rows = table("notes", user).list({"subject_id": subject_id})
    subject["note_count"] = len(rows)
    return subject


# 🔍 [语法] @router.put
# 🔍 [作用] PUT /api/subjects/{subject_id}
@router.put("/{subject_id}")
def update_subject(
    subject_id: int,
    data: SubjectUpdate,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] exclude_none=True
    # 🔍 [作用] 部分更新（只更新非空字段）
    subjects = table("subjects", user)
    existing = subjects.get(subject_id)
    if not existing:
        raise HTTPException(status_code=404, detail="科目不存在")
    payload = data.model_dump(exclude_none=True)
    if "name" in payload:
        requested_name = payload["name"].strip()
        if requested_name == str(existing.get("name", "")).strip():
            payload["name"] = existing["name"]
        else:
            payload["name"] = _unique_subject_name(requested_name, user, exclude_id=subject_id)
    subject = subjects.update(subject_id, payload)
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在")
    return subject


# 🔍 [语法] @router.delete
# 🔍 [作用] DELETE /api/subjects/{subject_id}
# 🔍 [陷阱] ⚠️ 硬删除会级联删除所有笔记和产品（SQLAlchemy cascade）
@router.delete("/{subject_id}")
def delete_subject(subject_id: int, user: dict = Depends(get_current_user)):
    # 🔍 [语法] 获取表实例
    subjects = table("subjects", user)
    if not subjects.get(subject_id):
        raise HTTPException(status_code=404, detail="科目不存在")
    # 🔍 [语法] 级联删除
    # 🔍 [陷阱] 数据库层 cascade 会删除所有 note 和 product
    subjects.delete(subject_id)
    return {"ok": True}
