"""User-customizable per-product-type generation strategy overrides."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..auth import get_current_user
from ..services.product_generator import PRODUCT_TYPES
from ..services.strategy_preferences import (
    get_override,
    list_all_overrides,
    reset_override,
    update_override,
)

router = APIRouter(prefix="/api/strategy-preferences", tags=["strategy-preferences"])


class OverrideUpdate(BaseModel):
    algorithms: List[str] | None = None
    techniques: List[str] | None = None
    skill_keywords: List[str] | None = None


@router.get("")
def get_all(user: dict = Depends(get_current_user)):
    """列出所有产品类型的用户覆盖（与默认骨架合并）。"""
    overrides = list_all_overrides()
    return {
        "product_types": [
            {"id": ptype, "name": PRODUCT_TYPES[ptype]["name"], "override": overrides.get(ptype) or {"algorithms": [], "techniques": [], "skill_keywords": []}}
            for ptype in PRODUCT_TYPES.keys()
        ]
    }


@router.get("/{product_type}")
def get_one(product_type: str, user: dict = Depends(get_current_user)):
    if product_type not in PRODUCT_TYPES:
        raise HTTPException(404, f"未知产品类型：{product_type}")
    return {
        "product_type": product_type,
        "name": PRODUCT_TYPES[product_type]["name"],
        "override": get_override(product_type),
    }


@router.put("/{product_type}")
def update_one(product_type: str, data: OverrideUpdate, user: dict = Depends(get_current_user)):
    if product_type not in PRODUCT_TYPES:
        raise HTTPException(404, f"未知产品类型：{product_type}")
    override = update_override(
        product_type,
        algorithms=data.algorithms,
        techniques=data.techniques,
        skill_keywords=data.skill_keywords,
    )
    return {"product_type": product_type, "override": override, "message": "策略偏好已更新"}


@router.delete("/{product_type}")
def reset_one(product_type: str, user: dict = Depends(get_current_user)):
    if product_type not in PRODUCT_TYPES:
        raise HTTPException(404, f"未知产品类型：{product_type}")
    return {"product_type": product_type, "override": reset_override(product_type), "message": "已恢复默认策略"}