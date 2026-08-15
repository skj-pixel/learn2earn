"""Background generation task API."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..auth import get_current_user
from ..cloud_db import table
from ..services.generation_task_service import enqueue_generation
from ..services.product_generator import PRODUCT_TYPES
from ..services.strategy_compat import compatibility_matrices, list_strategies, validate_combination
from ..services.strategy_preferences import list_all_overrides

router = APIRouter(prefix="/api/tasks", tags=["generation-tasks"])

DEFAULT_STRATEGIES = {
    product_type: {
        "algorithms": ["hierarchical_planning", "iterative_refinement"] + (["chunked_generation"] if product_type in {"article", "course_outline", "sop"} else []),
        "techniques": ["source_grounding", "rag_grounding", "memorybear", "quality_scoring", "hallucination_check", "seo_optimization"],
        "recommended_skill_keywords": [info["name"], product_type],
    }
    for product_type, info in PRODUCT_TYPES.items()
}


def _resolve_defaults(product_types: list[str]) -> dict:
    """合并 DEFAULT_STRATEGIES + 用户策略覆盖。优先用用户覆盖的非空字段。"""
    overrides = list_all_overrides()
    base = DEFAULT_STRATEGIES[product_types[0]].copy()
    for ptype in product_types:
        override = overrides.get(ptype) or {}
        for axis in ("algorithms", "techniques"):
            values = override.get(axis) or []
            if values:
                base[axis] = values
    return base


class TaskCreate(BaseModel):
    note_id: int
    product_types: list[str]
    product_id: int | None = None
    skill_ids: list[int] = []
    algorithms: list[str] = []
    techniques: list[str] = []
    # 🔍 [作用] 2026-08 feat/29：每个产品类型可独立指定 strategy；key = product_type，value = {skill_ids, algorithms, techniques}
    # 空 dict 表示沿用 task 级默认；后端会做"每个 product_type 自己一套"的合并。
    # 示例：{"article": {"skill_ids": [3], "techniques": ["memorybear"]}, "ppt": {"algorithms": ["chunked_generation"]}}
    product_strategies: dict[str, dict] = {}


def _decorate_task(task: dict, user: dict) -> dict:
    """Attach stable display metadata without changing the task schema."""
    result = dict(task)
    note = table("notes", user).get(task.get("note_id")) if task.get("note_id") else None
    subject = table("subjects", user).get(note.get("subject_id")) if note and note.get("subject_id") else None
    result["note_title"] = note.get("title") if note else None
    result["subject_id"] = note.get("subject_id") if note else None
    result["subject_name"] = subject.get("name") if subject else None
    return result


@router.get("/strategies")
def get_strategies(user: dict = Depends(get_current_user)):
    # The hidden compatibility payload is sparse. Avoid loading all Skills and
    # materializing O(n^2) compatible pairs for a page that never displays them.
    return {**list_strategies(), "compatibility": compatibility_matrices(), "defaults": DEFAULT_STRATEGIES, "user_overrides": list_all_overrides()}


@router.post("")
def create_task(data: TaskCreate, user: dict = Depends(get_current_user)):
    if not table("notes", user).get(data.note_id):
        raise HTTPException(404, "笔记不存在")
    invalid = [value for value in data.product_types if value not in PRODUCT_TYPES]
    if invalid or not data.product_types:
        raise HTTPException(400, f"产品类型无效：{', '.join(invalid)}")
    # 🔍 [作用] 2026-08 feat/29：product_strategies 里的 key 必须都在 product_types 内；多余的 key 拒绝
    extra_keys = set((data.product_strategies or {}).keys()) - set(data.product_types)
    if extra_keys:
        raise HTTPException(400, f"product_strategies 含未勾选的产品类型：{', '.join(extra_keys)}")
    defaults = _resolve_defaults(data.product_types)
    effective_algorithms = data.algorithms or defaults["algorithms"]
    effective_techniques = data.techniques or defaults["techniques"]
    installed_ids = {item["id"] for item in table("installed_skills", user).list()}
    compatibility = validate_combination(data.skill_ids, effective_algorithms, effective_techniques, available_skill_ids=installed_ids)
    if compatibility.errors:
        raise HTTPException(400, "；".join(compatibility.errors))
    task = table("generation_tasks", user).create({
        "note_id": data.note_id, "product_id": data.product_id,
        "product_types": data.product_types, "skill_ids": data.skill_ids,
        "algorithms": effective_algorithms,
        "techniques": effective_techniques,
        "product_strategies": data.product_strategies or {},
        "status": "queued", "progress": 0, "current_step": "等待后台执行",
    })
    enqueue_generation(task["id"], user)
    return _decorate_task(task, user)


@router.get("")
def list_tasks(
    user: dict = Depends(get_current_user),
    q: str | None = Query(None, description="按产品类型/状态搜索任务"),
    sort: str = Query("created_at", description="排序字段：created_at | name"),
    order: str = Query("desc", description="排序方向：asc | desc"),
):
    tasks = table("generation_tasks", user).list()
    # 过滤
    if q:
        needle = q.strip().lower()
        if needle:
            tasks = [
                t for t in tasks
                if needle in "、".join(t.get("product_types") or []).lower()
                or needle in (t.get("status") or "").lower()
            ]
    # 排序：name = 产品类型拼接字符串；created_at = 创建时间
    reverse = order != "asc"
    key = "created_at" if sort != "name" else "name"

    def _sort_value(t):
        if key == "name":
            return "、".join(t.get("product_types") or [])
        return str(t.get("created_at") or "")

    tasks.sort(key=_sort_value, reverse=reverse)
    return [_decorate_task(task, user) for task in tasks]


@router.get("/{task_id}")
def get_task(task_id: int, user: dict = Depends(get_current_user)):
    task = table("generation_tasks", user).get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    return _decorate_task(task, user)


@router.post("/{task_id}/retry")
def retry_task(task_id: int, user: dict = Depends(get_current_user)):
    previous = table("generation_tasks", user).get(task_id)
    if not previous:
        raise HTTPException(404, "任务不存在")
    if previous.get("status") in {"queued", "running"}:
        raise HTTPException(409, "任务仍在执行，不能重复提交")
    if not table("notes", user).get(previous.get("note_id")):
        raise HTTPException(404, "任务关联的笔记不存在")
    task = table("generation_tasks", user).create({
        "note_id": previous["note_id"],
        "product_id": previous.get("product_id"),
        "product_types": previous.get("product_types") or [],
        "skill_ids": previous.get("skill_ids") or [],
        "algorithms": previous.get("algorithms") or [],
        "techniques": previous.get("techniques") or [],
        "product_strategies": previous.get("product_strategies") or {},
        "status": "queued", "progress": 0, "current_step": "等待后台执行",
    })
    enqueue_generation(task["id"], user)
    return _decorate_task(task, user)


@router.delete("/{task_id}")
def delete_task(task_id: int, user: dict = Depends(get_current_user)):
    tasks = table("generation_tasks", user)
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.get("status") in {"queued", "running"}:
        raise HTTPException(409, "任务仍在执行，完成或失败后才能删除")
    tasks.delete(task_id)
    return {"ok": True}
