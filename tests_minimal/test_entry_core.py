"""
test_entry_core.py - 入口与核心模块的最小化单元测试

覆盖范围（仅 6 个核心点，不依赖真实数据库/网络）：
    1. main.py 的 FastAPI 应用存在、lifespan 已挂载、路由已注册
    2. database.py 的 init_db/get_db 接口契约
    3. models.py 的三个模型（Subject/Note/Product）to_dict 序列化
    4. llm_service.py 的 is_ready / 默认提示词（无需真实调用）
    5. routers/notes.py 的 Pydantic 模型（创建/更新）
    6. 前端 useStore.js 的导出形态

运行：cd backend && python -m pytest ../tests_minimal/ -v
"""
import os
import sys
import json
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

# ==================== Path setup ====================
# 将 backend/ 加入 sys.path，使 `app.xxx` 可正常导入
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(THIS_DIR, "..", "backend"))
sys.path.insert(0, BACKEND_DIR)


# ==================== Test 1: FastAPI 入口应用 ====================
def test_fastapi_app_entry():
    """验证 FastAPI 应用可正确导入，并已挂载 lifespan 和路由"""
    from app.main import app, lifespan

    # 1) app 是 FastAPI 实例
    assert app is not None
    assert app.title == "Learn2Earn API"
    assert app.version == "1.0.0"

    # 2) lifespan 已挂载（现代模式，替代 on_event）
    assert app.router.lifespan_context is lifespan

    # 3) API 路由已注册；根路径由 StaticFiles 前端挂载处理
    paths = [r.path for r in app.routes]
    assert "/api/stats" in paths
    # 业务路由前缀必须存在
    assert any(p.startswith("/api/notes") for p in paths)
    assert any(p.startswith("/api/subjects") for p in paths)
    assert any(p.startswith("/api/products") for p in paths)
    assert any(p.startswith("/api/ai") for p in paths)


# ==================== Test 2: 数据库模块契约 ====================
def test_database_module_contract():
    """验证 database 模块的对外契约（不实际建表）"""
    from app.database import (
        engine,
        SessionLocal,
        Base,
        get_db,
        init_db,
        DATABASE_URL,
    )

    # 1) SQLite URL
    assert DATABASE_URL.startswith("sqlite:///")

    # 2) 引擎和 Session 工厂已创建
    assert engine is not None
    assert SessionLocal is not None

    # 3) Base 是 declarative_base 的实例
    assert Base is not None
    assert hasattr(Base, "metadata")

    # 4) get_db 是生成器函数
    import inspect
    assert inspect.isgeneratorfunction(get_db)

    # 5) init_db 存在且可调用
    assert callable(init_db)


