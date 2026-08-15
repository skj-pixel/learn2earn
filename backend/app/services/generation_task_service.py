"""Persistent navigation-safe generation task runner."""
from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from ..cloud_db import table
from sqlalchemy.exc import OperationalError

from ..database import SessionLocal
from ..models import InstalledSkill, NoteAsset
from .note_asset_service import materialize_inline_note_images
from ..services.agentic_product_generator import AgenticProductGenerator
from ..services.llm_service import get_llm_service, reload_llm_service
from ..services.product_generator import PRODUCT_TYPES
from ..services.skill_service import build_skill_prompt
from ..services.memorybear_python_adapter import build_python_memory_context
from ..services.rag_service import retrieve_external_context
from ..services.strategy_compat import validate_combination

EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="learn2earn-generation")


def _exception_detail(exc: Exception) -> str:
    message = str(exc).strip() or "无错误详情"
    return f"{type(exc).__name__}: {message}"


def build_generation_meta(task_id: int, task: dict, skills: list[dict], techniques: list[str], memory_meta: dict, strategy_warnings: list[str], product_type: str | None = None, per_product: dict | None = None) -> dict:
    """构造产品生成溯源元数据，保证同一任务生成的多个产品可被统一定位。"""
    # 🔍 [作用] 技能名称单独存储，产品库无需再次查 Skill 表即可展示生成上下文。
    skill_names = [skill.get("name") for skill in skills]
    # 🔍 [作用] task_id 是任务页与产品库之间的稳定关联键，不新增数据库迁移。
    meta = {
        "task_id": task_id,
        "skill_ids": task.get("skill_ids") or [],
        "skill_names": skill_names,
        "algorithms": task.get("algorithms") or [],
        "techniques": techniques,
        "memorybear": memory_meta,
        "strategy_warnings": strategy_warnings,
    }
    # 🔍 [作用] 2026-08 feat/29：每个产品可记录自己生效的 strategy 覆盖，便于回溯"这个产品当时是怎么生成的"
    if product_type and per_product is not None:
        meta["product_type"] = product_type
        meta["effective"] = per_product
    return meta


def _load_selected_skills(user: dict, skill_ids: list[int]) -> list[dict]:
    """Load private instructions for the worker without exposing them in list APIs."""
    if not skill_ids:
        return []
    with SessionLocal() as db:
        rows = db.query(InstalledSkill).filter(
            InstalledSkill.user_id == user["id"],
            InstalledSkill.id.in_(skill_ids),
            InstalledSkill.enabled.is_(True),
        ).all()
        by_id = {
            row.id: {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "instructions": row.instructions,
            }
            for row in rows
        }
    return [by_id[skill_id] for skill_id in skill_ids if skill_id in by_id]


def enqueue_generation(task_id: int, user: dict):
    EXECUTOR.submit(_run_task, task_id, dict(user))


def _update(task_id: int, user: dict, **values):
    values["updated_at"] = datetime.now()
    table("generation_tasks", user).update(task_id, values)


def _resolve_per_product_strategy(task: dict, product_type: str) -> dict:
    """解析单个 product_type 实际生效的 strategy 覆盖。

    优先级：product_strategies[product_type] 中的字段 > task 级默认。
    缺省时回退到 task 级的 skill_ids / algorithms / techniques。
    """
    override = (task.get("product_strategies") or {}).get(product_type) or {}
    return {
        "skill_ids": override.get("skill_ids", task.get("skill_ids") or []),
        "algorithms": override.get("algorithms", task.get("algorithms") or []),
        "techniques": override.get("techniques", task.get("techniques") or []),
    }


def _is_transient_database_open_error(exc: Exception) -> bool:
    return isinstance(exc, OperationalError) and "unable to open database file" in str(exc).lower()


def _run_task(task_id: int, user: dict):
    try:
        return _run_task_once(task_id, user)
    except OperationalError as exc:
        # Replaying the workflow could duplicate products committed before the failure.
        try:
            _update(task_id, user, status="failed", current_step="生成失败", error=_exception_detail(exc), completed_at=datetime.now())
        except OperationalError:
            pass
        return None


