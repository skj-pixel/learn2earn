"""MemoryBear 长程记忆 API：预览 + 统计 + 场景路由。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user
from ..cloud_db import table
from ..services.memorybear import (
    build_memory_context,
    memorybear_stats,
    route_scene,
)

router = APIRouter(prefix="/api/memorybear", tags=["memorybear"])


@router.get("/preview")
def preview_memory(
    note_id: int = Query(..., description="指定笔记 ID，提取五层记忆上下文"),
    user: dict = Depends(get_current_user),
):
    """预览当前笔记的 MemoryBear 上下文（与 RAG 权重分配）。"""
    note = table("notes", user).get(note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    subject = table("subjects", user).get(note["subject_id"]) if note.get("subject_id") else None
    notes = table("notes", user).list()
    products = table("products", user).list()
    context, meta = build_memory_context(note, subject, notes, products)
    return {
        "note_id": note_id,
        "context": context,
        "meta": meta,
    }


@router.get("/stats")
def get_stats(user: dict = Depends(get_current_user)):
    """MemoryBear 全局统计：各层条目数 + 重要性分布 + 冲突点。"""
    notes = table("notes", user).list()
    products = table("products", user).list()
    return memorybear_stats(notes, products)


@router.get("/scene-router")
def scene_router(
    note_id: int = Query(..., description="查询场景路由权重"),
    user: dict = Depends(get_current_user),
):
    """查询指定笔记的 MemoryBear vs RAG 权重建议。"""
    note = table("notes", user).get(note_id)
    if not note:
        raise HTTPException(404, "笔记不存在")
    notes = table("notes", user).list()
    products = table("products", user).list()
    decision = route_scene(note, notes, products)
    return {
        "note_id": note_id,
        "memorybear_weight": decision.memorybear_weight,
        "rag_weight": decision.rag_weight,
        "reason": decision.reason,
    }
