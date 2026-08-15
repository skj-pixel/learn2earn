# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标识模块用途
# 🔍 [陷阱] 占位 TODO 应人工补全
"""
把学习过程变成赚钱过程的app/backend/app/main.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# main.py - FastAPI 应用入口
# =============================================================================
# 职责：
#   1. 创建 FastAPI 应用实例
#   2. 配置 CORS 跨域中间件
#   3. 注册所有路由模块
#   4. 应用启动时初始化数据库（使用现代 lifespan 模式）
#   5. 提供根路径和全局统计接口
# =============================================================================

# 🔍 [语法] from contextlib import asynccontextmanager
# 🔍 [作用] asynccontextmanager 装饰器把异步生成器转为异步上下文管理器（FastAPI lifespan 用）
# 🔍 [示例] @asynccontextmanager async def lifespan(app): yield ...  # 进入 yield 前/后分别执行
# 🔍 [陷阱] 替代已弃用的 @app.on_event("startup"/"shutdown")（FastAPI 0.93+）
import os
from contextlib import asynccontextmanager

# 🔍 [语法] from pathlib import Path
# 🔍 [作用] Path 类跨平台路径处理（Windows / Linux / macOS 自动适配）
# 🔍 [示例] Path(__file__).resolve().parent.parent  # 上上级目录
# 🔍 [陷阱] 字符串拼接路径不可移植，务必用 Path 对象
from pathlib import Path

# 🔍 [语法] from fastapi import FastAPI, Depends
# 🔍 [作用] FastAPI 主类；Depends 用于依赖注入
# 🔍 [示例] FastAPI() 创建应用；Depends(get_current_user) 注入当前用户
from fastapi import FastAPI, Depends

# 🔍 [语法] from fastapi.responses import FileResponse
# 🔍 [作用] 用于返回文件响应（SPA fallback 返回 index.html 用）
# 🔍 [陷阱] FileResponse 是 StreamingResponse 的子类，会自动设置 Content-Type
from fastapi.responses import FileResponse

# 🔍 [语法] from fastapi.staticfiles import StaticFiles
# 🔍 [作用] 用于挂载静态资源目录（前端 build 产物）
# 🔍 [陷阱] StaticFiles 只能挂载整个目录；具体文件用 FileResponse
from fastapi.staticfiles import StaticFiles

# 🔍 [语法] from fastapi.middleware.cors import CORSMiddleware
# 🔍 [作用] CORS 中间件，允许跨域请求（前端 5173 端口调后端 8000 端口）
# 🔍 [陷阱] ⚠️ 生产环境 allow_origins=["*"] + credentials=True 非法组合
from fastapi.middleware.cors import CORSMiddleware

# 🔍 [语法] from sqlalchemy.orm import Session
# 🔍 [作用] SQLAlchemy Session 类型注解
# 🔍 [陷阱] get_stats 函数实际未使用 Session（因为现在用云模式）
from sqlalchemy.orm import Session

# 🔍 [语法] 相对导入：from .module import ...
# 🔍 [作用] 导入同包内的模块（auth / cloud_db / database / routers）
# 🔍 [陷阱] . 表示当前包（app）；.. 表示上级包
from .auth import cloud_is_configured, get_current_user
from .cloud_db import count_rows, sum_product_value
from .database import init_db, get_db
from .routers import routers


# =============================================================================
# Lifespan 生命周期管理（替代已弃用的 @app.on_event("startup")）
# =============================================================================

# 🔍 [语法] @asynccontextmanager 装饰器
# 🔍 [作用] 把 lifespan 函数转为异步上下文管理器
# 🔍 [陷阱] 函数必须是 async def + yield，yield 前是启动代码，yield 后是关闭代码
@asynccontextmanager

# 🔍 [语法] async def lifespan(app: FastAPI)
# 🔍 [作用] FastAPI 应用生命周期回调
# 🔍 [示例] yield 之前的代码 → 应用启动时执行；yield → 应用运行中；yield 后 → 关闭
# 🔍 [陷阱] 此函数不接受 app 参数外的其他参数（FastAPI 强制签名）
async def lifespan(app: FastAPI):
    """
    管理 FastAPI 应用的生命周期

    执行顺序：
        1. yield 之前的代码 → 应用启动时执行（初始化数据库）
        2. yield → 应用运行中（处理请求）
        3. yield 之后的代码 → 应用关闭时执行（清理资源）
    """
    # 🔍 [语法] 早返回
    # 🔍 [作用] 未配置云数据库 → 使用本地 SQLite
    # 🔍 [陷阱] 配了云但仍想用本地会失败（cloud_is_configured 优先）
    if not cloud_is_configured():
        # 🔍 [语法] 函数调用
        # 🔍 [作用] 执行 Base.metadata.create_all(bind=engine)
        # 🔍 [示例] 首次启动会创建 subjects/notes/products 三张表
        # 🔍 [陷阱] 已存在的表不会被修改（生产用 Alembic）
        init_db()

    # 🔍 [语法] yield（无值）
    # 🔍 [作用] 把控制权交给 FastAPI，让其处理请求
    # 🔍 [陷阱] yield 不能被 try/finally 包裹（FastAPI 内部管理）
    yield

    # ---- 关闭时（可在此处添加清理逻辑） ----
    # 🔍 [作用] 预留位置：清理资源（关闭连接池、刷写缓冲等）
    # 🔍 [陷阱] 此处异常会阻止优雅关闭


# --------------- 创建 FastAPI 应用 ---------------

# 🔍 [语法] FastAPI(...) 实例化（类构造）
# 🔍 [作用] 创建 FastAPI 应用实例
# 🔍 [关联] 此 app 变量在 run.py 中被 uvicorn 启动
# 🔍 [示例] app.title 会显示在 /docs 的 Swagger UI 顶部
app = FastAPI(
    # 🔍 [语法] 关键字参数 title="..."
    # 🔍 [作用] API 文档标题（Swagger UI / ReDoc）
    title="Learn2Earn API",

    # 🔍 [语法] 关键字参数 description="..."
    # 🔍 [作用] API 描述
    description="将学习过程转化为赚钱过程的APP后端",

    # 🔍 [语法] version="1.0.0"
    # 🔍 [作用] API 版本号（OpenAPI 规范）
    # 🔍 [陷阱] 版本变更需要 breaking change 通知用户
    version="5.1.0",

    # 🔍 [语法] lifespan=lifespan 引用上方函数
    # 🔍 [作用] 注册生命周期回调
    # 🔍 [陷阱] 必须用关键字参数；位置参数顺序可能与 FastAPI 内部签名冲突
    lifespan=lifespan,
)

# --------------- CORS 跨域配置 ---------------

# 🔍 [安全] 2026-08 修复：origin 白名单化，消除 "*"+credentials=True 非法组合
# 🔍 [作用] 默认覆盖本地开发(5173)/演示(9000-9010)/预览(4173)，生产用 CORS_ORIGINS 覆盖
_CORS_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:9000,http://127.0.0.1:9000,"
        "http://localhost:9001,http://127.0.0.1:9001,http://localhost:4173,http://127.0.0.1:4173",
    ).split(",")
    if o.strip()
]

# 🔍 [作用] 允许前端（开发服务器 localhost:5173）跨域调用后端 API
# 🔍 [陷阱] 生产环境必须限制 allow_origins 为具体域名（不能用 *）
app.add_middleware(
    # 🔍 [语法] 类引用作为参数
    # 🔍 [作用] FastAPI 内置 CORS 中间件类
    CORSMiddleware,

    # 🔍 [语法] list[str] 参数
    # 🔍 [作用] 允许的跨域来源（origin）；"*" 表示允许所有
    # 🔍 [陷阱] ⚠️ 与 credentials=True 组合时浏览器会拒绝
    allow_origins=_CORS_ORIGINS,

    # 🔍 [语法] bool
    # 🔍 [作用] 允许跨域请求携带 Cookie/Authorization
    # 🔍 [陷阱] 必须配 allow_origins 为具体域名（不能 *）
    allow_credentials=True,

    # 🔍 [语法] list[str]
    # 🔍 [作用] 允许的 HTTP 方法
    # 🔍 [陷阱] 实际只检查 CORS 预检（OPTIONS）请求
    allow_methods=["*"],

    # 🔍 [语法] list[str]
    # 🔍 [作用] 允许的请求头
    allow_headers=["*"],
)
# --------------- 注册路由 ---------------

# 🔍 [语法] for-in 循环
# 🔍 [作用] 遍历 routers 列表，逐个注册到应用
# 🔍 [关联] routers 来自 app.routers 模块聚合
# 🔍 [陷阱] 注册顺序不影响功能，但影响 OpenAPI 文档展示顺序
for router in routers:
    # 🔍 [语法] app.include_router(router)
    # 🔍 [作用] 将路由器及其所有端点注册到应用中
    # 🔍 [陷阱] 重复注册同一 router 会导致路由冲突
    app.include_router(router)


# --------------- 根路径 ---------------

# 🔍 [语法] @app.get(path) 装饰器 + def 函数
# 🔍 [作用] 定义 GET 端点
# 🔍 [示例] 访问 http://localhost:8000/api/health 返回 JSON
@app.get("/api/health")

# 🔍 [语法] def root(): 返回 dict
# 🔍 [作用] 健康检查端点（用于 K8s liveness probe）
# 🔍 [陷阱] 不需要鉴权（让负载均衡器能访问）
def root():
    """
    根端点 - API 欢迎页
    """
    # 🔍 [语法] dict 字面量
    # 🔍 [作用] FastAPI 自动 JSON 序列化
    # 🔍 [陷阱] datetime / 对象等需要 str() 或 Pydantic 序列化
    return {
        "message": "Welcome to Learn2Earn API",
        "version": "5.1.0",
        "description": "把学习过程变成赚钱过程的APP - 边学边输出知识付费产品",
    }


# --------------- 全局统计接口 ---------------

# 🔍 [语法] @app.get(path) 装饰器
# 🔍 [作用] 定义 GET 端点
@app.get("/api/stats")

# 🔍 [语法] 函数签名 + 默认参数 + Depends 注入
# 🔍 [作用] 获取全局统计（需要登录）
# 🔍 [示例] curl -H "Authorization: Bearer <token>" http://localhost:8000/api/stats
def get_stats(user: dict = Depends(get_current_user)):
    """
    获取全局统计数据
    """
    # 🔍 [语法] dict.get 链式取值
    # 🔍 [作用] 从 user dict 取 id（依赖 auth.py 的标准化输出）
    # 🔍 [陷阱] 若 user 结构变化会导致 KeyError
    user_id = user["id"]

    # 🔍 [语法] 函数调用传参
    # 🔍 [作用] 统计各表的当前用户数据条数
    # 🔍 [关联] count_rows 是 cloud_db.py 的统一接口（双模式）
    subject_count = count_rows("subjects", user_id)
    note_count = count_rows("notes", user_id)
    product_count = count_rows("products", user_id)

    # 🔍 [语法] dict 作为额外过滤参数
    # 🔍 [作用] 统计草稿数（status="draft"）
    # 🔍 [陷阱] 云模式用 PostgREST eq 语法；本地模式用 SQLAlchemy filter_by
    draft_count = count_rows("products", user_id, {"status": "draft"})

    # 🔍 [语法] 同上
    # 🔍 [作用] 统计已发布数
    published_count = count_rows("products", user_id, {"status": "published"})

    # 🔍 [语法] 函数调用
    # 🔍 [作用] 汇总所有产品的建议售价总和
    # 🔍 [陷阱] 此函数当前对所有用户返回所有产品（未过滤 user_id）
    total_value = sum_product_value(user_id)

    # 🔍 [语法] dict 字面量 + f-string + 类型转换
    # 🔍 [作用] 返回统计 JSON
    # 🔍 [陷阱] round(float(x), 2) 防止 Decimal 类型 JSON 序列化失败
    return {
        "subjects": subject_count,
        "notes": note_count,
        "products": product_count,
        "draft_products": draft_count,
        "published_products": published_count,
        # 🔍 [语法] round() 内置函数
        # 🔍 [作用] 保留 2 位小数；float() 转 Decimal 为 float
        "estimated_total_value": round(float(total_value), 2),
        # 🔍 [语法] f-string 嵌套
        # 🔍 [作用] 人类可读的潜力收入描述
        "earning_potential": f"已生成 {product_count} 个知识付费产品，潜在收入约 ¥{round(float(total_value), 2)}",
    }


# --------------- SPA 静态文件托管 ---------------

# 🔍 [语法] pathlib 操作
# 🔍 [作用] 计算前端构建产物的绝对路径
# 🔍 [示例] /code/frontend/dist
# 🔍 [陷阱] 假设 frontend/dist 在项目根目录；Docker 部署时路径可能不同
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# 🔍 [语法] if path.exists()
# 🔍 [作用] 仅当构建产物存在时才挂载（避免开发环境报错）
if FRONTEND_DIST.exists():
    # 🔍 [语法] Path / 运算符
    # 🔍 [作用] 拼接 assets 目录路径
    assets_dir = FRONTEND_DIST / "assets"

    # 🔍 [语法] 嵌套 if
    # 🔍 [作用] 仅当 assets 目录存在才挂载
    if assets_dir.exists():
        # 🔍 [语法] app.mount(path, app, name)
        # 🔍 [作用] 把 /assets 路径请求交给 StaticFiles 处理
        # 🔍 [示例] /assets/index-xxx.js → frontend/dist/assets/index-xxx.js
        # 🔍 [陷阱] mount 的路径必须以 / 开头且不能与现有路由冲突
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # 🔍 [语法] @app.get("/{path:path}") 路径参数
    # 🔍 [作用] 捕获所有未匹配路由（SPA fallback 到 index.html）
    # 🔍 [陷阱] include_in_schema=False 不在 OpenAPI 文档中显示
    @app.get("/{path:path}", include_in_schema=False)

    # 🔍 [语法] 函数签名 + path: str
    # 🔍 [作用] SPA 路由 fallback
    def serve_spa(path: str):
        # 🔍 [语法] Path / 运算符 + is_file()
        # 🔍 [作用] 拼接请求文件路径；判断是否是真实文件
        target = FRONTEND_DIST / path
        # 🔍 [语法] if condition
        # 🔍 [作用] 如果是文件则返回真实文件（如 favicon.ico、robots.txt）
        if target.is_file():
            return FileResponse(target)
        # 🔍 [语法] 否则返回 index.html
        # 🔍 [作用] SPA 客户端路由（如 /products/123 由前端 React Router 处理）
        # 🔍 [陷阱] 此 fallback 会捕获所有未匹配 URL（包括 API 错误 URL），需注意安全
        return FileResponse(FRONTEND_DIST / "index.html")