def _run_task_once(task_id: int, user: dict):
    task = table("generation_tasks", user).get(task_id)
    if not task:
        return
    try:
        _update(task_id, user, status="running", progress=5, current_step="读取笔记与生成策略", started_at=datetime.now())
        note = table("notes", user).get(task["note_id"])
        if not note:
            raise RuntimeError("源笔记不存在")
        subject = table("subjects", user).get(note["subject_id"])
        raw_content = note.get("raw_content") or note.get("content") or ""
        # 🔍 [作用] 2026-08 feat/29：先按 task 级的 skill_ids 准备基础 skills 列表；后续每个产品可叠加自己的 skill_ids
        base_skills = _load_selected_skills(user, task.get("skill_ids", []))
        # 🔍 [作用] 2026-08 feat/29：收集所有 product_type 用到的 skill_ids（task 级 + 各产品 override 之并集）
        all_skill_ids: set[int] = set(task.get("skill_ids") or [])
        for ptype in (task.get("product_types") or []):
            override = (task.get("product_strategies") or {}).get(ptype) or {}
            for sid in override.get("skill_ids") or []:
                all_skill_ids.add(int(sid))
        merged_skills = _load_selected_skills(user, sorted(all_skill_ids))
        prompt = build_skill_prompt(merged_skills)
        # 🔍 [作用] task 级 techniques 仅用于一次性上下文（MemoryBear / RAG），下面按 product 各自再算
        base_techniques = task.get("techniques") or []
        memory_meta = {"layers": {}, "pruned": 0}
        # 🔍 [作用] MemoryBear / RAG 是 task 级上下文，不按产品分别注入（每个产品都看到同一份长期记忆更合理）
        if "memorybear" in base_techniques:
            memory_context, memory_meta = build_python_memory_context(
                note,
                subject,
                table("notes", user).list(),
                table("products", user).list(),
                str(user.get("id", "local-user")),
            )
            # MemoryBear 为权威记忆来源（处理历史笔记/产品/用户偏好）；
            # RAG(rag_grounding) 退化为外部知识补丁，仅作补充。
            prompt = f"{prompt}\n\n## MemoryBear 长期记忆（权威记忆来源，优先遵循用户历史偏好与已验证知识）\n{memory_context}"
        if "rag_grounding" in base_techniques:
            rag_result = retrieve_external_context(
                query=f"{note['title']}\n{(note.get('raw_content') or '')[:1500]}",
                notes=table("notes", user).list(),
                products=table("products", user).list(),
                user=user,
            )
            prompt = f"{prompt}\n\n{rag_result.to_prompt_section()}"
        # 🔍 [作用] 读取该笔记下所有 NoteAsset（word-import / editor-upload 图片），
        # 注入到 prompt 让 LLM 在生成中保留 [插图 N: filename] 引用。
        note_assets: list[dict] = []
        materialize_inline_note_images(note, user)
        with SessionLocal() as db:
            rows = db.query(NoteAsset).filter(
                NoteAsset.user_id == user["id"],
                NoteAsset.note_id == task["note_id"],
            ).order_by(NoteAsset.id).all()
            note_assets = [
                {"id": row.id, "filename": row.filename, "url": f"/api/assets/{row.id}", "source_anchor": row.source_anchor}
                for row in rows
            ]
        if note_assets:
            asset_lines = ["", "## 源笔记插图清单", "以下图片为源笔记中已上传的资源，请用形如 `[插图 N: filename]` 的语法在正文中保留引用（docx_service 会自动还原为内嵌图片）："]
            for idx, asset in enumerate(note_assets, 1):
                asset_lines.append(f"- [插图 {idx}: {asset['filename']}] (URL: {asset['url']}, 定位: {asset['source_anchor']})")
            prompt = f"{prompt}\n" + "\n".join(asset_lines)
        # 🔍 [作用] LLM 与生成器初始化不依赖 MemoryBear，任意质量技术组合都可执行。
        reload_llm_service()
        llm = get_llm_service()
        llm_ready = llm.is_ready()
        if not llm_ready:
            raise RuntimeError("LLM 服务未配置或未启用")
        # 🔍 [作用] 2026-08 feat/29：兼容校验合并考虑 task 级 + 各产品 override
        union_skill_ids = sorted(all_skill_ids)
        union_algorithms = list(task.get("algorithms") or [])
        for ptype in (task.get("product_types") or []):
            override = (task.get("product_strategies") or {}).get(ptype) or {}
            for algo in override.get("algorithms") or []:
                if algo not in union_algorithms:
                    union_algorithms.append(algo)
        # 🔍 [作用] 咨询式兼容校验只产生警告，不阻断用户选择的自由组合。
        compat = validate_combination(
            skill_ids=union_skill_ids,
            algorithms=union_algorithms,
            techniques=base_techniques,
            llm_ready=llm_ready,
        )
        generator = AgenticProductGenerator(llm)
        results = []
        types = task.get("product_types") or []
        for index, product_type in enumerate(types):
            info = PRODUCT_TYPES.get(product_type)
            if not info:
                raise RuntimeError(f"不支持的产品类型：{product_type}")
            # 🔍 [作用] 2026-08 feat/29：每个产品用自己的 strategy 覆盖
            per_product = _resolve_per_product_strategy(task, product_type)
            per_skill_ids = per_product["skill_ids"]
            per_algorithms = per_product["algorithms"]
            per_techniques = per_product["techniques"]
            per_skills = _load_selected_skills(user, per_skill_ids) if per_skill_ids else base_skills
            per_prompt = build_skill_prompt(per_skills) if per_skills else prompt
            prompt_settings = (task.get("product_strategies") or {}).get("__user_prompts__", {})
            common_prompt = (task.get("common_prompt") or prompt_settings.get("common_prompt") or "").strip()
            product_prompts = task.get("product_prompts") or prompt_settings.get("product_prompts") or {}
            product_prompt = str(product_prompts.get(product_type) or "").strip()
            if common_prompt:
                per_prompt += f"\n\n## 用户公共生成要求\n{common_prompt}"
            if product_prompt:
                per_prompt += f"\n\n## 当前产品专属生成要求\n{product_prompt}"
            per_compat = validate_combination(
                skill_ids=list(per_skill_ids),
                algorithms=list(per_algorithms),
                techniques=list(per_techniques),
                llm_ready=llm_ready,
            )
            per_warnings = list(compat.warnings) + [w for w in per_compat.warnings if w not in compat.warnings]
            per_meta = build_generation_meta(
                task_id, task, per_skills, per_techniques, memory_meta, per_warnings,
                product_type=product_type, per_product=per_product,
            )
            _update(task_id, user, progress=10 + round(index / max(1, len(types)) * 80), current_step=f"生成 {info['name']}")
            generated = asyncio.run(generator.generate(
                note_title=note["title"], note_content=raw_content,
                product_type=product_type, subject_name=subject["name"] if subject else "",
                skill_prompt=per_prompt, algorithms=per_algorithms, techniques=per_techniques,
            ))
            if task.get("product_id") and len(types) == 1:
                product = table("products", user).update(task["product_id"], {"content": generated["content"], "generation_meta": per_meta})
            else:
                product = table("products", user).create({
                    "title": f"[{info['icon']}] {note['title']} - {info['name']}",
                    "product_type": product_type, "content": generated["content"],
                    "subject_id": note["subject_id"], "note_id": note["id"],
                    "price_suggestion": float(info["price_range"][0]),
                    "platform_suggestion": info["platforms"][:3],
                    "keywords": [note["title"]] + (note.get("tags") or []), "status": "draft",
                    "generation_meta": per_meta,
                })
            results.append({"product": product, "quality_report": generated.get("quality_report", {}), "workflow_trace": generated.get("workflow_trace", [])})
        _update(task_id, user, status="completed", progress=100, current_step="生成完成", result={"products": results}, completed_at=datetime.now())
    except OperationalError as exc:
        _update(task_id, user, status="failed", current_step="生成失败", error=_exception_detail(exc), completed_at=datetime.now())
    except Exception as exc:
        _update(task_id, user, status="failed", current_step="生成失败", error=_exception_detail(exc), completed_at=datetime.now())
