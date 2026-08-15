"""Build a curated Skills ZIP for the 14 supported product types."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = REPO_ROOT / "backend" / "bundled_skills"
MAP_PATH = SKILL_DIR / "product_type_skill_map.json"
SOURCE_ZIP = SKILL_DIR / "workbuddy_skills_all.zip"


def load_required_skill_names(map_path: Path = MAP_PATH) -> list[str]:
    """Return mapped skill names once, preserving product-map order."""
    mapping = json.loads(map_path.read_text(encoding="utf-8"))["mapping"]
    return list(dict.fromkeys(name for entry in mapping.values() for name in entry["skills"]))


def index_skill_roots(source: zipfile.ZipFile) -> dict[str, str]:
    """Index frontmatter skill names to their top-level ZIP directory."""
    index: dict[str, str] = {}
    for member in source.namelist():
        if not member.endswith("/SKILL.md") or member.count("/") != 1:
            continue
        text = source.read(member).decode("utf-8", "ignore")
        match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        if match:
            index.setdefault(match.group(1).strip(), member.split("/", 1)[0])
    return index


def build_pack(output_path: Path) -> Path:
    """Copy only mapped skill folders and a readable manifest into a new ZIP."""
    required_names = load_required_skill_names()
    mapping_text = MAP_PATH.read_text(encoding="utf-8")
    with zipfile.ZipFile(SOURCE_ZIP) as source:
        roots = index_skill_roots(source)
        missing = [name for name in required_names if name not in roots]
        if missing:
            raise ValueError(f"Missing mapped skills in source ZIP: {', '.join(missing)}")
        selected_roots = {roots[name] for name in required_names}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as target:
            for member in source.infolist():
                if member.filename.split("/", 1)[0] in selected_roots:
                    target.writestr(member, source.read(member.filename))
            target.writestr("产品类型技能映射.json", mapping_text.encode("utf-8"))
            target.writestr(
                "README.md",
                (
                    "# Learn2Earn 14 种产品生成 Skills 包\n\n"
                    f"本包只包含当前 14 种产品类型所需的 {len(required_names)} 个去重 Skills。\n"
                    "映射详见 `产品类型技能映射.json`；每个 Skill 的说明位于其目录内 `SKILL.md`。\n"
                ).encode("utf-8"),
            )
    return output_path


def main() -> None:
    """Parse the output argument and build the curated artifact."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Destination .zip path")
    args = parser.parse_args()
    built = build_pack(args.output.resolve())
    print(built)


if __name__ == "__main__":
    main()
