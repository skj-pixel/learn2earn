"""Lightweight RAG service.

Implements external knowledge retrieval as a complementary technique alongside
MemoryBear. The strategy is intentionally pragmatic:

1. If a search-capable Skill (baidu-search, tavily-search) is installed AND its
   required API key env var is configured, run that skill as a subprocess to
   fetch live web snippets.
2. Otherwise, fall back to a "user-as-knowledge-base" retrieval: rank the
   user's other notes / products by keyword overlap and surface the top hits
   as in-context references.

The result is injected into the generation prompt with a clear "external
context, supplement only" disclaimer so the LLM treats it as a patch rather
than the authoritative source (MemoryBear remains primary).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# -----------------------------------------------------------------------------
# 关键词提取（粗粒度，按字符 unigram + 2-gram）
# -----------------------------------------------------------------------------

_CJK_RE = re.compile(r"[\u4e00-\u9fff]")
_ASCII_RE = re.compile(r"[A-Za-z0-9]+")
_STOPWORDS = set(
    "the a an of in on for to and or with by is are be was were this that it its as at from".split()
)


def _extract_keywords(text: str, limit: int = 8) -> list[str]:
    """抽取关键词：英文按空格切 + 中文按字符 unigram / bigram，过滤停用词。"""
    if not text:
        return []
    keywords: list[str] = []
    seen: set[str] = set()
    for token in _ASCII_RE.findall(text):
        token_low = token.lower()
        if token_low in _STOPWORDS or len(token_low) < 3:
            continue
        if token_low not in seen:
            seen.add(token_low)
            keywords.append(token_low)
    cjk_chars = _CJK_RE.findall(text)
    for ch in cjk_chars:
        if ch not in seen:
            seen.add(ch)
            keywords.append(ch)
    for i in range(len(cjk_chars) - 1):
        bigram = cjk_chars[i] + cjk_chars[i + 1]
        if bigram not in seen:
            seen.add(bigram)
            keywords.append(bigram)
        if len(keywords) >= limit:
            break
    return keywords[:limit]


def _score(text: str, keywords: Iterable[str]) -> int:
    """关键词命中数（粗粒度相关度打分）。"""
    if not text or not keywords:
        return 0
    lower = text.lower()
    hits = 0
    for kw in keywords:
        if kw.lower() in lower:
            hits += 1
    return hits


# -----------------------------------------------------------------------------
# 数据类
# -----------------------------------------------------------------------------


@dataclass
class RAGHit:
    title: str
    snippet: str
    source: str  # "web:baidu" / "web:tavily" / "user:note" / "user:product"
    url: str = ""
    score: float = 0.0


@dataclass
class RAGResult:
    query: str
    keywords: list[str] = field(default_factory=list)
    hits: list[RAGHit] = field(default_factory=list)
    engine: str = "none"  # "external" / "user-fallback" / "none"
    notes: list[str] = field(default_factory=list)

    def to_prompt_section(self, max_chars: int = 4000) -> str:
        """渲染为可注入 prompt 的 Markdown 段落，附带「外部知识补丁」免责声明。"""
        if not self.hits:
            return (
                "## RAG 外部检索（无可用上下文）\n"
                "本次未检索到相关材料，仅依赖 MemoryBear 长期记忆与源笔记。"
            )
        lines = [
            "## RAG 外部检索（外部知识补丁，非权威；以 MemoryBear + 源笔记为准）",
            f"检索关键词：{', '.join(self.keywords) or '(无)'}",
            f"检索引擎：{self.engine}",
            "",
        ]
        for idx, hit in enumerate(self.hits[:8], 1):
            title = hit.title.strip() or "(无标题)"
            snippet = hit.snippet.strip().replace("\n", " ")[:280]
            source = hit.source
            url = f" ({hit.url})" if hit.url else ""
            lines.append(f"{idx}. [{source}] {title}{url}")
            if snippet:
                lines.append(f"   {snippet}")
        body = "\n".join(lines)
        if len(body) > max_chars:
            body = body[: max_chars - 50] + "\n\n…（后续片段已截断，避免 prompt 过长）"
        return body


# -----------------------------------------------------------------------------
# 外部检索（通过 Skill 子进程）
# -----------------------------------------------------------------------------


def _find_installed_skill(user: dict, names: Iterable[str]) -> dict | None:
    """从用户的 InstalledSkill 表中按名称查找第一个 enabled 的 skill。"""
    try:
        from ..database import SessionLocal
        from ..models import InstalledSkill
    except Exception:
        return None
    with SessionLocal() as db:
        for name in names:
            row = db.query(InstalledSkill).filter(
                InstalledSkill.user_id == user["id"],
                InstalledSkill.name == name,
                InstalledSkill.enabled.is_(True),
            ).first()
            if row and Path(row.storage_path).is_dir():
                return {"id": row.id, "name": row.name, "storage_path": row.storage_path}
    return None


def _run_skill_subprocess(skill: dict, query: str, max_results: int = 5, timeout: int = 25) -> list[RAGHit]:
    """调用 Skill 自带的脚本作为外部知识检索入口（baidu-search / tavily-search）。"""
    storage = Path(skill["storage_path"])
    name = skill["name"]
    try:
        if name == "baidu-search":
            script = storage / "scripts" / "search.py"
            if not script.is_file():
                return []
            payload = json.dumps({"query": query, "count": max_results}, ensure_ascii=False)
            proc = subprocess.run(
                ["python", str(script), payload],
                capture_output=True, text=True, timeout=timeout,
                env={**os.environ},
            )
            if proc.returncode != 0:
                return []
            data = json.loads(proc.stdout or "{}")
        elif name == "tavily-search":
            script = storage / "scripts" / "tavily_search.py"
            if not script.is_file():
                return []
            proc = subprocess.run(
                ["python", str(script), "--query", query, "--max-results", str(max_results), "--format", "brave"],
                capture_output=True, text=True, timeout=timeout,
                env={**os.environ},
            )
            if proc.returncode != 0:
                return []
            data = json.loads(proc.stdout or "{}")
        else:
            return []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, Exception):
        return []
    hits: list[RAGHit] = []
    for item in (data.get("results") or [])[:max_results]:
        if not isinstance(item, dict):
            continue
        hits.append(
            RAGHit(
                title=str(item.get("title") or "(无标题)"),
                snippet=str(item.get("snippet") or item.get("content") or ""),
                source=f"web:{name}",
                url=str(item.get("url") or ""),
                score=1.0,
            )
        )
    return hits


# -----------------------------------------------------------------------------
# 用户知识库兜底检索
# -----------------------------------------------------------------------------


def _user_kb_fallback(query: str, keywords: list[str], notes: list[dict], products: list[dict], limit: int = 6) -> list[RAGHit]:
    """在没有外部 Skill 的情况下，把用户的其他笔记/产品当作"知识库"做关键词检索。"""
    hits: list[RAGHit] = []
    for note in notes:
        title = (note.get("title") or "").strip()
        body = (note.get("raw_content") or note.get("content") or "").strip()
        score = _score(title, keywords) * 3 + _score(body, keywords)
        if score <= 0:
            continue
        snippet = body[:240].replace("\n", " ")
        hits.append(RAGHit(title=title or "(无标题)", snippet=snippet, source="user:note", score=float(score)))
    for product in products:
        title = (product.get("title") or "").strip()
        body = (product.get("content") or "").strip()
        score = _score(title, keywords) * 2 + _score(body, keywords)
        if score <= 0:
            continue
        snippet = body[:240].replace("\n", " ")
        hits.append(RAGHit(title=title or "(无标题)", snippet=snippet, source="user:product", score=float(score)))
    hits.sort(key=lambda h: h.score, reverse=True)
    return hits[:limit]


# -----------------------------------------------------------------------------
# 主入口
# -----------------------------------------------------------------------------


def retrieve_external_context(query: str, notes: list[dict], products: list[dict], user: dict, *, max_results: int = 5) -> RAGResult:
    """按优先级检索 RAG 上下文：web Skill → 用户知识库兜底 → 无命中。"""
    keywords = _extract_keywords(query)
    result = RAGResult(query=query, keywords=keywords)
    if not keywords and not query.strip():
        result.notes.append("查询为空，未执行检索")
        return result
    # 1. 优先尝试 web Skill（baidu-search / tavily-search）
    for skill_names in (("baidu-search",), ("tavily-search",)):
        skill = _find_installed_skill(user, skill_names)
        if not skill:
            continue
        hits = _run_skill_subprocess(skill, query or " ".join(keywords), max_results=max_results)
        if hits:
            result.hits = hits
            result.engine = f"external:{skill['name']}"
            result.notes.append(f"通过已安装 Skill「{skill['name']}」检索到 {len(hits)} 条外部资料")
            return result
    # 2. 用户笔记/产品兜底
    fallback = _user_kb_fallback(query or " ".join(keywords), keywords, notes or [], products or [])
    if fallback:
        result.hits = fallback
        result.engine = "user-fallback"
        result.notes.append("外部 Skill 不可用，已回退到用户笔记/产品库")
        return result
    result.notes.append("未命中任何外部材料")
    return result