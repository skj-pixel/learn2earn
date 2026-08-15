"""User-customizable per-product-type generation strategy preferences.

Users can override the default `algorithms` / `techniques` / `recommended_skill_keywords`
for any product type from the Settings → 产品策略 page. Preferences are stored in
`backend/app/services/strategy_preferences.json` (gitignored) so they survive across
restarts but never leak to the repository.

The default fallbacks live in `routers/tasks.py::DEFAULT_STRATEGIES` (built from
`PRODUCT_TYPES`); this module only adds the per-user override layer.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List

from .product_generator import PRODUCT_TYPES

_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))
PREFERENCES_FILE = os.path.join(_CONFIG_DIR, "strategy_preferences.json")


def _empty_preferences() -> dict:
    """Generate the empty preferences skeleton (every product type gets an entry)."""
    return {
        "version": 1,
        "overrides": {
            ptype: {"algorithms": [], "techniques": [], "skill_keywords": []}
            for ptype in PRODUCT_TYPES.keys()
        },
    }


def load_preferences() -> dict:
    """Load preferences JSON; auto-create on first call."""
    if not os.path.isfile(PREFERENCES_FILE):
        save_preferences(_empty_preferences())
        return _empty_preferences()
    try:
        with open(PREFERENCES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_preferences()
    # Ensure every known product type has an entry (forward compatibility).
    skeleton = _empty_preferences()
    for ptype, info in skeleton["overrides"].items():
        data.setdefault("overrides", {}).setdefault(ptype, info)
    return data


def save_preferences(prefs: dict) -> None:
    """Persist preferences to JSON (UTF-8, pretty-printed)."""
    os.makedirs(os.path.dirname(PREFERENCES_FILE), exist_ok=True)
    with open(PREFERENCES_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)


def get_override(product_type: str) -> dict:
    """Return the override (or default skeleton entry) for a single product type."""
    prefs = load_preferences()
    overrides = prefs.get("overrides") or {}
    if product_type not in overrides:
        return {"algorithms": [], "techniques": [], "skill_keywords": []}
    return overrides[product_type] or {"algorithms": [], "techniques": [], "skill_keywords": []}


def update_override(product_type: str, *, algorithms: List[str] | None = None, techniques: List[str] | None = None, skill_keywords: List[str] | None = None) -> dict:
    """Update a single product type's override and persist."""
    if product_type not in PRODUCT_TYPES:
        raise ValueError(f"未知产品类型: {product_type}")
    prefs = load_preferences()
    current = prefs.get("overrides", {}).get(product_type, {"algorithms": [], "techniques": [], "skill_keywords": []})
    if algorithms is not None:
        current["algorithms"] = list(dict.fromkeys(algorithms))
    if techniques is not None:
        current["techniques"] = list(dict.fromkeys(techniques))
    if skill_keywords is not None:
        current["skill_keywords"] = list(dict.fromkeys(skill_keywords))
    prefs.setdefault("overrides", {})[product_type] = current
    save_preferences(prefs)
    return current


def list_all_overrides() -> Dict[str, dict]:
    """Return a `product_type -> override` map (always covering every known type)."""
    prefs = load_preferences()
    return prefs.get("overrides", {})


def reset_override(product_type: str) -> dict:
    """Reset one product type back to defaults (empty override)."""
    prefs = load_preferences()
    empty = {"algorithms": [], "techniques": [], "skill_keywords": []}
    prefs.setdefault("overrides", {})[product_type] = empty
    save_preferences(prefs)
    return empty