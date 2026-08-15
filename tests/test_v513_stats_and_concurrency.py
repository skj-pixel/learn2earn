from pathlib import Path
import sqlite3


ROOT = Path(__file__).resolve().parents[1]


def test_dashboard_value_uses_the_same_visible_products_as_product_list():
    source = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert "from .cloud_db import count_rows, sum_product_value, table" in source
    assert "visible_products = table(\"products\", user).list()" in source
    assert "sum(float(item.get(\"price_suggestion\") or 0) for item in visible_products)" in source
    assert "total_value = sum_product_value(user_id)" not in source


def test_read_paths_retry_sqlite_lock_without_returning_empty_state():
    db = (ROOT / "backend/app/cloud_db.py").read_text(encoding="utf-8")
    store = (ROOT / "frontend/src/store/useStore.js").read_text(encoding="utf-8")
    assert "database is locked" in db.lower()
    assert "retry_safe=True" in db
    fetch_products = store.split("fetchProducts: async", 1)[1].split("createProduct:", 1)[0]
    assert "set({ error: e.message })" in fetch_products
    assert "products: []" not in fetch_products
    assert "return get().products" in fetch_products


def test_strategy_and_skill_endpoints_use_lock_safe_reads():
    workspace = (ROOT / "backend/app/routers/workspace.py").read_text(encoding="utf-8")
    generator = (ROOT / "frontend/src/components/ProductGenerator.jsx").read_text(encoding="utf-8")
    assert 'skills_table.list_skill_summaries' in workspace
    assert "Promise.allSettled" in generator
    assert "部分数据暂时繁忙，已保留现有内容" in generator


def test_sqlite_wal_allows_reads_while_a_generation_write_is_open(tmp_path):
    database = tmp_path / "concurrent.db"
    writer = sqlite3.connect(database, timeout=1)
    writer.execute("pragma journal_mode=wal")
    writer.execute("create table products (id integer primary key, title text)")
    writer.execute("insert into products(title) values ('历史产品')")
    writer.commit()

    writer.execute("begin immediate")
    writer.execute("insert into products(title) values ('生成中的产品')")
    reader = sqlite3.connect(database, timeout=1)
    try:
        assert reader.execute("select title from products").fetchall() == [("历史产品",)]
    finally:
        reader.close()
        writer.rollback()
        writer.close()


def test_fixed_release_prefers_dependencies_from_the_version_worktree():
    launcher = (ROOT / "scripts/start_fixed_release.ps1").read_text(encoding="utf-8")
    assert "$dependencyModules = Join-Path $codeRepo 'frontend\\node_modules'" in launcher
    assert "'.bin\\vite.cmd'" in launcher
    assert "npm.cmd --prefix (Join-Path $codeRepo 'frontend') ci" in launcher


def test_v513_launcher_inherits_v512_data_without_writing_to_it():
    launcher = (ROOT / "Start-Learn2Earn-V5.1.3.ps1").read_text(encoding="utf-8")
    batch = (ROOT / "启动Learn2Earn-V5.1.3统计与并发读取修复版.bat").read_bytes()
    assert "v5.1.2-restored.2" in launcher
    assert "Creating an independent data copy" in launcher
    assert "Copy-Item -LiteralPath $sourceData -Destination $targetData -Recurse" in launcher
    assert all(byte < 128 for byte in batch)
    assert b'set "LEARN2EARN_HISTORY_REPO=%~dp0"' in batch
    assert b'pause' in batch
