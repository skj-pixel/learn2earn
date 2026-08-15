# 🔍 [语法] 多行 import，按字母顺序组织
# 🔍 [作用] 导入认证模块所需的所有依赖
# 🔍 [关联] 所有依赖都被全局使用，无未使用 import
# 🔍 [陷阱] Any 是大写字母开头，需要 from typing import Any
import os          # ① OS 接口：读环境变量
import base64      # ② Base64 编解码：本地 token 编解码
import hashlib
import hmac
import json        # ③ JSON 序列化：解析 token payload
import time
from typing import Any  # ④ 类型注解：dict[str, Any]

# 🔍 [语法] httpx 导入
# 🔍 [作用] 同步 HTTP 客户端，用于调用 Supabase auth API
# 🔍 [陷阱] httpx 替代了 requests；与 FastAPI 异步的 httpx.AsyncClient 不同（这是同步版）
import httpx

# 🔍 [语法] FastAPI 依赖 + 安全相关导入
# 🔍 [作用] Depends 用于依赖注入；HTTPException 用于 401/502 等异常抛出
# 🔍 [示例] def protected(user: dict = Depends(get_current_user)): ...
from fastapi import Depends, HTTPException

# 🔍 [语法] FastAPI 安全模块
# 🔍 [作用] HTTPBearer 是 Bearer Token 认证方案；HTTPAuthorizationCredentials 是凭据封装
# 🔍 [示例] Authorization: Bearer eyJhbGc... → HTTPBearer 提取 token
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


# 🔍 [语法] 模块级 HTTPBearer 实例
# 🔍 [作用] 创建 Bearer Token 安全方案，auto_error=False 不自动抛 401（让代码自己控制错误信息）
# 🔍 [示例] 在 get_current_user 中通过 Depends(security) 注入凭据
# 🔍 [陷阱] auto_error=False 必须，否则 FastAPI 会自动抛 401 而不是代码的自定义错误
security = HTTPBearer(auto_error=False)


# 🔍 [语法] def 函数 + -> str 返回类型注解
# 🔍 [作用] 读取 SUPABASE_URL 环境变量并去掉末尾斜杠
# 🔍 [示例] "https://abc.supabase.co/" → "https://abc.supabase.co"
# 🔍 [陷阱] rstrip("/") 只去末尾单斜杠（不去路径中间）
def supabase_url() -> str:
    return os.getenv("SUPABASE_URL", "").rstrip("/")


# 🔍 [语法] 同上结构
# 🔍 [作用] 读取 Supabase 匿名 key（前端可见，受 RLS 保护）
# 🔍 [陷阱] 匿名 key 公开后安全性依赖 RLS 策略
def supabase_anon_key() -> str:
    return os.getenv("SUPABASE_ANON_KEY", "")


# 🔍 [语法] 同上结构
# 🔍 [作用] 读取 Supabase 服务端 key（绕过 RLS，仅服务端用）
# 🔍 [陷阱] ⚠️ service_role_key 绝对不能泄露到前端！等同于超级管理员
def supabase_service_role_key() -> str:
    return os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")


# 🔍 [语法] bool(...) 转换 + and 链
# 🔍 [作用] 判断云环境是否配置齐全（URL + 匿名 key + 服务端 key 三者齐全）
# 🔍 [示例] 都配置 → True；任一缺失 → False
# 🔍 [陷阱] 空字符串也是 falsy，所以 bool("") = False
def cloud_is_configured() -> bool:
    return bool(supabase_url() and supabase_anon_key() and supabase_service_role_key())


# 🔍 [语法] def + raise HTTPException
# 🔍 [作用] 强制要求云配置，未配置则抛 503 Service Unavailable
# 🔍 [示例] 在 cloud_db.py 调用 cloud 模式前调用
# 🔍 [陷阱] 503 是 5xx 服务端错误；区别于 4xx 客户端错误
def require_cloud() -> None:
    if not cloud_is_configured():
        raise HTTPException(
            status_code=503,
            detail="云数据库尚未配置。请先运行 meoo cloud enable 和 meoo cloud pull-env。",
        )


