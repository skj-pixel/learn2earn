# 🔍 [语法] 类型注解导入
# 🔍 [作用] Any 用于 dict value 类型；quote 用于 URL 编码
from typing import Any
import time

# 🔍 [语法] from urllib.parse import quote
# 🔍 [作用] quote 用于 URL 编码（PostgREST filter 参数）
# 🔍 [陷阱] 不编码可能含特殊字符的值会导致请求失败
from urllib.parse import quote

# 🔍 [语法] httpx 导入
# 🔍 [作用] 同步 HTTP 客户端（调 Supabase REST API）
import httpx

# 🔍 [语法] FastAPI 异常
# 🔍 [作用] 把 Supabase 错误转为 HTTP 响应
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError
from sqlalchemy import func, or_

# 🔍 [语法] 相对导入
# 🔍 [作用] 复用 auth 模块的认证工具
from .auth import auth_headers, cloud_is_configured, require_cloud, supabase_url

# 🔍 [语法] 数据库会话导入
# 🔍 [作用] 本地模式用 SQLAlchemy Session
from .database import SessionLocal

# 🔍 [语法] ORM 模型导入
# 🔍 [作用] 本地模式用 ORM 类操作表
from .models import GenerationTask, InstalledSkill, Note, NoteAsset, Product, Subject


# 🔍 [语法] dict literal（模块级常量）
# 🔍 [作用] 表名 → ORM 类的映射（用于本地模式）
# 🔍 [陷阱] 增删表必须同步更新
LOCAL_MODELS = {
    "subjects": Subject,
    "notes": Note,
    "products": Product,
    "note_assets": NoteAsset,
    "installed_skills": InstalledSkill,
    "generation_tasks": GenerationTask,
}

def _is_transient_database_open_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return isinstance(exc, OperationalError) and any(marker in message for marker in (
        "unable to open database file", "database is locked", "database is busy",
    ))


def _run_local_operation(operation, *, retry_safe: bool = False):
    """Retry transient open failures only for operations without write side effects."""
    for attempt in range(8):
        try:
            return operation()
        except OperationalError as exc:
            if not retry_safe or not _is_transient_database_open_error(exc) or attempt == 7:
                raise
            time.sleep(min(0.1 * (2 ** attempt), 1.0))


# 🔍 [语法] def + f-string
# 🔍 [作用] 构造 Supabase REST API 表 URL
# 🔍 [示例] https://abc.supabase.co/rest/v1/subjects
def _rest_url(table: str) -> str:
    return f"{supabase_url()}/rest/v1/{table}"


# 🔍 [语法] 函数 + Optional return
# 🔍 [作用] 统一处理 Supabase HTTP 响应（错误转 HTTPException）
# 🔍 [关联] 所有云模式方法都调用此函数
# 🔍 [陷阱] 错误时优先用 JSON（结构化），失败才用 text
def _handle(response: httpx.Response) -> Any:
    # 🔍 [语法] >= 400 错误判断
    # 🔍 [作用] 4xx 客户端错误 + 5xx 服务端错误
    if response.status_code >= 400:
        # 🔍 [语法] try/except + ValueError
        # 🔍 [作用] 尝试 JSON 解析；失败回退到文本
        try:
            detail = response.json()
        except ValueError:
            detail = response.text
        # 🔍 [语法] raise HTTPException with status_code 透传
        # 🔍 [作用] 把 Supabase 错误状态码和详情透传给客户端
        raise HTTPException(status_code=response.status_code, detail=detail)

    # 🔍 [语法] not response.content
    # 🔍 [作用] 空响应体（如 204）返回 None
    if not response.content:
        return None

    # 🔍 [语法] response.json()
    # 🔍 [作用] 解析 JSON 响应
    return response.json()


