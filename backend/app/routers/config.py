# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——LLM 配置管理路由（v2：多配置支持）
# 🔍 [陷阱] 占位 TODO 应人工补全
"""
把学习过程变成赚钱过程的app/backend/app/routers/config.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# routers/config.py - LLM API 配置管理路由（v2：多配置支持）
# =============================================================================
# 提供多 LLM 配置的 CRUD 接口（最多10个自定义API）
# =============================================================================

# 🔍 [语法] FastAPI 导入
from fastapi import APIRouter, Depends, HTTPException

# 🔍 [语法] 标准库 + Pydantic BaseModel
import os
from pydantic import BaseModel

# 🔍 [语法] 相对导入
# 🔍 [作用] 导入 LLM 配置管理相关类与函数
from ..services.llm_config import (
    # 🔍 [语法] 多对象导入
    # 🔍 [作用] LLMConfig 数据模型；MultiLLMConfig 多配置管理器；文件读写；6 家提供商预设
    LLMConfig, MultiLLMConfig, load_multi_config, save_multi_config,
    PROVIDER_PRESETS, get_provider_preset, is_local_demo_mode,
)

# 🔍 [语法] 相对导入
# 🔍 [作用] LLM 服务 + 重载（切换配置后刷新）
from ..services.llm_service import LLMService, reload_llm_service
from ..auth import get_current_user


# 🔍 [语法] APIRouter 实例化
# 🔍 [作用] 配置路由：URL 前缀 /api/config
router = APIRouter(prefix="/api/config", tags=["config"])

KNOWN_LLM_ENV_VARS = (
    "LEARN2EARN_LLM_API_KEY",
    "OPENAI_API_KEY",
    "OPENROUTER_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "GEMINI_API_KEY",
    "DEEPSEEK_API_KEY",
    "DASHSCOPE_API_KEY",
    "MODELSCOPE_API_KEY",
    "SILICONFLOW_API_KEY",
    "MINIMAX_API_KEY",
    "TEAMOROUTER_API_KEY",
    "DOUBAO_CLOUD_API",
)


# =============================================================================
# Pydantic 请求模型
# =============================================================================

# 🔍 [语法] BaseModel
# 🔍 [作用] 新增/更新 LLM 配置请求体
class LLMSaveRequest(BaseModel):
    # 🔍 [语法] str 默认 "default"
    # 🔍 [作用] 配置名称（唯一标识）
    name: str = "default"

    # 🔍 [语法] str 默认 "custom"
    # 🔍 [作用] 提供商类型
    provider: str = "custom"

    # 🔍 [语法] str 默认空
    # 🔍 [作用] API 密钥
    api_key: str = ""

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 从环境变量导入 Key 时的变量名（本地演示模式可用）
    api_key_env: str = ""

    # 🔍 [语法] str 默认空
    # 🔍 [作用] API 基础地址
    base_url: str = ""

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 模型名称
    model: str = ""

    # 🔍 [语法] int 默认 4096
    # 🔍 [作用] 单次请求最大 token
    max_tokens: int = 4096

    # 🔍 [语法] float 默认 0.7
    # 🔍 [作用] 生成温度（0.0-2.0）
    temperature: float = 0.7

    # 🔍 [语法] bool 默认 False
    # 🔍 [作用] 是否启用
    is_enabled: bool = False

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 自定义系统提示词
    system_prompt: str = ""


# 🔍 [语法] BaseModel
# 🔍 [作用] 切换激活配置请求体
class SetActiveRequest(BaseModel):
    # 🔍 [语法] str 必填
    # 🔍 [作用] 要激活的配置名称
    name: str


# 🔍 [语法] BaseModel
# 🔍 [作用] 测试连接请求体
class TestRequest(BaseModel):
    # 🔍 [语法] str 必填
    # 🔍 [作用] 提供商
    provider: str

    # 🔍 [语法] str 必填
    # 🔍 [作用] API 密钥
    api_key: str = ""

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 从环境变量导入 Key 时的变量名（测试连接也支持）
    api_key_env: str = ""

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 地址
    base_url: str = ""

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 模型
    model: str = ""


# =============================================================================
# API 端点
# =============================================================================

# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/config/llms 列出所有配置
@router.get("/llms")
def list_configs(user: dict = Depends(get_current_user)):
    """获取所有LLM配置列表（api_key脱敏）"""
    # 🔍 [语法] 函数调用
    # 🔍 [作用] 从 JSON 文件加载多配置
    mgr = load_multi_config()
    # 🔍 [语法] dict 字面量
    # 🔍 [作用] 返回激活配置名 + 配置列表 + 数量
    return {
        "active_config": mgr.active_config,
        # 🔍 [语法] list_configs() 方法
        # 🔍 [作用] 自动脱敏 API Key（首 4 + **** + 末 4）
        "configs": mgr.list_configs(),
        "total": len(mgr.configs),
        # 🔍 [语法] 类常量
        # 🔍 [作用] 显示最大配置数限制
        "max": MultiLLMConfig.MAX_CONFIGS,
    }


# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/config/llms/active 获取当前激活配置
@router.get("/llms/active")
def get_active_config(user: dict = Depends(get_current_user)):
    """获取当前激活的LLM配置（api_key脱敏）"""
    mgr = load_multi_config()
    # 🔍 [语法] get_active()
    # 🔍 [作用] 获取当前激活配置
    active = mgr.get_active()
    # 🔍 [语法] 早返回
    # 🔍 [作用] 没有激活配置
    if not active:
        return {"active_config": None, "config": None, "message": "无可用配置"}
    # 🔍 [语法] model_dump()
    # 🔍 [作用] Pydantic v2 转字典
    d = active.model_dump()
    # 🔍 [语法] API Key 脱敏
    # 🔍 [作用] 前端展示时隐藏完整 Key
    if len(active.api_key) > 8:
        # 🔍 [语法] 字符串切片
        # 🔍 [作用] 首 4 + 中间 **** + 末 4
        d["api_key"] = active.api_key[:4] + "****" + active.api_key[-4:]
    else:
        # 🔍 [语法] 三元
        # 🔍 [作用] 短 key 全隐藏
        d["api_key"] = "****" if active.api_key else ""
    return {"active_config": mgr.active_config, "config": d}


# 🔍 [语法] @router.put
# 🔍 [作用] PUT /api/config/llms/active 切换激活
@router.put("/llms/active")
def set_active_config(data: SetActiveRequest, user: dict = Depends(get_current_user)):
    """切换当前激活的LLM配置"""
    mgr = load_multi_config()
    # 🔍 [语法] in 检查
    # 🔍 [作用] 校验配置存在
    if data.name not in mgr.configs:
        raise HTTPException(status_code=404, detail=f"配置 '{data.name}' 不存在")
    # 🔍 [语法] 赋值
    # 🔍 [作用] 切换激活名
    mgr.active_config = data.name
    save_multi_config(mgr)
    # 🔍 [语法] reload_llm_service()
    # 🔍 [作用] 重新加载 LLM 服务（让新配置生效）
    reload_llm_service()
    return {"active_config": data.name, "message": f"已切换到配置 '{data.name}'"}


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/config/llms 创建新配置
@router.post("/llms")
def create_config(data: LLMSaveRequest, user: dict = Depends(get_current_user)):
    """新增一个LLM配置"""
    # 🔍 [语法] 关键字检查
    # 🔍 [作用] "active" 是保留字（避免与 active_config 字段冲突）
    if data.name.lower() == "active":
        raise HTTPException(status_code=400, detail="配置名不能为 'active'，这是保留关键字")

    # 🔍 [语法] LLMConfig(**data.model_dump())
    # 🔍 [作用] 用 dict 创建 Pydantic 实例
    config = LLMConfig(**data.model_dump())

    mgr = load_multi_config()
    # 🔍 [语法] add_config 返回 bool
    # 🔍 [作用] 失败可能是重名或超限
    if not mgr.add_config(config):
        # 🔍 [语法] 细分错误原因
        # 🔍 [作用] 区分重名 vs 超限
        if data.name in mgr.configs:
            raise HTTPException(status_code=409, detail=f"配置名 '{data.name}' 已存在")
        raise HTTPException(status_code=400, detail=f"已达最大配置数({MultiLLMConfig.MAX_CONFIGS})")

    save_multi_config(mgr)
    return {"success": True, "name": data.name, "message": "配置已创建"}


# 🔍 [语法] @router.put + path 参数
# 🔍 [作用] PUT /api/config/llms/{name} 更新指定配置
@router.put("/llms/{name}")
def update_config(name: str, data: LLMSaveRequest, user: dict = Depends(get_current_user)):
    """更新指定名称的LLM配置"""
    mgr = load_multi_config()
    # 🔍 [语法] 404 检查
    if name not in mgr.configs:
        raise HTTPException(status_code=404, detail=f"配置 '{name}' 不存在")

    # 🔍 [语法] exclude_none=True
    # 🔍 [作用] 只更新提供的字段
    update_dict = data.model_dump(exclude_none=True)
    # 🔍 [语法] 空字符串视为不更新
    # 🔍 [作用] 避免覆盖现有 key
    if not update_dict.get("api_key"):
        update_dict.pop("api_key", None)

    # 🔍 [语法] setattr
    # 🔍 [作用] 动态更新字段
    existing = mgr.configs[name]
    for key, value in update_dict.items():
        setattr(existing, key, value)

    save_multi_config(mgr)
    reload_llm_service()
    return {"success": True, "name": name, "message": "配置已更新"}


# 🔍 [语法] @router.delete
# 🔍 [作用] DELETE /api/config/llms/{name} 删除配置
@router.delete("/llms/{name}")
def delete_config(name: str, user: dict = Depends(get_current_user)):
    """删除指定名称的LLM配置"""
    mgr = load_multi_config()
    # 🔍 [语法] 防止删除激活配置
    # 🔍 [作用] 必须先切换才能删除
    if name == mgr.active_config:
        raise HTTPException(status_code=400, detail="不能删除当前激活的配置，请先切换")
    if not mgr.delete_config(name):
        raise HTTPException(status_code=404, detail=f"配置 '{name}' 不存在")
    save_multi_config(mgr)
    return {"success": True, "name": name, "message": "配置已删除"}


# 🔍 [语法] @router.post async
# 🔍 [作用] POST /api/config/llms/test 测试连接
@router.post("/llms/test")
async def test_connection(data: TestRequest, user: dict = Depends(get_current_user)):
    """测试指定配置的LLM API连接"""
    # 🔍 [语法] get_provider_preset
    # 🔍 [作用] 获取提供商预设（base_url + default_model）
    preset = get_provider_preset(data.provider)

    # 🔍 [语法] 优先用明文 Key，否则尝试从环境变量导入
    # 🔍 [作用] 支持"从环境变量导入"配置也能一键测试
    api_key = data.api_key or ""
    if not api_key and data.api_key_env.strip():
        api_key = os.environ.get(data.api_key_env.strip(), "")

    # 🔍 [语法] dict 合并 + 三元
    # 🔍 [作用] 用户提供的值优先，缺失用预设
    temp_config = LLMConfig(
        provider=data.provider,
        api_key=api_key,
        # 🔍 [语法] or 短路
        # 🔍 [作用] 用户提供则用，否则用预设
        base_url=data.base_url or preset["base_url"],
        model=data.model or preset["default_model"],
        # 🔍 [语法] 测试时用较小参数
        # 🔍 [作用] 节省 token
        max_tokens=256,
        temperature=0.1,
        is_enabled=True,
    )

    # 🔍 [语法] LLMService 实例化
    # 🔍 [作用] 临时 LLM 服务（不替换全局）
    temp_service = LLMService(temp_config)

    # 🔍 [语法] is_ready 预检查
    # 🔍 [作用] 配置不完整直接返回
    if not temp_service.is_ready():
        return {"success": False, "error": "配置不完整", "elapsed_ms": 0}

    # 🔍 [语法] import time 局部导入
    # 🔍 [作用] 计时性能
    import time
    start = time.time()

    # 🔍 [语法] try/except
    # 🔍 [作用] 捕获所有异常
    try:
        # 🔍 [语法] await chat
        # 🔍 [作用] 异步调用 LLM 测试
        response = await temp_service.chat(
            "你好，请用一句话介绍你自己。",
            max_tokens=256,
            timeout=30,
        )
        # 🔍 [语法] 计时
        # 🔍 [作用] 毫秒级响应时间
        elapsed_ms = int((time.time() - start) * 1000)
        # 🔍 [语法] response[:300]
        # 🔍 [作用] 只返回前 300 字
        return {
            "success": True,
            "response": response[:300],
            "elapsed_ms": elapsed_ms,
        }
    # 🔍 [语法] except Exception
    # 🔍 [作用] 任何异常都返回失败
    except Exception as e:
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "success": False,
            "error": str(e),
            "elapsed_ms": elapsed_ms,
        }


# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/config/llms/providers 列出支持的提供商
@router.get("/llms/providers")
def get_providers(user: dict = Depends(get_current_user)):
    """获取所有支持的LLM提供商预设"""
    # 🔍 [语法] 直接返回常量
    # 🔍 [作用] 前端用此数据渲染提供商选择器
    return PROVIDER_PRESETS


# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/config/llms/env-import-meta 返回本地演示模式与可用环境变量名
@router.get("/llms/env-import-meta")
def env_import_meta(user: dict = Depends(get_current_user)):
    """本地演示模式下，暴露可导入 Key 的环境变量名（不含值）"""
    # 🔍 [语法] 本地演示模式判定
    # 🔍 [作用] 仅未配置云数据库时开放，避免在生产环境泄露环境变量名
    local = is_local_demo_mode()
    env_vars = []
    if local:
        # 🔍 [语法] 仅枚举疑似密钥类变量名（KEY/TOKEN/API/SECRET/PASSWORD），不含值
        # 🔍 [作用] 子集枚举策略：避免泄出与项目无关的环境变量；OpenRouter / LLM_KEY / Anthropic 等都在覆盖范围。
        patterns = ("KEY", "TOKEN", "API", "SECRET", "PASSWORD", "OPENROUTER")
        seen = set(KNOWN_LLM_ENV_VARS)
        for name in os.environ.keys():
            upper = name.upper()
            if any(p in upper for p in patterns):
                seen.add(name)
        env_vars = sorted(seen)
    return {"local_mode": local, "env_vars": env_vars}
