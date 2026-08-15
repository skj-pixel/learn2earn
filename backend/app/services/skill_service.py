"""Safe skill archive storage and prompt instruction loading."""
from __future__ import annotations

import io
import json
import re
import shutil
import zipfile
from functools import lru_cache
from pathlib import Path, PurePosixPath

MAX_FILES = 2000
MAX_PROMPT_CHARS = 24000

# 🔍 [语法] 模块级常量
# 🔍 [作用] 产品类型→技能 推荐映射清单（与 workbuddy_skills_all.zip 内 SKILL.md name 对齐）
_PRODUCT_TYPE_SKILL_MAP_PATH = (
    Path(__file__).resolve().parents[3] / "backend" / "bundled_skills" / "product_type_skill_map.json"
)

PRODUCT_TYPE_INDEX = {
    "article": 0, "ppt": 1, "sop": 2, "prompt_template": 3,
    "course_outline": 4, "interview_qa": 5, "workflow": 6,
    "product_intro": 7, "quiz": 8, "mindmap": 9, "checklist": 10,
    "flashcard": 11, "script": 12, "llm_skill": 13,
}


@lru_cache(maxsize=1)
def load_product_type_skill_map() -> dict:
    """读取「产品类型→技能」推荐映射（清单文件缺失时返回空映射，绝不抛错）。"""
    if not _PRODUCT_TYPE_SKILL_MAP_PATH.is_file():
        return {}
    try:
        data = json.loads(_PRODUCT_TYPE_SKILL_MAP_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data.get("mapping", {}) or {}


def recommend_skill_names(product_type: str) -> list[str]:
    """返回某产品类型推荐的技能名称列表（按映射顺序）。未知类型返回空列表。"""
    mapping = load_product_type_skill_map()
    entry = mapping.get(product_type)
    if not entry:
        return []
    return list(entry.get("skills", []))


def product_type_ids_for_skill(skill_name: str, description: str = "") -> list[int]:
    """Return stable 0-13 labels, with conservative keyword inference for unknown Skills."""
    name = str(skill_name or "").strip().casefold()
    matched = []
    for product_type, entry in load_product_type_skill_map().items():
        names = {str(value).strip().casefold() for value in entry.get("skills", [])}
        if name in names and product_type in PRODUCT_TYPE_INDEX:
            matched.append(PRODUCT_TYPE_INDEX[product_type])
    if matched:
        return sorted(matched)

    searchable = f"{name} {description or ''}".casefold()
    keyword_groups = {
        0: ("article", "wechat", "公众号", "写作", "copywriting", "blog"),
        1: ("ppt", "slide", "deck", "演示", "幻灯"),
        2: ("sop", "procedure", "流程文档"),
        3: ("prompt", "提示词"),
        4: ("course", "lesson", "tutorial", "课程", "教案"),
        5: ("interview", "面试", "问答"),
        6: ("workflow", "automation", "工作流", "自动化"),
        7: ("product", "marketing", "promo", "销售", "营销", "分销"),
        8: ("quiz", "exam", "test", "测验", "练习题"),
        9: ("mindmap", "mind-map", "思维导图"),
        10: ("checklist", "清单", "避坑"),
        11: ("flashcard", "anki", "记忆卡"),
        12: ("video", "script", "storyboard", "视频", "脚本", "分镜"),
        13: ("skill", "agent", "llm", "claude", "codex"),
    }
    inferred = [product_id for product_id, keywords in keyword_groups.items() if any(word in searchable for word in keywords)]
    return sorted(set(inferred)) or [13]


def filter_installed_for_product_type(product_type: str, installed: list[dict]) -> list[dict]:
    """从已安装技能中筛出与某产品类型匹配的技能（按 name 精确匹配）。

    返回结构：[{"name", "description", "recommended": true, ...}]，
    并附 coverage_gap 标记（推荐技能是否全部已安装）。
    """
    # 🔍 [作用] 取推荐名称集合，顺序保留映射里的先后
    names = recommend_skill_names(product_type)
    name_set = {n for n in names}
    matched = [s for s in installed if (s.get("name") or "") in name_set]
    # 按映射顺序重排，未匹配（缺失）的 skill 置后
    order = {n: i for i, n in enumerate(names)}
    matched.sort(key=lambda s: order.get(s.get("name", ""), 999))
    return matched


def safe_extract_zip(data: bytes, destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        members = archive.infolist()
        if len(members) > MAX_FILES:
            raise ValueError("Skill 压缩包文件数量过多")
        for member in members:
            path = PurePosixPath(member.filename.replace("\\", "/"))
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Skill 压缩包包含不安全路径")
            target = destination.joinpath(*path.parts)
            resolved = target.resolve()
            if destination.resolve() not in resolved.parents and resolved != destination.resolve():
                raise ValueError("Skill 解包路径越界")
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            extracted.append(target)
    return extracted


def discover_skills(root: Path) -> list[dict]:
    results = []
    for skill_file in root.rglob("SKILL.md"):
        text = skill_file.read_text(encoding="utf-8", errors="replace")
        name = skill_file.parent.name
        frontmatter = re.match(r"^---\s*(.*?)\s*---", text, re.S)
        description = ""
        if frontmatter:
            name_match = re.search(r"^name:\s*[\"']?(.+?)[\"']?\s*$", frontmatter.group(1), re.M)
            desc_match = re.search(r"^description:\s*[\"']?(.+?)[\"']?\s*$", frontmatter.group(1), re.M)
            if name_match:
                name = name_match.group(1).strip()
            if desc_match:
                description = desc_match.group(1).strip()
        results.append({"name": name[:200], "description": description[:1000], "instructions": text[:MAX_PROMPT_CHARS], "path": str(skill_file.parent)})
    return results


def build_skill_prompt(skills: list[dict]) -> str:
    sections, remaining = [], MAX_PROMPT_CHARS
    for skill in skills:
        header = f"\n## Skill: {skill.get('name', '未命名')}\n"
        body = skill.get("instructions", "")
        chunk = (header + body)[:remaining]
        if chunk:
            sections.append(chunk)
            remaining -= len(chunk)
        if remaining <= 0:
            break
    return "\n".join(sections)
