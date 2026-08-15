# 🔍 [语法] 模块级 docstring（占位）
"""
把学习过程变成赚钱过程的app/backend/app/models.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# models.py - ORM 数据模型定义
# =============================================================================
# 定义了三个核心数据模型：
#   1. Subject  - 学习科目（如 Python、嵌入式、英语等）
#   2. Note    - 学习笔记（对应每次学习记录）
#   3. Product - 知识付费产品（从笔记中 AI 自动生成）
#
# 模型关系：
#   Subject (1) ──→ (N) Note (1) ──→ (N) Product
#   一个科目下有多篇笔记，一篇笔记可生成多个知识付费产品
# =============================================================================

# --------------- 导入依赖 ---------------

# 🔍 [语法] 多 Column 类型从 sqlalchemy 导入
# 🔍 [作用] 各种数据库列类型（Integer/Text/Boolean/JSON 等）
# 🔍 [示例] Column(Integer, primary_key=True) 定义主键
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, JSON, ForeignKey

# 🔍 [语法] 从 sqlalchemy.orm 导入 relationship
# 🔍 [作用] ORM 关系映射（一对多、多对一）
# 🔍 [示例] notes = relationship("Note", back_populates="subject")  # 反向引用
from sqlalchemy.orm import relationship

# 🔍 [语法] 从 datetime 导入 datetime 和 timezone
# 🔍 [作用] UTC 时间处理
# 🔍 [陷阱] 旧版 utcnow() 已弃用，必须用 datetime.now(timezone.utc)
from datetime import datetime, timezone, timedelta

# 🔍 [语法] 相对导入（.database）
# 🔍 [作用] 导入 Base（所有模型继承它）
from .database import Base


# 🔍 [语法] lambda 表达式赋值给变量
# 🔍 [作用] 工厂函数：每次调用返回新的本地（与 UI 一致的北京时间）当前时间
# 🔍 [陷阱] 之前使用 datetime.now(timezone.utc) 写入 SQLite 时会被剥离 tzinfo，
#          前端 toLocaleString('zh-CN') 把无时区字符串视为本地时间，比真实 UTC 慢 8 小时。
#          本地模式以本地时间写入，前端展示与北京时钟一致。
# 🔍 [示例] created_at = Column(DateTime, default=_utc_now)  # 插入时自动填入当前本地时间
_utc_now = lambda: datetime.now()


# 🔍 [语法] 模块级常量：时间戳序列化助手
# 🔍 [作用] 修复新老数据混存的 8 小时偏差。
#          新数据（>=此阈值）以本地时间写入 → 输出 +08:00；
#          旧数据（<此阈值）以 UTC 时间写入 → 输出 +00:00；
#          这样前端 new Date() 解析后 toLocaleString 都与北京时间一致。
# 🔍 [陷阱] 阈值定位 2026-08-08 00:00:00 之前的所有历史数据按 UTC 解析（与本任务时间锚点对应）。
_LOCAL_TZ_OFFSET = timezone(timedelta(hours=8))
# 阈值：2026-08-08 00:00:00（这是项目从 UTC-naive 改为 local-naive 的切换点）
_HYBRID_CUTOFF = datetime(2026, 8, 8, 0, 0, 0)


def _serialize_timestamp(value):
    """将 DB 中的 naive timestamp 序列化为带时区的 ISO 字符串。

    老数据（_HYBRID_CUTOFF 之前）以 UTC 写入 → 加 +00:00 后缀；
    新数据（_HYBRID_CUTOFF 之后）以本地时间写入 → 加 +08:00 后缀。
    """
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.isoformat()
    if value < _HYBRID_CUTOFF:
        return value.replace(tzinfo=timezone.utc).isoformat()
    return value.replace(tzinfo=_LOCAL_TZ_OFFSET).isoformat()


# =============================================================================
# Subject - 学习科目模型
# =============================================================================

# 🔍 [语法] class ModelName(Base): 继承声明式基类
# 🔍 [作用] ORM 模型类继承 Base 后，自动映射到数据库表
# 🔍 [示例] Subject → subjects 表
# 🔍 [陷阱] 表名必须与 PostgreSQL 保留字不冲突（避免 user/order 等）
class Subject(Base):
    """
    学习科目表 - 存储用户添加的所有学习科目
    """
    # 🔍 [语法] 类属性 __tablename__
    # 🔍 [作用] 自定义数据库表名（默认用类名小写）
    # 🔍 [陷阱] 必须显式声明，否则 SQLAlchemy 会用类名小写
    __tablename__ = "subjects"

    # ---------- 主键 ----------
    # 🔍 [语法] Column(Integer, primary_key=True, index=True)
    # 🔍 [作用] 定义自增主键 + 索引（加速主键查询）
    # 🔍 [陷阱] SQLite/PostgreSQL 都支持 Integer 主键自增
    id = Column(Integer, primary_key=True, index=True)

    # ---------- 基本信息 ----------
    # 🔍 [语法] Column(String(N), nullable=False)
    # 🔍 [作用] 最大 100 字符的非空字符串
    # 🔍 [陷阱] String(N) 是提示而非强约束（数据库层才会强制）
    name = Column(String(100), nullable=False)

    # 🔍 [语法] Column(String(N), default="📚")
    # 🔍 [作用] 默认书本 emoji 图标
    # 🔍 [陷阱] String 列存 emoji 占用 4 字节/字符（UTF-8）
    icon = Column(String(50), default="📚")

    # 🔍 [语法] Column(Text, default="")
    # 🔍 [作用] 不限长度的文本（用于描述）
    # 🔍 [陷阱] Text 在 SQLite 中等价于 VARCHAR（无长度限制）
    description = Column(Text, default="")

    # 🔍 [语法] Column(String(20)) + HEX 颜色
    # 🔍 [作用] 存储主题色（前端 Tailwind 用）
    # 🔍 [陷阱] 颜色格式未做正则校验（如 #RRGGBB）
    color = Column(String(20), default="#6366f1")

    # ---------- 统计字段 ----------
    # 🔍 [语法] Column(Float, default=0)
    # 🔍 [作用] 累计学习时长（小时，支持小数 2.5）
    # 🔍 [陷阱] 浮点数累加可能有精度问题（用 Decimal 更精确）
    total_hours = Column(Float, default=0)

    # ---------- 时间戳 ----------
    # 🔍 [语法] Column(DateTime, default=_utc_now)
    # 🔍 [作用] 插入时自动填入当前 UTC 时间
    # 🔍 [陷阱] Python 函数引用（不调用）作为 default，SQLAlchemy 会自动调用
    created_at = Column(DateTime, default=_utc_now)

    # 🔍 [语法] onupdate=_utc_now
    # 🔍 [作用] 每次 UPDATE 时自动刷新时间戳
    # 🔍 [陷阱] 仅在 SQLAlchemy 1.4+ 的 ORM 模式下生效
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    # ---------- ORM 关系 ----------
    # 🔍 [语法] relationship("ClassName", back_populates="...", cascade=...)
    # 🔍 [作用] 一对多关系（一个 Subject 多个 Note）；级联删除
    # 🔍 [陷阱] cascade="all, delete-orphan" 删除 Subject 时自动删除所有 Note
    notes = relationship("Note", back_populates="subject", cascade="all, delete-orphan")

    # 🔍 [语法] def 方法 + self
    # 🔍 [作用] 自定义方法：将 ORM 对象转为 dict（用于 JSON 序列化）
    # 🔍 [陷阱] ORM 对象不能直接 JSON 序列化，必须 to_dict()
    def to_dict(self):
        # 🔍 [语法] dict 字面量
        # 🔍 [作用] 返回包含所有字段的字典
        return {
            "id": self.id,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "color": self.color,
            "total_hours": self.total_hours,
            # 🔍 [语法] 三元表达式 + len() + bool
            # 🔍 [作用] 安全获取关系数量（防止 lazy loading 报错）
            # 🔍 [陷阱] 直接访问 self.notes 可能触发额外查询（lazy load）
            "note_count": len(self.notes) if self.notes else 0,
            # 🔍 [语法] .isoformat() 方法
            # 🔍 [作用] 时间转 ISO 8601 字符串（前端可直接用）
            # 🔍 [陷阱] 无效时间会返回 None
            "created_at": _serialize_timestamp(self.created_at),
            "updated_at": _serialize_timestamp(self.updated_at),
        }


# =============================================================================
# Note - 学习笔记模型
# =============================================================================

# 🔍 [语法] class ModelName(Base)
# 🔍 [作用] 笔记模型，关联到 Subject
class Note(Base):
    """学习笔记表 - 存储每次学习记录和笔记内容"""
    # 🔍 [语法] __tablename__
    __tablename__ = "notes"

    # ---------- 主键 ----------
    id = Column(Integer, primary_key=True, index=True)

    # ---------- 内容字段 ----------
    # 🔍 [语法] String(200)
    # 🔍 [作用] 标题最长 200 字符（够用即可）
    # 🔍 [陷阱] UI 显示需考虑截断（line-clamp）
    title = Column(String(200), nullable=False)

    # 🔍 [语法] Text, default=""
    # 🔍 [作用] 保留字段（可为富文本/Markdown 格式，当前版本暂用 raw_content）
    content = Column(Text, default="")

    # 🔍 [语法] Text, default=""
    # 🔍 [作用] 原始学习笔记纯文本（AI 产品生成器的核心输入源）
    # 🔍 [陷阱] 大文本影响性能（应分块存储或索引）
    raw_content = Column(Text, default="")

    # ---------- 外键 ----------
    # 🔍 [语法] ForeignKey("table.column")
    # 🔍 [作用] 外键约束，确保 subject_id 存在于 subjects.id
    # 🔍 [陷阱] 数据库层约束；ORM 层不强制（懒加载）
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    # ---------- 分类与统计 ----------
    # 🔍 [语法] JSON, default=[]
    # 🔍 [作用] 存储 JSON 数组（SQLite 中存储为 TEXT）
    # 🔍 [陷阱] JSON 字段无索引，频繁查询需重建为关联表
    tags = Column(JSON, default=[])

    # 🔍 [语法] String(50), default="stage1"
    # 🔍 [作用] 学习阶段枚举（stage1-4）
    learning_stage = Column(String(50), default="stage1")

    # 🔍 [语法] Float, default=30
    # 🔍 [作用] 预估学习时长（分钟）
    estimated_minutes = Column(Float, default=30)

    # 🔍 [语法] Boolean, default=False
    # 🔍 [作用] 是否完成学习
    is_completed = Column(Boolean, default=False)

    # ---------- 时间戳 ----------
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    # ---------- ORM 关系 ----------
    # 🔍 [语法] relationship("ClassName", back_populates=...)
    # 🔍 [作用] 多对一关系（一篇笔记属于一个科目）
    subject = relationship("Subject", back_populates="notes")

    # 🔍 [语法] cascade="all, delete-orphan"
    # 🔍 [作用] 删除笔记时级联删除所有产品
    products = relationship("Product", back_populates="note", cascade="all, delete-orphan")

    # 🔍 [语法] def 方法
    # 🔍 [作用] ORM 对象转字典
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "raw_content": self.raw_content,
            "subject_id": self.subject_id,
            # 🔍 [语法] 可选链 + 三元
            # 🔍 [作用] 安全获取关联科目名称
            "subject_name": self.subject.name if self.subject else None,
            # 🔍 [语法] 逻辑或
            # 🔍 [作用] JSON 字段可能为 None，统一返回 []
            "tags": self.tags or [],
            "learning_stage": self.learning_stage,
            "estimated_minutes": self.estimated_minutes,
            "is_completed": self.is_completed,
            # 🔍 [语法] 同 Subject.to_dict 的安全获取
            "product_count": len(self.products) if self.products else 0,
            "created_at": _serialize_timestamp(self.created_at),
            "updated_at": _serialize_timestamp(self.updated_at),
        }


# =============================================================================
# Product - 知识付费产品模型
# =============================================================================

# 🔍 [语法] class ModelName(Base)
# 🔍 [作用] 知识付费产品表（13 种产品类型之一）
class Product(Base):
    """知识付费产品表 - 存储 AI 从笔记中自动生成的各种知识付费产品"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # 🔍 [语法] String(120), nullable=True, index
    # 🔍 [作用] 2026-08 安全修复：本地模式按用户隔离产品（云端 schema 早有此列）
    # 🔍 [陷阱] nullable=True 兼容旧本地库；cloud_db CRUD 抽象在 hasattr 时自动注入/过滤
    user_id = Column(String(120), nullable=True, index=True)

    # ---------- 基本信息 ----------
    # 🔍 [语法] String(200), nullable=False
    # 🔍 [作用] 产品标题（必填）
    title = Column(String(200), nullable=False)

    # 🔍 [语法] String(50), nullable=False
    # 🔍 [作用] 产品类型枚举值（13 种之一）
    # 🔍 [陷阱] 类型值必须与 services/product_generator.py 的 PRODUCT_TYPES 一致
    product_type = Column(String(50), nullable=False)

    # ---------- 内容字段 ----------
    # 🔍 [语法] Text, default=""
    # 🔍 [作用] 产品正文内容（Markdown 格式）
    content = Column(Text, default="")

    # ---------- 外键 ----------
    # 🔍 [语法] ForeignKey + nullable=False
    # 🔍 [作用] 关联到所属科目（必填）
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

    # 🔍 [语法] ForeignKey + nullable=True
    # 🔍 [作用] 关联到源笔记（可空：产品可不来源于任何笔记）
    # 🔍 [陷阱] nullable=True 允许独立产品存在（人工创建的非 AI 产品）
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=True)

    # ---------- 变现相关 ----------
    # 🔍 [语法] Float, default=0
    # 🔍 [作用] AI 建议的售价（元）
    # 🔍 [陷阱] 实际售价由用户决定；建议价仅供参考
    price_suggestion = Column(Float, default=0)

    # 🔍 [语法] JSON, default=[]
    # 🔍 [作用] AI 建议的售卖平台列表
    platform_suggestion = Column(JSON, default=[])

    # 🔍 [语法] JSON, default=[]
    # 🔍 [作用] 产品关键词列表（便于搜索和平台标签）
    keywords = Column(JSON, default=[])

    # 🔍 [语法] String(50), default=""
    # 🔍 [作用] 预估收益范围描述（如 "¥19-199"）
    # 🔍 [陷阱] 用 String 而非 Float 是为了保留范围表达
    estimated_value = Column(String(50), default="")

    # ---------- 导出与状态 ----------
    # 🔍 [语法] String(20), default="markdown"
    # 🔍 [作用] 导出文件格式（markdown / pdf / html / image）
    export_format = Column(String(20), default="markdown")

    # 🔍 [语法] String(20), default="draft"
    # 🔍 [作用] 产品发布状态（draft / published / archived）
    # 🔍 [陷阱] status 字段是字符串而非 Enum（数据库层不强制）
    status = Column(String(20), default="draft")

    # 🔍 [语法] JSON, default={}
    # 🔍 [作用] 生成溯源：记录本次生成选用的 skill_ids / algorithms / techniques / skill_names
    # 🔍 [陷阱] 每种产品可独立携带默认/自定义的生成策略，便于复现与质量追溯
    generation_meta = Column(JSON, default={})

    # ---------- 时间戳 ----------
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    # ---------- ORM 关系 ----------
    # 🔍 [语法] 多对一关系（产品属于笔记）
    note = relationship("Note", back_populates="products")

    # 🔍 [语法] def 方法
    # 🔍 [作用] ORM 对象转字典
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "product_type": self.product_type,
            "content": self.content,
            "subject_id": self.subject_id,
            "note_id": self.note_id,
            "price_suggestion": self.price_suggestion,
            "platform_suggestion": self.platform_suggestion or [],
            "keywords": self.keywords or [],
            "estimated_value": self.estimated_value,
            "export_format": self.export_format,
            "status": self.status,
            "generation_meta": self.generation_meta or {},
            "created_at": _serialize_timestamp(self.created_at),
            "updated_at": _serialize_timestamp(self.updated_at),
        }


