# 🔍 [语法] 模块级 docstring（占位说明，TODO 自动化生成）
# 🔍 [作用] 标记本模块用途——数据库配置
# 🔍 [陷阱] 该 TODO 应人工补全实际功能说明
"""
把学习过程变成赚钱过程的app/backend/app/database.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# database.py - 数据库配置模块
# =============================================================================
# 功能：
#   1. 配置 SQLite 数据库引擎和连接
#   2. 提供 FastAPI 依赖注入的数据库会话获取器
#   3. 提供数据库表结构初始化函数
# =============================================================================

# --------------- 导入依赖 ---------------

# 🔍 [语法] from sqlalchemy import create_engine
# 🔍 [作用] 导入 SQLAlchemy 引擎工厂函数，用于创建数据库连接
# 🔍 [关联] SQLAlchemy 是 Python 最流行的 ORM 库
# 🔍 [陷阱] 不同数据库需用不同驱动（sqlite/postgresql/mysql）
from sqlalchemy import create_engine

# 🔍 [语法] from sqlalchemy.orm import declarative_base, sessionmaker
# 🔍 [作用] declarative_base 返回 ORM 模型基类；sessionmaker 创建 Session 工厂
# 🔍 [示例] 所有 ORM 模型类（如 models.py 中的 Subject/Note/Product）都继承 Base
# 🔍 [陷阱] SQLAlchemy 2.0 推荐用 DeclarativeBase，新风格更类型友好
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import QueuePool

# 🔍 [语法] import os
# 🔍 [作用] 导入操作系统接口，用于路径拼接
# 🔍 [示例] os.path.join 跨平台拼接路径
# 🔍 [陷阱] 不要硬编码路径分隔符（用 os.path.join）
import os
from pathlib import Path

# --------------- 数据库路径配置 ---------------

# 🔍 [语法] os.path.dirname(os.path.abspath(__file__))
# 🔍 [作用] 获取当前文件所在目录的绝对路径（即 backend/app/）
# 🔍 [示例] __file__ = "backend/app/database.py" → 绝对路径 → dirname = "backend/app"
# 🔍 [陷阱] abspath 解析符号链接；realpath 不解析（视需求选择）
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔍 [语法] f-string + os.path.join
# 🔍 [作用] 拼接 SQLite 数据库文件路径 → backend/app/learn2earn.db
# 🔍 [示例] "sqlite:////绝对路径/learn2earn.db"（sqlite:/// 三斜杠 + 绝对路径）
# 🔍 [陷阱] Windows 路径含反斜杠会报错，应用正斜杠或用 sqlite://// 前缀
DEFAULT_DATABASE_PATH = Path(BASE_DIR) / "learn2earn.db"
DATABASE_PATH = Path(os.environ.get("LEARN2EARN_DATABASE_PATH", DEFAULT_DATABASE_PATH)).expanduser().resolve()
if not DATABASE_PATH.parent.is_dir():
    raise RuntimeError(f"Database directory does not exist: {DATABASE_PATH.parent}")
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

# --------------- 数据库引擎 ---------------

# 🔍 [语法] create_engine(url, **connect_args)
# 🔍 [作用] 创建 SQLAlchemy 数据库引擎（连接池）
# 🔍 [关联] engine 是数据库连接的核心，被 SessionLocal 引用
# 🔍 [陷阱] SQLite 多线程需要 check_same_thread=False（FastAPI 异步必须）
# 🔍 [示例] 生产可改为 "postgresql://user:pass@host:5432/db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    pool_pre_ping=True,
    poolclass=QueuePool,
    pool_size=3,
    max_overflow=0,
)

# --------------- 会话工厂 ---------------

# 🔍 [语法] sessionmaker(autocommit=False, autoflush=False, bind=engine)
# 🔍 [作用] 创建 Session 工厂；绑定到上面创建的引擎
# 🔍 [示例] SessionLocal() 创建一个新会话
# 🔍 [陷阱] autocommit=False 需要手动 db.commit()；autoflush=False 需要手动 db.flush()
# 🔍 [陷阱] 不 commit 会导致数据未持久化；不 flush 会导致查询不到刚 add 的对象
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --------------- 声明式基类 ---------------

# 🔍 [语法] declarative_base()
# 🔍 [作用] 创建 ORM 模型的声明式基类
# 🔍 [示例] models.py 中的 class Subject(Base): ... 继承此 Base
# 🔍 [陷阱] 必须先 import Base，再定义继承它的模型
Base = declarative_base()


# 🔍 [语法] def get_db(): + yield
# 🔍 [作用] FastAPI 依赖注入函数，每次请求返回新 Session，请求结束自动关闭
# 🔍 [关联] 在路由函数中通过 Depends(get_db) 调用
# 🔍 [示例] def get_user(db: Session = Depends(get_db)): db.query(User).all()
# 🔍 [陷阱] 必须用 try/finally + yield 才能保证关闭（异常路径也要关闭）
def get_db():
    """
    FastAPI 依赖注入：获取数据库会话

    用法（在 FastAPI 路由函数中）：
        @app.get("/items")
        def list_items(db: Session = Depends(get_db)):
            ...

    Yields:
        Session: SQLAlchemy 数据库会话，请求结束后自动关闭
    """
    # 🔍 [语法] SessionLocal() 实例化
    # 🔍 [作用] 创建一个新的数据库会话
    # 🔍 [陷阱] 每个请求都应该创建新会话（不要跨请求共享）
    db = SessionLocal()

    # 🔍 [语法] try ... finally:
    # 🔍 [作用] 保证无论请求成功或失败，db.close() 都会被执行
    # 🔍 [陷阱] 如果没有 try/finally，请求异常时连接会泄漏
    try:
        # 🔍 [语法] yield db
        # 🔍 [作用] 把 db 暂停并返回给调用者（路由函数），请求结束后回到 finally
        # 🔍 [示例] FastAPI 会在 yield 处注入，路由函数执行完后回到 finally
        yield db
    finally:
        # 🔍 [语法] db.close()
        # 🔍 [作用] 关闭会话，释放连接到连接池
        # 🔍 [陷阱] 即使 SQLAlchemy 2.0 推荐用 with statement，这里仍显式 close 更明确
        db.close()


# 🔍 [语法] def init_db():
# 🔍 [作用] 初始化数据库表结构（create_all）
# 🔍 [关联] 在 main.py 的 lifespan 中调用
# 🔍 [示例] init_db() 会在应用启动时执行一次
# 🔍 [陷阱] create_all 不会更新已存在的表结构（生产用 Alembic 迁移）
def init_db():
    """
    初始化数据库：根据 ORM 模型定义自动创建所有表结构

    执行时机：FastAPI 应用启动时（@app.on_event("startup")）
    特性：如果表已存在则跳过（不会覆盖现有数据）
    """
    # 🔍 [语法] Base.metadata.create_all(bind=engine)
    # 🔍 [作用] 遍历所有继承 Base 的模型类，自动在数据库中创建对应表
    # 🔍 [示例] Subject → subjects 表，Note → notes 表，Product → products 表
    # 🔍 [陷阱] 不会添加新列到已存在的表（需 Alembic 迁移）
    # 🔍 [陷阱] 不会删除列（drop_all 才会）
    Base.metadata.create_all(bind=engine)
    # 🔍 [作用] 兼容已有本地库：给已存在的表补加新列
    # 🔍 [陷阱] create_all 不会给已存在表加列，这里用 PRAGMA 探测后 ALTER
    _ensure_new_columns(engine)


def _ensure_new_columns(engine):
    """给已存在的本地 SQLite 表补加新列（create_all 不会做这件事）。"""
    from sqlalchemy import inspect as _sa_inspect, text

    _EXPECTED = {
        "products": ["generation_meta", "user_id"],
        "generation_tasks": ["product_strategies"],
    }
    try:
        insp = _sa_inspect(engine)
        available_tables = set(insp.get_table_names())
        with engine.connect() as conn:
            for table, columns in _EXPECTED.items():
                if table not in available_tables:
                    continue
                existing = {c["name"] for c in insp.get_columns(table)}
                for col in columns:
                    if col not in existing:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} TEXT"))
                        conn.commit()
    except Exception:
        # 云模式或非 SQLite 时静默忽略，不影响启动
        pass
