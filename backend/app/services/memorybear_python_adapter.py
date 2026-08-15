"""V3 adapter for the vendored, lightweight Python MemoryBear engine."""
from __future__ import annotations

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
VENDOR_ROOT = REPO_ROOT / "vendor" / "memory_bear_py"
if str(VENDOR_ROOT) not in sys.path:
    sys.path.insert(0, str(VENDOR_ROOT))

from memory_bear import MemoryBear  # noqa: E402


LAYER_MAP = {
    "working": "working",
    "episodic": "short_term",
    "explicit": "long_term",
    "implicit": "long_term",
}


def _stable_id(kind: str, value: object) -> str:
    return hashlib.sha256(f"{kind}:{value}".encode("utf-8")).hexdigest()[:24]


def _database_path(end_user_id: str) -> Path:
    root = REPO_ROOT / "storage" / "memory-bear-v3"
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{_stable_id('user', end_user_id)}.db"


def _text(row: dict) -> str:
    return str(row.get("raw_content") or row.get("content") or "").strip()


def _remember(bear: MemoryBear, *, kind: str, row_id: object, content: str,
              semantic_layer: str, importance: float = 0.8) -> None:
    if not content:
        return
    bear.remember(
        content[:12000],
        tags=[semantic_layer],
        importance=importance,
        source=f"{kind}:{row_id}",
        memory_id=_stable_id(kind, row_id),
        layer=LAYER_MAP[semantic_layer],
    )


def build_python_memory_context(note: dict, subject: dict | None, notes: list[dict],
                                products: list[dict], end_user_id: str) -> tuple[str, dict]:
    """Persist user-isolated memories and retrieve context with official five-layer semantics."""
    bear = MemoryBear(db_path=str(_database_path(end_user_id)), auto_prune=True)
    current_id = note.get("id", "current")
    current = f"{note.get('title', '')}\n{_text(note)}".strip()
    _remember(bear, kind="working-note", row_id=current_id, content=current,
              semantic_layer="working", importance=1.0)

    for row in notes:
        if str(row.get("id")) == str(current_id):
            continue
        content = f"{row.get('title', '')}\n{_text(row)}".strip()
        _remember(bear, kind="note", row_id=row.get("id"), content=content,
                  semantic_layer="episodic", importance=0.8)

    for row in products:
        content = f"{row.get('title', '')}\n{row.get('content') or ''}".strip()
        _remember(bear, kind="product", row_id=row.get("id"), content=content,
                  semantic_layer="explicit", importance=0.9)

    product_types = Counter(str(row.get("product_type")) for row in products if row.get("product_type"))
    tags = Counter(str(tag) for row in notes for tag in (row.get("tags") or []))
    preference = {
        "subject": (subject or {}).get("name"),
        "preferred_product_types": [key for key, _ in product_types.most_common(3)],
        "frequent_tags": [key for key, _ in tags.most_common(8)],
    }
    _remember(bear, kind="preferences", row_id="derived", content=json.dumps(preference, ensure_ascii=False),
              semantic_layer="implicit", importance=0.85)

    results = bear.recall(current, mode="deep", max_items=12)
    selected = [item for item in results if item.source != f"working-note:{current_id}"]
    sections = []
    layer_counts: Counter[str] = Counter()
    reverse_layer = {"short_term": "episodic", "long_term": "explicit", "working": "working"}
    for item in selected:
        semantic = next((tag for tag in item.tags if tag in LAYER_MAP), reverse_layer.get(item.layer, item.layer))
        layer_counts[semantic] += 1
        sections.append(f"### {semantic}\n{item.content}")

    # Perception is the current request; it is intentionally not persisted as long-term memory.
    meta = {
        "provider": "memory-bear-python-v3",
        "database": "user-isolated-sqlite",
        "layers": {name: layer_counts.get(name, 0) for name in ("perception", "working", "episodic", "explicit", "implicit")},
        "pruned": 0,
        "engine_stats": bear.get_stats(),
    }
    return "\n\n".join(sections) or "No relevant historical memory was recalled.", meta