# 🔍 [语法] class ClassName + __init__
# 🔍 [作用] 云模式表操作封装
# 🔍 [关联] table() 工厂根据配置返回 CloudTable 或 LocalTable
# 🔍 [陷阱] 必须 require_cloud() 否则无法构造
class CloudTable:
    # 🔍 [语法] __init__(self, table, user_id)
    # 🔍 [作用] 构造时绑定表名和当前用户 ID（用于 RLS）
    def __init__(self, table: str, user_id: str):
        # 🔍 [语法] 显式校验
        # 🔍 [作用] 构造时确保云已配置（避免运行时错误）
        require_cloud()
        self.table = table
        self.user_id = user_id

    # 🔍 [语法] def + 默认参数 + 类型注解
    # 🔍 [作用] 列表查询（支持过滤、排序）
    # 🔍 [示例] list({"subject_id": 1}) 查科目 1 的所有笔记
    # 🔍 [陷阱] 默认按 updated_at 降序
    def list(self, filters: dict[str, Any] | None = None, order: str = "updated_at.desc") -> list[dict[str, Any]]:
        # 🔍 [语法] dict 构造
        # 🔍 [作用] PostgREST 查询参数：select 所有字段 + 按 user_id 过滤 + 排序
        params: dict[str, str] = {
            "select": "*",
            # 🔍 [语法] f-string
            # 🔍 [作用] PostgREST eq 过滤语法（user_id = self.user_id）
            "user_id": f"eq.{self.user_id}",
            "order": order,
        }

        # 🔍 [语法] for-in 循环
        # 🔍 [作用] 遍历过滤条件
        for key, value in (filters or {}).items():
            # 🔍 [语法] 跳过 None 和空字符串
            # 🔍 [作用] 避免发送无效过滤
            if value is not None and value != "":
                # 🔍 [语法] f-string 拼接
                # 🔍 [作用] 构造 eq 过滤参数
                params[key] = f"eq.{value}"

        # 🔍 [语法] with httpx.Client + 上下文管理器
        # 🔍 [作用] 同步 HTTP 请求（20 秒超时）
        # 🔍 [陷阱] 每次调用都新建 Client（性能可优化为复用）
        with httpx.Client(timeout=20) as client:
            response = client.get(_rest_url(self.table), headers=auth_headers(admin=True), params=params)

        # 🔍 [语法] or [] 短路返回
        # 🔍 [作用] _handle 返回 None 时兜底为 []
        return _handle(response) or []

    # 🔍 [语法] def + return type Optional
    # 🔍 [作用] 单条查询
    # 🔍 [陷阱] 找不到返回 None（调用方必须处理）
    def get(self, item_id: int) -> dict[str, Any] | None:
        # 🔍 [语法] dict 构造查询参数
        # 🔍 [作用] PostgREST 多条件过滤
        params = {
            "select": "*",
            "id": f"eq.{item_id}",
            "user_id": f"eq.{self.user_id}",
            "limit": "1",  # 🔍 [语法] PostgREST 限制返回数
        }
        with httpx.Client(timeout=20) as client:
            response = client.get(_rest_url(self.table), headers=auth_headers(admin=True), params=params)
        # 🔍 [语法] rows[0] if rows else None
        # 🔍 [作用] 取第一条或 None
        rows = _handle(response) or []
        return rows[0] if rows else None

    # 🔍 [语法] def + return type
    # 🔍 [作用] 创建记录
    # 🔍 [关联] PostgREST 必须返回 representation 才能拿到新行
    # 🔍 [陷阱] 必须返回新行（rows[0]），不能只返回 None
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        # 🔍 [语法] dict 解构 + 合并
        # 🔍 [作用] 强制注入 user_id（防止漏传）
        # 🔍 [陷阱] user_id 是必需的，覆盖 data 中的同名字段
        payload = {**data, "user_id": self.user_id}

        # 🔍 [语法] dict merge
        # 🔍 [作用] 添加 PostgREST Prefer 头要求返回数据
        headers = {
            **auth_headers(admin=True),
            # 🔍 [语法] Prefer: return=representation
            # 🔍 [作用] 让 POST 返回新插入的行（而非空响应）
            "Prefer": "return=representation",
        }

        with httpx.Client(timeout=20) as client:
            response = client.post(_rest_url(self.table), headers=headers, json=payload)

        rows = _handle(response) or []
        # 🔍 [语法] rows[0]
        # 🔍 [作用] 返回创建的新行
        return rows[0]

    # 🔍 [语法] PATCH 方法（部分更新）
    # 🔍 [作用] 更新记录
    def update(self, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        headers = {**auth_headers(admin=True), "Prefer": "return=representation"}
        # 🔍 [语法] PostgREST 过滤 + PATCH
        # 🔍 [作用] 通过 user_id 过滤确保只能改自己的数据
        params = {"id": f"eq.{item_id}", "user_id": f"eq.{self.user_id}"}
        with httpx.Client(timeout=20) as client:
            response = client.patch(_rest_url(self.table), headers=headers, params=params, json=data)
        rows = _handle(response) or []
        return rows[0] if rows else None

    # 🔍 [语法] DELETE 方法
    # 🔍 [作用] 删除单条记录
    def delete(self, item_id: int) -> bool:
        params = {"id": f"eq.{item_id}", "user_id": f"eq.{self.user_id}"}
        with httpx.Client(timeout=20) as client:
            response = client.delete(_rest_url(self.table), headers=auth_headers(admin=True), params=params)
        _handle(response)
        return True

    # 🔍 [语法] 批量删除
    # 🔍 [作用] 按多个条件删除
    # 🔍 [示例] delete_matching({"note_id": 1, "product_type": "article"}) 删某笔记下所有 article
    def delete_matching(self, filters: dict[str, Any]) -> bool:
        # 🔍 [语法] 初始化 params with user_id
        # 🔍 [作用] 必须过滤 user_id 防越权
        params = {"user_id": f"eq.{self.user_id}"}
        # 🔍 [语法] dict.items() 遍历
        # 🔍 [作用] 把所有过滤条件转 PostgREST eq 语法
        for key, value in filters.items():
            params[key] = f"eq.{value}"
        with httpx.Client(timeout=20) as client:
            response = client.delete(_rest_url(self.table), headers=auth_headers(admin=True), params=params)
        _handle(response)
        return True


# 🔍 [语法] class LocalTable
# 🔍 [作用] 本地模式表操作（用 SQLAlchemy Session）
# 🔍 [关联] CloudTable 的本地对应物（接口一致）
class LocalTable:
    # 🔍 [语法] __init__ + 校验
    # 🔍 [作用] 构造时检查表名有效性
    def __init__(self, table: str, user_id: str):
        # 🔍 [语法] not in 检查
        # 🔍 [作用] 防止非法表名（如 SQL 注入）
        if table not in LOCAL_MODELS:
            # 🔍 [语法] raise 500
            # 🔍 [作用] 服务器内部错误
            raise HTTPException(status_code=500, detail=f"未知本地数据表: {table}")
        self.table = table
        self.model = LOCAL_MODELS[table]
        self.user_id = user_id

    # 🔍 [语法] def + with SessionLocal()
    # 🔍 [作用] 本地列表查询
    def list(self, filters: dict[str, Any] | None = None, order: str = "updated_at.desc") -> list[dict[str, Any]]:
        # 🔍 [语法] with SessionLocal() as db:
        # 🔍 [作用] 上下文管理器确保会话关闭
        def operation():
            with SessionLocal() as db:
            # 🔍 [语法] db.query(Model)
            # 🔍 [作用] 构造查询对象
                query = db.query(self.model)
                if hasattr(self.model, "user_id"):
                    query = query.filter(self.model.user_id == self.user_id)

            # 🔍 [语法] for-in 遍历
            # 🔍 [作用] 应用过滤条件
                for key, value in (filters or {}).items():
                # 🔍 [语法] hasattr + getattr
                # 🔍 [作用] 动态获取列属性 + 比较
                # 🔍 [陷阱] hasattr 防止字段不存在报错
                    if value is not None and value != "" and hasattr(self.model, key):
                        query = query.filter(getattr(self.model, key) == value)

            # 🔍 [语法] hasattr + getattr + desc()
            # 🔍 [作用] 按 updated_at 降序（如字段存在）
                if hasattr(self.model, "updated_at"):
                    query = query.order_by(getattr(self.model, "updated_at").desc())

            # 🔍 [语法] list comprehension + to_dict()
            # 🔍 [作用] 转为字典列表返回
                return [row.to_dict() for row in query.all()]

        return _run_local_operation(operation, retry_safe=True)

    def list_skill_summaries(self, q: str = "", category: str | None = None) -> Any:
        """Search Skill bodies in SQLite but return metadata only."""
        if self.model is not InstalledSkill:
            raise TypeError("Skill summaries are only available for installed_skills")
        def operation():
            with SessionLocal() as db:
                query = db.query(
                InstalledSkill.id, InstalledSkill.name, InstalledSkill.description,
                InstalledSkill.category, InstalledSkill.enabled, InstalledSkill.created_at,
                InstalledSkill.updated_at, func.length(InstalledSkill.instructions).label("instruction_chars"),
                ).filter(InstalledSkill.user_id == self.user_id)
                if category:
                    query = query.filter(InstalledSkill.category == category)
                needle = q.strip().lower()
                if needle:
                    pattern = f"%{needle}%"
                    query = query.filter(or_(
                    func.lower(InstalledSkill.name).like(pattern),
                    func.lower(InstalledSkill.description).like(pattern),
                    func.lower(InstalledSkill.category).like(pattern),
                    func.lower(InstalledSkill.instructions).like(pattern),
                    ))
                rows = query.order_by(InstalledSkill.updated_at.desc()).all()
                return [{
                "id": row.id, "name": row.name, "description": row.description,
                "category": row.category, "enabled": row.enabled,
                "instruction_chars": row.instruction_chars or 0,
                "created_at": row.created_at.isoformat() if row.created_at else None,
                "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                } for row in rows]
        return _run_local_operation(operation, retry_safe=True)

    # 🔍 [语法] def
    # 🔍 [作用] 单条查询（用 db.get 主键快捷方法）
    def get(self, item_id: int) -> dict[str, Any] | None:
        def operation():
            with SessionLocal() as db:
                row = db.get(self.model, item_id)
                if row and hasattr(row, "user_id") and row.user_id != self.user_id:
                    return None
                return row.to_dict() if row else None

        return _run_local_operation(operation, retry_safe=True)

    # 🔍 [语法] def
    # 🔍 [作用] 创建记录
    def create(self, data: dict[str, Any]) -> dict[str, Any]:
        def operation():
            with SessionLocal() as db:
            # 🔍 [语法] Model(**data)
            # 🔍 [作用] 用 kwargs 构造 ORM 实例
            # 🔍 [陷阱] data 中字段名必须与模型字段名一致
                payload = {**data}
                if hasattr(self.model, "user_id"):
                    payload["user_id"] = self.user_id
                row = self.model(**payload)
            # 🔍 [语法] db.add + commit + refresh
            # 🔍 [作用] 标准 CRUD 流程
                db.add(row)
                db.commit()
            # 🔍 [语法] db.refresh(obj)
            # 🔍 [作用] 重新加载字段（如自增 id）
                db.refresh(row)
                return row.to_dict()

        return _run_local_operation(operation)

    # 🔍 [语法] def
    # 🔍 [作用] 更新记录（动态赋值）
    def update(self, item_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        def operation():
            with SessionLocal() as db:
                row = db.get(self.model, item_id)
                if not row or (hasattr(row, "user_id") and row.user_id != self.user_id):
                    return None
            # 🔍 [语法] for-in + setattr
            # 🔍 [作用] 动态更新字段
                for key, value in data.items():
                    if hasattr(row, key):
                    # 🔍 [语法] setattr(obj, name, value)
                    # 🔍 [作用] 动态属性赋值
                        setattr(row, key, value)
                db.commit()
                db.refresh(row)
                return row.to_dict()

        return _run_local_operation(operation)

    # 🔍 [语法] def
    # 🔍 [作用] 删除单条
    def delete(self, item_id: int) -> bool:
        def operation():
            with SessionLocal() as db:
                row = db.get(self.model, item_id)
                if row and hasattr(row, "user_id") and row.user_id != self.user_id:
                    row = None
            # 🔍 [语法] if row
            # 🔍 [作用] 存在才删
                if row:
                    db.delete(row)
                    db.commit()
            return True

        return _run_local_operation(operation)

    # 🔍 [语法] def
    # 🔍 [作用] 批量删除（按多个条件）
    def delete_matching(self, filters: dict[str, Any]) -> bool:
        with SessionLocal() as db:
            query = db.query(self.model)
            if hasattr(self.model, "user_id"):
                query = query.filter(self.model.user_id == self.user_id)
            for key, value in filters.items():
                # 🔍 [语法] hasattr 检查
                # 🔍 [作用] 防止字段不存在报错
                if hasattr(self.model, key):
                    query = query.filter(getattr(self.model, key) == value)
            # 🔍 [语法] for row in query.all() + db.delete
            # 🔍 [作用] 逐个删除
            for row in query.all():
                db.delete(row)
            db.commit()
        return True


# 🔍 [语法] 工厂函数
# 🔍 [作用] 根据配置返回 CloudTable 或 LocalTable
# 🔍 [关联] routers 中通过 table("subjects", user) 调用
# 🔍 [陷阱] 返回值类型是 Union（业务方无需关心具体类型）
def table(name: str, user: dict[str, Any]) -> CloudTable:
    # 🔍 [语法] not cloud_is_configured()
    # 🔍 [作用] 未配置云 → 本地模式
    if not cloud_is_configured():
        return LocalTable(name, user["id"])
    # 🔍 [语法] 否则云模式
    return CloudTable(name, user["id"])


# 🔍 [语法] def + 返回 int
# 🔍 [作用] 统计行数（通用 count 接口）
# 🔍 [关联] main.py 的 /api/stats 用此函数
def count_rows(name: str, user_id: str, filters: dict[str, Any] | None = None) -> int:
    # 🔍 [语法] if not cloud_is_configured()
    # 🔍 [作用] 本地模式分支
    if not cloud_is_configured():
        # 🔍 [语法] LOCAL_MODELS[name]
        # 🔍 [作用] 表名 → ORM 类
        model = LOCAL_MODELS[name]
        with SessionLocal() as db:
            query = db.query(model)
            for key, value in (filters or {}).items():
                if hasattr(model, key):
                    query = query.filter(getattr(model, key) == value)
            # 🔍 [语法] query.count()
            # 🔍 [作用] 统计行数
            return query.count()

    # 🔍 [语法] 云模式分支
    # 🔍 [作用] 用 PostgREST Content-Range 头返回总数
    params = {"select": "id", "user_id": f"eq.{user_id}"}
    for key, value in (filters or {}).items():
        # 🔍 [语法] quote(str(value), safe='')
        # 🔍 [作用] URL 编码 value（含特殊字符也安全）
        params[key] = f"eq.{quote(str(value), safe='')}"
    # 🔍 [语法] Prefer: count=exact
    # 🔍 [作用] PostgREST 返回精确总数（而非估算）
    headers = {**auth_headers(admin=True), "Prefer": "count=exact"}
    with httpx.Client(timeout=20) as client:
        response = client.get(_rest_url(name), headers=headers, params=params)
    _handle(response)
    # 🔍 [语法] response.headers.get
    # 🔍 [作用] Content-Range 头格式：0-N/Total
    # 🔍 [示例] "0-9/100" 表示 0 到 9 共 100 条
    content_range = response.headers.get("content-range", "0-0/0")
    # 🔍 [语法] rsplit + int
    # 🔍 [作用] 取斜杠后部分（总数）
    return int(content_range.rsplit("/", 1)[-1])


# 🔍 [语法] def + 返回 float
# 🔍 [作用] 汇总产品建议售价
# 🔍 [关联] main.py 的 /api/stats 用此
# 🔍 [安全] 2026-08 修复：本地模式同样按 user_id 过滤，避免多用户串户
def sum_product_value(user_id: str) -> float:
    # 🔍 [语法] 本地模式分支
    if not cloud_is_configured():
        with SessionLocal() as db:
            # 🔍 [语法] filter(user_id)
            # 🔍 [作用] 仅累加当前用户的产品建议售价
            rows = db.query(Product).filter(Product.user_id == user_id).all()
            # 🔍 [语法] generator + sum
            # 🔍 [作用] 累加 price_suggestion（默认 0）
            return float(sum(float(row.price_suggestion or 0) for row in rows))

    # 🔍 [语法] 云模式分支
    params = {"select": "price_suggestion", "user_id": f"eq.{user_id}"}
    with httpx.Client(timeout=20) as client:
        response = client.get(_rest_url("products"), headers=auth_headers(admin=True), params=params)
    # 🔍 [语法] or []
    # 🔍 [作用] rows 为 None 兜底为 []
    rows = _handle(response) or []
    # 🔍 [语法] 列表推导式
    # 🔍 [作用] 每行的 price_suggestion 累加
    return float(sum(float(row.get("price_suggestion") or 0) for row in rows))
