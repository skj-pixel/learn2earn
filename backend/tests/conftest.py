# =============================================================================
# tests/conftest.py - pytest 共享 Fixtures 配置
# =============================================================================
# 提供所有测试用例可复用的 fixture（测试装置），包括：
#   - 数据库会话（内存 SQLite，测试间互不影响）
#   - FastAPI 测试客户端
#   - 预置测试数据（科目、笔记）
#
# 关键设计：使用 SQLite 内存数据库 → 每个测试函数独立、无副作用
# =============================================================================

import pytest                          # pytest 测试框架
import sys
import os

# 将 backend 目录加入 Python 路径，确保可以导入 app 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine    # 创建数据库引擎
from sqlalchemy.orm import sessionmaker # 创建会话工厂
from sqlalchemy.pool import StaticPool # 静态连接池（内存数据库专用）

# 导入应用组件
from app.database import Base, get_db  # ORM 基类和依赖注入函数
from app.auth import create_local_token
import app.cloud_db as cloud_db
from app.models import Subject, Note, Product  # 数据模型
from app.main import app               # FastAPI 应用实例

# --------------- 内存测试数据库配置 ---------------
# 使用 SQLite 内存数据库，每次测试结束自动销毁，测试间完全隔离
TEST_DATABASE_URL = "sqlite:///:memory:"

# 创建测试引擎
# connect_args={"check_same_thread": False} 允许跨线程（FastAPI 异步需要）
# poolclass=StaticPool 使用静态连接池，确保同一连接复用
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,               # 内存数据库专用连接池
)

# 创建测试会话工厂
TestSessionLocal = sessionmaker(
    autocommit=False,                   # 不自动提交
    autoflush=False,                    # 不自动刷新
    bind=test_engine,                   # 绑定到测试引擎
)


# =============================================================================
# Fixture: 数据库会话
# =============================================================================
@pytest.fixture(scope="function")      # scope="function": 每个测试函数独立运行
def db_session():
    """
    为每个测试函数提供独立的数据库会话

    生命周期：
        1. 创建所有表结构
        2. yield 数据库会话给测试函数
        3. 测试结束后回滚并删除所有表

    使用示例:
        def test_create_subject(db_session):
            subject = Subject(name="Test")
            db_session.add(subject)
            db_session.commit()
    """
    # 在测试引擎上创建所有表结构
    Base.metadata.create_all(bind=test_engine)

    # 创建新的数据库会话
    db = TestSessionLocal()
    try:
        yield db                       # 将会话交给测试函数
    finally:
        # 测试结束：回滚未提交内容 + 关闭会话
        db.rollback()
        db.close()
        # 删除所有表，确保下一个测试的数据库是干净的
        Base.metadata.drop_all(bind=test_engine)


# =============================================================================
# Fixture: FastAPI 测试客户端
# =============================================================================
@pytest.fixture(scope="function")
def client(db_session):
    """
    提供 FastAPI TestClient，并重写依赖注入为测试数据库会话

    工作原理：
        1. 重写 get_db 依赖 → 使用测试数据库而非生产数据库
        2. 创建 TestClient 用于发送 HTTP 请求
        3. 测试结束后恢复原始依赖

    使用示例:
        def test_api(client):
            response = client.get("/api/subjects")
            assert response.status_code == 200
    """
    # 重写 FastAPI 的 get_db 依赖注入
    # 使所有 API 路由使用测试数据库会话
    def override_get_db():
        try:
            yield db_session            # 提供测试数据库会话
        finally:
            pass                        # 由 db_session fixture 负责清理

    # 应用依赖覆盖
    app.dependency_overrides[get_db] = override_get_db
    cloud_db.SessionLocal = TestSessionLocal

    # 导入 TestClient 并创建实例
    from fastapi.testclient import TestClient
    test_client = TestClient(app)
    token = create_local_token("pytest@example.com")["access_token"]
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    # yield 测试客户端
    yield test_client

    # 清理：移除依赖覆盖
    app.dependency_overrides.clear()


# =============================================================================
# Fixture: 预置测试科目
# =============================================================================
@pytest.fixture
def sample_subject(db_session):
    """
    创建一个预置测试科目并返回

    Returns:
        Subject: 已保存的科目 ORM 对象
    """
    subject = Subject(
        name="Python编程",
        icon="🐍",
        description="Python入门到精通",
        color="#3b82f6",
    )
    db_session.add(subject)             # 加入会话
    db_session.commit()                 # 提交
    db_session.refresh(subject)         # 刷新以获取 id 和时间戳
    return subject


# =============================================================================
# Fixture: 预置测试笔记（含内容）
# =============================================================================
@pytest.fixture
def sample_note(db_session, sample_subject):
    """
    创建一个预置测试笔记，关联到 sample_subject

    Returns:
        Note: 已保存的笔记 ORM 对象
    """
    note = Note(
        title="Python列表推导式学习",
        raw_content="""# Python 列表推导式

## 基本语法
列表推导式是Python中创建列表的简洁方式。
语法：[表达式 for 变量 in 可迭代对象]

## 代码示例
```python
# 基础用法：生成平方数列表
squares = [x**2 for x in range(10)]
print(squares)  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]

# 带条件过滤
evens = [x for x in range(20) if x % 2 == 0]
print(evens)  # [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]
```

## 进阶技巧
- 可以嵌套多层循环
- 可以结合三元表达式
- 性能优于传统for循环

## 常见坑点
1. 不要写过于复杂的推导式（影响可读性）
2. 注意内存占用（大量数据时考虑生成器表达式）
""",
        subject_id=sample_subject.id,       # 关联到测试科目
        tags=["Python", "基础", "列表"],     # 预置标签
        learning_stage="stage1",             # 筑基期
        estimated_minutes=45,
    )
    db_session.add(note)
    db_session.commit()
    db_session.refresh(note)
    return note
