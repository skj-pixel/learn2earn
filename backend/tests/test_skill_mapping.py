# 🔍 [语法] 模块级 docstring
# 🔍 [作用] F07 单元测试：产品类型→技能映射 完整性与一致性
"""
验证 product_type_skill_map.json 的：
    - 14 种产品类型全部覆盖（≥1 技能）；
    - 每个推荐技能名称都能在 workbuddy_skills_all.zip 的 SKILL.md 中找到（无悬空引用）；
    - recommend_skill_names / filter_installed_for_product_type 行为正确。
"""
import json
import re
import zipfile
from pathlib import Path
import sys

from app.services.skill_service import (
    load_product_type_skill_map,
    recommend_skill_names,
    filter_installed_for_product_type,
)
from app.services.product_generator import PRODUCT_TYPES

# 映射清单与 zip 同目录
_MAP_PATH = Path(__file__).resolve().parents[1] / "bundled_skills" / "product_type_skill_map.json"
_ZIP_PATH = Path(__file__).resolve().parents[1] / "bundled_skills" / "workbuddy_skills_all.zip"
# 🔍 [作用] 复用用户交付包构建器，验证精简包不会漏掉映射技能。
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from build_product_skill_pack import build_pack  # noqa: E402


def _zip_skill_names() -> set[str]:
    """从内置 zip 抽取所有 SKILL.md 的 name 字段，作为"真实存在"的技能名集合。"""
    names = set()
    with zipfile.ZipFile(_ZIP_PATH) as z:
        for n in z.namelist():
            if n.endswith("SKILL.md") and n.count("/") == 1:
                txt = z.read(n).decode("utf-8", "ignore")
                m = re.search(r"^name:\s*(.+)$", txt, re.M)
                if m:
                    names.add(m.group(1).strip())
    return names


def test_all_14_product_types_covered():
    # 🔍 [作用] 当前 14 种产品类型在映射中都能找到 ≥1 个推荐技能
    mapping = load_product_type_skill_map()
    assert set(mapping.keys()) == set(PRODUCT_TYPES.keys()), "映射键必须与 PRODUCT_TYPES 完全一致"
    for ptype, entry in mapping.items():
        skills = entry.get("skills", [])
        assert len(skills) >= 1, f"产品类型 {ptype} 至少需要 1 个推荐技能"
        assert entry.get("rationale"), f"产品类型 {ptype} 缺少 rationale 说明"


def test_recommended_skills_exist_in_bundle():
    # 🔍 [作用] 映射里写的每个技能名，都必须真实存在于打包 zip 中（杜绝悬空引用）
    real_names = _zip_skill_names()
    mapping = load_product_type_skill_map()
    for ptype, entry in mapping.items():
        for name in entry.get("skills", []):
            assert name in real_names, (
                f"产品类型 {ptype} 推荐的技能 {name!r} 不在打包 zip 中；"
                f"真实技能名样例：{sorted(real_names)[:5]}"
            )


def test_recommend_skill_names_order_and_content():
    # 🔍 [作用] 单类型推荐返回顺序稳定、内容正确
    names = recommend_skill_names("article")
    assert names == ["wechat-article-pro", "humanizer", "content-factory"]
    # 未知类型返回空列表（不抛错）
    assert recommend_skill_names("nonexistent_type") == []


def test_filter_installed_for_product_type():
    # 🔍 [作用] 从已安装技能中精准筛出匹配项，并按映射顺序重排
    installed = [
        {"name": "humanizer", "description": "去AI味"},
        {"name": "content-factory", "description": "内容工厂"},
        {"name": "stock-analysis", "description": "无关技能"},
        {"name": "wechat-article-pro", "description": "公众号长文"},
    ]
    matched = filter_installed_for_product_type("article", installed)
    assert [s["name"] for s in matched] == [
        "wechat-article-pro", "humanizer", "content-factory"
    ]
    # 无关技能被排除
    assert all(s["name"] != "stock-analysis" for s in matched)


def test_filter_reports_coverage_gap_via_public_api():
    # 🔍 [作用] 当某推荐技能未安装时，filter 仍能返回已安装部分（缺口由端点层标记）
    installed = [{"name": "skill-creator"}]  # prompt_template 推荐 3 个，仅装了 1 个
    matched = filter_installed_for_product_type("prompt_template", installed)
    assert len(matched) == 1
    assert matched[0]["name"] == "skill-creator"


def test_curated_skill_pack_contains_only_mapped_skills(tmp_path):
    # 🔍 [作用] 构建产物必须覆盖所有推荐技能，并携带可读映射和说明。
    output = build_pack(tmp_path / "Learn2Earn_14种产品生成Skills包.zip")
    required = {name for entry in load_product_type_skill_map().values() for name in entry["skills"]}
    with zipfile.ZipFile(output) as bundle:
        assert {"README.md", "产品类型技能映射.json"}.issubset(bundle.namelist())
        bundled_names = set()
        for member in bundle.namelist():
            if member.endswith("SKILL.md") and member.count("/") == 1:
                text = bundle.read(member).decode("utf-8", "ignore")
                match = re.search(r"^name:\s*(.+)$", text, re.M)
                if match:
                    bundled_names.add(match.group(1).strip())
        assert bundled_names == required