class NoteAsset(Base):
    """Image or attachment extracted from an imported note."""
    __tablename__ = "note_assets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    note_id = Column(Integer, nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    media_type = Column(String(100), default="application/octet-stream")
    storage_path = Column(Text, nullable=False)
    source_anchor = Column(String(120), default="")
    size_bytes = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utc_now)

    def to_dict(self):
        return {
            "id": self.id, "note_id": self.note_id, "filename": self.filename,
            "media_type": self.media_type, "source_anchor": self.source_anchor,
            "size_bytes": self.size_bytes,
            "url": f"/api/assets/{self.id}",
            "created_at": _serialize_timestamp(self.created_at),
        }


class InstalledSkill(Base):
    """User-owned prompt skill. Files are stored, but never executed by the server."""
    __tablename__ = "installed_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    category = Column(String(100), default="通用")
    instructions = Column(Text, default="")
    storage_path = Column(Text, nullable=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "category": self.category, "enabled": self.enabled,
            "instruction_chars": len(self.instructions or ""),
            "created_at": _serialize_timestamp(self.created_at),
            "updated_at": _serialize_timestamp(self.updated_at),
        }


class GenerationTask(Base):
    """Persistent task metadata for navigation-safe product generation."""
    __tablename__ = "generation_tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(120), nullable=False, index=True)
    note_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=True, index=True)
    product_types = Column(JSON, default=[])
    skill_ids = Column(JSON, default=[])
    algorithms = Column(JSON, default=[])
    techniques = Column(JSON, default=[])
    # 🔍 [作用] 2026-08 feat/29：每产品类型独立 strategy；key=product_type, value={skill_ids, algorithms, techniques}
    # 旧数据无此字段 → 默认空 dict，后端会用 task 级 / 策略偏好兜底
    product_strategies = Column("product_strategies", JSON, default={})
    status = Column(String(30), default="queued", index=True)
    progress = Column(Integer, default=0)
    current_step = Column(String(255), default="等待执行")
    error = Column(Text, default="")
    result = Column(JSON, default={})
    created_at = Column(DateTime, default=_utc_now)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    def to_dict(self):
        return {
            "id": self.id, "note_id": self.note_id, "product_id": self.product_id,
            "product_types": self.product_types or [], "skill_ids": self.skill_ids or [],
            "algorithms": self.algorithms or [], "techniques": self.techniques or [],
            # 🔍 [作用] 2026-08 feat/29：每个产品类型的独立 strategy 透出给前端
            "product_strategies": self.product_strategies or {},
            "status": self.status, "progress": self.progress,
            "current_step": self.current_step, "error": self.error,
            "result": self.result or {},
            "created_at": _serialize_timestamp(self.created_at),
            "started_at": _serialize_timestamp(self.started_at),
            "completed_at": _serialize_timestamp(self.completed_at),
            "updated_at": _serialize_timestamp(self.updated_at),
        }
