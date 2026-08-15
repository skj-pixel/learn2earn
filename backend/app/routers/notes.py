# 🔍 [语法] typing.Optional
# 🔍 [作用] 表示可选参数类型（可为 None）
from typing import Optional

# 🔍 [语法] FastAPI 导入
# 🔍 [作用] APIRouter/Depends/HTTPException
from fastapi import APIRouter, Depends, HTTPException

# 🔍 [语法] Pydantic BaseModel
# 🔍 [作用] 请求体验证
from pydantic import BaseModel

# 🔍 [语法] 相对导入（..auth, ..cloud_db）
# 🔍 [作用] 复用认证 + 双模式数据访问
from ..auth import get_current_user
from ..cloud_db import table


# 🔍 [语法] APIRouter 实例化
# 🔍 [作用] 笔记路由：URL 前缀 /api/notes
router = APIRouter(prefix="/api/notes", tags=["notes"])


# 🔍 [语法] Pydantic BaseModel
# 🔍 [作用] 创建笔记请求体
class NoteCreate(BaseModel):
    # 🔍 [语法] str（必填）
    # 🔍 [作用] 笔记标题
    title: str

    # 🔍 [语法] str（默认空）
    # 🔍 [作用] 保留字段（可为富文本）
    content: str = ""

    # 🔍 [语法] str（默认空）
    # 🔍 [作用] AI 生成器的核心输入
    raw_content: str = ""

    # 🔍 [语法] int（必填）
    # 🔍 [作用] 外键：所属科目 ID
    subject_id: int

    # 🔍 [语法] list（默认空）
    # 🔍 [作用] 标签列表
    tags: list = []

    # 🔍 [语法] str（默认 stage1）
    # 🔍 [作用] 学习阶段（stage1-4）
    learning_stage: str = "stage1"

    # 🔍 [语法] float（默认 30）
    # 🔍 [作用] 预估学习时长（分钟）
    estimated_minutes: float = 30

    # 🔍 [语法] bool（默认 False）
    # 🔍 [作用] 是否完成学习
    is_completed: bool = False


# 🔍 [语法] BaseModel（全 Optional）
# 🔍 [作用] 更新笔记请求体（PATCH 语义）
class NoteUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    raw_content: str | None = None
    tags: list | None = None
    learning_stage: str | None = None
    estimated_minutes: float | None = None
    is_completed: bool | None = None


# 🔍 [语法] 私有辅助函数
# 🔍 [作用] 注入 subject_name 字段（避免前端二次查询）
# 🔍 [陷阱] 每次列表都会触发 N 次科目查询（N+1 问题）
def _with_subject_name(note: dict, user: dict) -> dict:
    # 🔍 [语法] dict.get 通过 table()
    # 🔍 [作用] 查找科目名称
    subject = table("subjects", user).get(note["subject_id"])
    # 🔍 [语法] 三元表达式
    # 🔍 [作用] 找不到时返回 None
    return {**note, "subject_name": subject["name"] if subject else None}


# 🔍 [语法] @router.get + Optional 查询参数
# 🔍 [作用] GET /api/notes 列表查询
@router.get("")
def list_notes(
    # 🔍 [语法] Optional[int] = None
    # 🔍 [作用] 可选过滤参数（subject_id 不传则查全部）
    subject_id: Optional[int] = None,

    # 🔍 [语法] Optional[str] = None
    # 🔍 [作用] 学习阶段过滤
    learning_stage: Optional[str] = None,
    summary: bool = False,

    # 🔍 [语法] Depends 注入
    # 🔍 [作用] 依赖注入当前用户（鉴权）
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] 双模式数据访问
    # 🔍 [作用] 根据配置返回 CloudTable 或 LocalTable
    rows = table("notes", user).list({"subject_id": subject_id, "learning_stage": learning_stage})
    # 🔍 [语法] list comprehension
    # 🔍 [作用] 为每条注入 subject_name
    results = [_with_subject_name(row, user) for row in rows]
    if summary:
        for note in results:
            full_content = note.get("raw_content") or note.get("content") or ""
            note["content_length"] = len(full_content)
            note["raw_content"] = (note.get("raw_content") or "")[:400]
            note["content"] = (note.get("content") or "")[:400]
    return results


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/notes 创建笔记
@router.post("")
def create_note(
    # 🔍 [语法] BaseModel 自动验证
    data: NoteCreate,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] 外键校验
    # 🔍 [作用] 确保所属科目存在
    if not table("subjects", user).get(data.subject_id):
        # 🔍 [语法] raise HTTPException 404
        # 🔍 [作用] 科目不存在时返回 404
        raise HTTPException(status_code=404, detail="科目不存在")
    # 🔍 [语法] data.model_dump()
    # 🔍 [作用] Pydantic v2 转字典
    return _with_subject_name(table("notes", user).create(data.model_dump()), user)


# 🔍 [语法] @router.get + path 参数
# 🔍 [作用] GET /api/notes/{note_id}
@router.get("/{note_id}")
def get_note(
    # 🔍 [语法] int（FastAPI 自动验证类型）
    # 🔍 [作用] 路径参数（必须为整数）
    note_id: int,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] 调用 .get
    # 🔍 [作用] 单条查询
    note = table("notes", user).get(note_id)
    # 🔍 [语法] 早返回
    # 🔍 [作用] 404 处理
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return _with_subject_name(note, user)


# 🔍 [语法] @router.put + path 参数
# 🔍 [作用] PUT /api/notes/{note_id}
@router.put("/{note_id}")
def update_note(
    note_id: int,
    # 🔍 [语法] BaseModel
    # 🔍 [作用] PATCH 语义（部分更新）
    data: NoteUpdate,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] model_dump(exclude_none=True)
    # 🔍 [作用] 排除 None 字段，只更新提供的字段
    note = table("notes", user).update(note_id, data.model_dump(exclude_none=True))
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return _with_subject_name(note, user)


# 🔍 [语法] @router.delete
# 🔍 [作用] DELETE /api/notes/{note_id}
@router.delete("/{note_id}")
def delete_note(note_id: int, user: dict = Depends(get_current_user)):
    # 🔍 [语法] 双赋值
    # 🔍 [作用] 获取表实例
    notes = table("notes", user)
    # 🔍 [语法] 404 检查
    if not notes.get(note_id):
        raise HTTPException(status_code=404, detail="笔记不存在")
    # 🔍 [语法] 级联删除
    # 🔍 [作用] 删除笔记会级联删除其产品（models.py cascade 配置）
    notes.delete(note_id)
    # 🔍 [语法] 简单 ack
    # 🔍 [作用] RESTful DELETE 通常返回 204 或简单 ack
    return {"ok": True}