def _local_secret() -> bytes:
    secret = os.getenv("LEARN2EARN_LOCAL_TOKEN_SECRET") or os.getenv("SECRET_KEY") or "learn2earn-local-demo-secret"
    return secret.encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64url_json(data: dict[str, Any]) -> str:
    return _b64url(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def _decode_b64url_json(payload: str) -> dict[str, Any]:
    padding = "=" * (-len(payload) % 4)
    return json.loads(base64.urlsafe_b64decode(payload + padding).decode("utf-8"))


# 🔍 [语法] def 函数带默认参数 + Optional
# 🔍 [作用] 构造 Supabase API 请求头
# 🔍 [示例] auth_headers(token) 用于带 token 调用；auth_headers(admin=True) 用于服务端管理操作
# 🔍 [陷阱] admin=True 时用 service_role_key（绕过 RLS），admin=False 时用 anon_key 或 token
def auth_headers(token: str | None = None, admin: bool = False) -> dict[str, str]:
    # 🔍 [语法] 三元表达式
    # 🔍 [作用] admin=True 用 service_role_key（高权限），否则用 anon_key（公开权限）
    key = supabase_service_role_key() if admin else supabase_anon_key()

    # 🔍 [语法] 三元表达式 + or 短路
    # 🔍 [作用] bearer：admin 用 service_role_key，否则用传入的 token
    # 🔍 [陷阱] 如果 token=None 且 not admin，bearer=None，会导致 Authorization 头部为空
    bearer = supabase_service_role_key() if admin else token

    # 🔍 [语法] dict 字面量
    # 🔍 [作用] 返回 Supabase REST API 标准头（apikey + Authorization Bearer）
    return {
        # 🔍 [语法] "apikey" 是 Supabase 自定义头（不同于标准 Authorization）
        "apikey": key,
        # 🔍 [语法] f-string 拼接
        # 🔍 [作用] 标准 Authorization Bearer 格式
        # 🔍 [陷阱] bearer 为 None 时 f-string 会拼成 "Bearer None"，应保证 bearer 不为 None
        "Authorization": f"Bearer {bearer or key}",
        # 🔍 [语法] 标准 Content-Type
        "Content-Type": "application/json",
    }


# 🔍 [语法] 下划线前缀表示私有函数（约定）
# 🔍 [作用] 从本地 token 字符串解析出用户信息
# 🔍 [关联] 与 create_local_token 配对（一个创建，一个解析）
# 🔍 [陷阱] token 格式必须是 "local.{base64_payload}"，否则视为无效
def _local_user_from_token(token: str) -> dict[str, Any]:
    # 🔍 [语法] 字符串 startswith
    # 🔍 [作用] 校验 token 前缀是否是 "local."
    # 🔍 [陷阱] 必须严格匹配；本地模式 token 不能用作云模式
    if not token.startswith("local."):
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    # 🔍 [语法] try ... except 多异常类型元组
    # 🔍 [作用] 解析 payload；捕获 ValueError 和 JSONDecodeError
    try:
        parts = token.split(".", 2)
        if len(parts) != 3:
            raise ValueError("invalid local token format")
        _, payload, signature = parts
        expected = _b64url(hmac.new(_local_secret(), payload.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid local token signature")
        data = _decode_b64url_json(payload)
    # 🔍 [语法] except (ValueError, json.JSONDecodeError) 元组捕获
    # 🔍 [作用] 任何解码错误都视为无效 token
    except (ValueError, json.JSONDecodeError):
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    # 🔍 [语法] dict.get(key) 取值（不存在返回 None）
    # 🔍 [作用] 从 payload 取 email；如果没有则视为无效
    email = os.environ.get("LEARN2EARN_LOCAL_DEMO_EMAIL", "").strip() or data.get("email")
    if not email:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    exp = int(data.get("exp") or 0)
    if exp and exp < int(time.time()):
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    # 🔍 [语法] dict 字面量 + f-string
    # 🔍 [作用] 返回标准 Supabase 用户对象格式（与云模式一致）
    # 🔍 [陷阱] id 用了 "local:" 前缀，与云模式的 UUID 不同；下游需要兼容
    return {
        "id": f"local:{email}",
        "email": email,
        # 🔍 [语法] Supabase 标准字段
        # 🔍 [作用] aud = audience（受众）；role = authenticated（已认证用户）
        "aud": "authenticated",
        "role": "authenticated",
        # 🔍 [语法] app_metadata 嵌套字典
        # 🔍 [作用] 标记这是本地开发模式
        "app_metadata": {"provider": "local-dev"},
    }


# 🔍 [语法] def 函数 + 返回 dict
# 🔍 [作用] 生成本地开发模式 token（无需云数据库）
# 🔍 [关联] auth.py 的 /signup 和 /login 路由调用
# 🔍 [陷阱] ⚠️ 这是开发辅助，生产环境必须使用真正的云认证
def create_local_token(email: str) -> dict[str, Any]:
    # 🔍 [语法] f-string id
    # 🔍 [作用] 用 email 作唯一标识
    user = {
        "id": f"local:{email}",
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
    }

    payload = _b64url_json({"email": email, "iat": int(time.time()), "exp": int(time.time()) + 7 * 24 * 3600})
    signature = _b64url(hmac.new(_local_secret(), payload.encode("ascii"), hashlib.sha256).digest())

    # 🔍 [语法] dict 字面量
    # 🔍 [作用] 返回 OAuth 标准格式（access_token + token_type + user）
    # 🔍 [陷阱] ⚠️ 这只是模拟 JWT，不是真正的签名 token（任何人都可伪造）
    return {
        "access_token": f"local.{payload}.{signature}",
        "token_type": "bearer",
        "user": user,
    }


# 🔍 [语法] FastAPI 依赖函数
# 🔍 [作用] 核心：从请求头获取 Bearer Token 并验证，返回当前用户 dict
# 🔍 [示例] 在路由函数中 user: dict = Depends(get_current_user)
# 🔍 [陷阱] 这是整个认证的核心；任何修改都要全面测试
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    # 🔍 [语法] 早返回（Early Return）模式
    # 🔍 [作用] 未配置云 → 使用本地模式
    if not cloud_is_configured():
        # 🔍 [语法] and 链式判断
        # 🔍 [作用] 没有 credentials 或 token 为空都视为未登录
        if not credentials or not credentials.credentials:
            raise HTTPException(status_code=401, detail="请先登录")
        # 🔍 [语法] 函数调用作为值
        # 🔍 [作用] 调用本地 token 解析
        return _local_user_from_token(credentials.credentials)

    # 🔍 [语法] 显式调用（vs 条件表达式）
    # 🔍 [作用] 已配置云：要求必须配置（双重保险）
    require_cloud()

    # 🔍 [语法] 同样的早返回
    # 🔍 [作用] 云模式下也校验凭证存在
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=401, detail="请先登录")

    # 🔍 [语法] 别名
    # 🔍 [作用] token 是核心变量；后续多处使用
    token = credentials.credentials

    # 🔍 [语法] try ... except HTTPError
    # 🔍 [作用] 调用 Supabase auth API 获取当前用户
    # 🔍 [陷阱] 网络超时、连接错误等都转为 502（Bad Gateway）
    try:
        # 🔍 [语法] httpx.Client(timeout=15) — 上下文管理器确保连接关闭
        # 🔍 [作用] 同步 HTTP 客户端，15 秒超时（防止长时间阻塞）
        # 🔍 [示例] timeout=15 是经验值；生产可调小（5-10s）减少等待
        with httpx.Client(timeout=15) as client:
            # 🔍 [语法] client.get(url, headers=...)
            # 🔍 [作用] GET /auth/v1/user 获取当前用户信息
            # 🔍 [陷阱] Supabase 返回格式：{id, email, role, ...}
            response = client.get(
                # 🔍 [语法] f-string URL
                # 🔍 [作用] 拼接 Supabase auth API URL
                f"{supabase_url()}/auth/v1/user",
                # 🔍 [语法] keyword arg + 函数调用结果
                # 🔍 [作用] 使用 token 构造的认证头
                headers=auth_headers(token),
            )
    # 🔍 [语法] except HTTPError as exc
    # 🔍 [作用] 捕获 httpx 所有 HTTP 异常（超时、连接失败等）
    # 🔍 [陷阱] raise ... from exc 保留原始异常堆栈
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"认证服务不可用: {exc}") from exc

    # 🔍 [语法] 4xx/5xx 错误判断
    # 🔍 [作用] Supabase 返回 401 表示 token 无效/过期
    if response.status_code >= 400:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    # 🔍 [语法] response.json() 解析 JSON
    # 🔍 [作用] 返回 Supabase 用户对象
    return response.json()