# ==================== Test 3: ORM 模型 to_dict 序列化 ====================
def test_models_to_dict():
    """验证三个核心模型的 to_dict 序列化（含 None 安全处理）"""
    from datetime import datetime, timezone
    from app.models import Subject, Note, Product

    # 构造最小化 ORM 实例（绕过会话，模拟已填充的对象）
    subj = Subject(
        id=1, name="Python编程", icon="🐍",
        description="desc", color="#000000",
        total_hours=2.5,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    # 模拟未加载的关系
    subj.notes = []

    d = subj.to_dict()
    assert d["id"] == 1
    assert d["name"] == "Python编程"
    assert d["note_count"] == 0  # 安全处理 None notes
    assert d["created_at"] is not None

    note = Note(
        id=10, title="列表推导式", content="", raw_content="raw",
        subject_id=1, tags=None, learning_stage="stage2",
        estimated_minutes=15.0, is_completed=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    note.subject = None
    note.products = []
    d = note.to_dict()
    assert d["subject_name"] is None
    assert d["tags"] == []           # None → []
    assert d["product_count"] == 0  # None → 0

    prod = Product(
        id=100, title="面试题", product_type="interview_qa", content="...",
        subject_id=1, note_id=10,
        price_suggestion=19.9, platform_suggestion=None,
        keywords=None, estimated_value="¥19-99",
        export_format="markdown", status="draft",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    prod.note = None
    d = prod.to_dict()
    assert d["platform_suggestion"] == []
    assert d["keywords"] == []
    assert d["status"] == "draft"


# ==================== Test 4: LLM 服务可配置性 ====================
def test_llm_service_is_ready_and_prompt():
    """验证 LLM 服务的 is_ready 检查和默认系统提示词（不实际发请求）"""
    from app.services.llm_service import LLMService
    from app.services.llm_config import LLMConfig

    # 1) 未启用 + 空 api_key → 不可用
    cfg = LLMConfig(is_enabled=False, api_key="", base_url="", model="")
    svc = LLMService(cfg)
    assert svc.is_ready() is False

    # 2) 完全配置 + 启用 → 可用
    cfg2 = LLMConfig(
        is_enabled=True,
        api_key="sk-test",
        base_url="https://api.example.com/v1",
        model="gpt-4o-mini",
        max_tokens=2048,
        temperature=0.7,
    )
    svc2 = LLMService(cfg2)
    assert svc2.is_ready() is True

    # 3) Authorization 头格式正确
    assert svc2.headers["Authorization"] == "Bearer sk-test"
    assert svc2.headers["Content-Type"] == "application/json"

    # 4) 默认系统提示词非空且包含"知识付费"关键词
    assert svc2.system_prompt
    assert "知识付费" in svc2.system_prompt or "学习" in svc2.system_prompt


# ==================== Test 5: notes 路由的 Pydantic 模型 ====================
def test_notes_router_pydantic_models():
    """验证 notes 路由的请求/响应数据模型"""
    from app.routers.notes import NoteCreate, NoteUpdate

    # 1) 完整创建模型
    c = NoteCreate(title="test", subject_id=1)
    payload = c.model_dump()
    assert payload["title"] == "test"
    assert payload["subject_id"] == 1
    assert payload["learning_stage"] == "stage1"   # 默认值
    assert payload["is_completed"] is False        # 默认值

    # 2) 更新模型所有字段都是 None（部分更新语义）
    u = NoteUpdate()
    assert u.title is None
    assert u.is_completed is None
    assert u.model_dump(exclude_none=True) == {}   # exclude_none 过滤后为空


# ==================== Test 6: 前端 useStore 导出 ====================
def test_frontend_store_uses_zustand():
    """验证前端 useStore 正确使用 zustand create() 并导出 default"""
    # 前端文件是 JS（无 JSX 逻辑），仅做语法/导出形态校验
    store_path = os.path.abspath(os.path.join(
        BACKEND_DIR, "..", "frontend", "src", "store", "useStore.js"
    ))
    assert os.path.exists(store_path), f"未找到 useStore.js: {store_path}"

    with open(store_path, "r", encoding="utf-8") as f:
        src = f.read()

    # 1) 使用 zustand create
    assert "from 'zustand'" in src or 'from "zustand"' in src
    # 2) 暴露了全部业务字段
    for field in ("subjects", "notes", "products", "stats",
                  "fetchSubjects", "fetchNotes", "fetchProducts",
                  "generateProducts", "fetchStats"):
        assert field in src, f"useStore 缺少字段: {field}"
    # 3) 默认导出
    assert "export default useStore" in src


# ==================== Test 7 (额外): 根路径响应 ====================
def test_root_endpoint_serves_frontend():
    """验证 / 端点返回可启动 React 应用的 HTML。"""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert '<div id="root"></div>' in resp.text


# ==================== Test 8 (额外): 静态笔记列表接口契约 ====================
def test_notes_list_endpoint_contract():
    """验证 GET /api/notes 接口契约（无 DB 数据时返回空列表）"""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import create_local_token

    client = TestClient(app)
    token = create_local_token("minimal-test@example.com")["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    resp = client.get("/api/notes")
    assert resp.status_code == 200
    # 即使数据库为空，也应返回列表（而非 None 或报错）
    assert isinstance(resp.json(), list)
