# 🔍 [语法] httpx 导入
# 🔍 [作用] 同步 HTTP 客户端（调 Supabase auth API）
import httpx

# 🔍 [语法] FastAPI 核心导入
# 🔍 [作用] APIRouter 定义路由；Depends 注入；HTTPException 抛错
from fastapi import APIRouter, Depends, HTTPException

# 🔍 [语法] Pydantic 导入
# 🔍 [作用] BaseModel 定义请求体；EmailStr 邮箱校验（依赖 email-validator）
from pydantic import BaseModel, EmailStr

# 🔍 [语法] 相对导入（..auth）
# 🔍 [作用] 复用 auth.py 的工具（双斜杠 .. 表示 app 包上一层）
# 🔍 [陷阱] .. 表示父包（app）的同级模块（不是 app.auth）
from ..auth import (
    auth_headers, cloud_is_configured, create_local_token,
    get_current_user, require_cloud, supabase_url,
)


# 🔍 [语法] APIRouter(prefix, tags)
# 🔍 [作用] 创建路由实例；所有端点 URL 自动加 /api/auth 前缀；tags 用于 OpenAPI 分类
# 🔍 [示例] @router.post("/signup") 实际 URL = POST /api/auth/signup
router = APIRouter(prefix="/api/auth", tags=["auth"])


# 🔍 [语法] Pydantic BaseModel 继承
# 🔍 [作用] 定义登录/注册请求体（含字段验证）
class AuthRequest(BaseModel):
    # 🔍 [语法] EmailStr 类型
    # 🔍 [作用] Pydantic 自动校验邮箱格式（必须含 @）
    email: EmailStr

    # 🔍 [语法] str（无最小长度约束）
    # 🔍 [作用] 密码字段（最小长度应在路由中校验）
    # 🔍 [陷阱] ⚠️ 当前未限制长度，应加 min_length=6
    password: str


# 🔍 [语法] 第二个 BaseModel
# 🔍 [作用] 忘记密码请求体（仅需邮箱）
class ForgotPasswordRequest(BaseModel):
    email: EmailStr


# 🔍 [语法] 下划线前缀表示模块内部函数
# 🔍 [作用] Supabase auth API 通用调用（login/signup/recover 共用）
# 🔍 [关联] Supabase auth API 端点：/auth/v1/{path}
def _call_auth(path: str, payload: dict, token: str | None = None) -> dict:
    # 🔍 [语法] 早返回校验
    # 🔍 [作用] 云模式强制要求配置
    require_cloud()

    # 🔍 [语法] try/except HTTPError
    # 🔍 [作用] 调用 Supabase auth API；网络错误转 502
    try:
        # 🔍 [语法] with httpx.Client(timeout=20) as client
        # 🔍 [作用] 上下文管理器 + 20 秒超时
        with httpx.Client(timeout=20) as client:
            # 🔍 [语法] client.post(url, headers, json)
            # 🔍 [作用] POST 到 Supabase auth API
            response = client.post(
                # 🔍 [语法] f-string URL
                # 🔍 [作用] 拼接 Supabase auth 端点
                f"{supabase_url()}/auth/v1/{path}",
                headers=auth_headers(token),
                json=payload,
            )
    # 🔍 [语法] except HTTPError as exc
    # 🔍 [作用] 网络/超时错误转 502 Bad Gateway
    # 🔍 [陷阱] raise from exc 保留原始堆栈
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"认证服务不可用: {exc}") from exc

    # 🔍 [语法] if status >= 400
    # 🔍 [作用] Supabase 返回 4xx/5xx 视为认证错误
    if response.status_code >= 400:
        # 🔍 [语法] 三元 + startswith
        # 🔍 [作用] 优先 JSON 错误，失败用文本
        detail = (
            response.json()
            if response.headers.get("content-type", "").startswith("application/json")
            else response.text
        )
        # 🔍 [语法] raise HTTPException with status_code 透传
        # 🔍 [作用] 把 Supabase 错误状态码透传给前端
        raise HTTPException(status_code=response.status_code, detail=detail)

    # 🔍 [语法] response.json() or {}
    # 🔍 [作用] 空响应返回空 dict
    return response.json() if response.content else {}


# 🔍 [语法] @router.post(path) 装饰器
# 🔍 [作用] 定义 POST /api/auth/signup 端点
@router.post("/signup")
def signup(data: AuthRequest):
    # 🔍 [语法] 早返回
    # 🔍 [作用] 未配置云 → 本地开发模式直接发 token
    if not cloud_is_configured():
        # 🔍 [语法] return create_local_token(data.email)
        # 🔍 [作用] 跳过 Supabase 直接返回本地 token
        # 🔍 [陷阱] ⚠️ 生产必须删除此分支
        return create_local_token(data.email)

    # 🔍 [语法] _call_auth 通用调用
    # 🔍 [作用] 调用 Supabase signup 端点
    return _call_auth(
        "signup",
        # 🔍 [语法] dict 字面量
        # 🔍 [作用] 构造 Supabase signup 请求体
        {"email": data.email, "password": data.password},
    )


# 🔍 [语法] @router.post
# 🔍 [作用] 定义登录端点
@router.post("/login")
def login(data: AuthRequest):
    # 🔍 [语法] 双模式：本地 vs 云
    # 🔍 [作用] 未配置云 → 本地模式
    if not cloud_is_configured():
        # 🔍 [陷阱] ⚠️ 本地模式不校验密码（仅生成 token）
        return create_local_token(data.email)

    # 🔍 [语法] Supabase token 端点
    # 🔍 [作用] OAuth 2.0 password grant（已不推荐，但 Supabase 仍支持）
    return _call_auth(
        "token?grant_type=password",
        {"email": data.email, "password": data.password},
    )


# 🔍 [语法] @router.post
# 🔍 [作用] 忘记密码端点
@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest):
    # 🔍 [语法] 本地模式返回固定响应
    # 🔍 [作用] 不真发邮件，提示用任意 6+ 位密码登录
    if not cloud_is_configured():
        return {
            "ok": True,
            "message": "本地演示模式无需重置密码，请直接使用任意邮箱和 6 位以上密码登录。",
        }

    # 🔍 [语法] Supabase recover 端点
    # 🔍 [作用] 触发 Supabase 发送重置邮件
    return _call_auth("recover", {"email": data.email})


# 🔍 [语法] @router.get + Depends
# 🔍 [作用] 获取当前登录用户
# 🔍 [依赖注入] user: dict = Depends(get_current_user)
@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    # 🔍 [语法] dict 字面量包装
    # 🔍 [作用] 前端 AuthGate.jsx 期望的响应格式是 {user: ...}
    return {"user": user}
