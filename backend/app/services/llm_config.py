# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——LLM 配置管理（v2 多配置）
# 🔍 [陷阱] 占位 TODO 应人工补全
"""
把学习过程变成赚钱过程的app/backend/app/services/llm_config.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# llm_config.py - LLM API 配置管理模块（v2：支持10个自定义API）
# =============================================================================

import os
import json
from typing import Optional, Dict, List
from pydantic import BaseModel, Field


# --------------- 配置文件路径 ---------------

# 🔍 [语法] os.path.dirname + abspath
# 🔍 [作用] 获取本文件所在目录（backend/app/services/）
_CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# 🔍 [语法] os.path.join
# 🔍 [作用] 配置文件完整路径（llm_config.json 与本文件同目录）
CONFIG_FILE = os.path.join(_CONFIG_DIR, "llm_config.json")


# =============================================================================
# LLMConfig - 单个 LLM API 配置数据模型
# =============================================================================

# 🔍 [语法] Pydantic BaseModel
# 🔍 [作用] 单个 LLM 配置模型（字段约束 + 自动序列化）
class LLMConfig(BaseModel):
    """单个 LLM API 配置模型"""
    # 🔍 [语法] str 默认值
    # 🔍 [作用] 配置名称（唯一标识）
    name: str = "default"

    # 🔍 [语法] str 默认值
    # 🔍 [作用] 提供商类型（minimax/openrouter/custom 等）
    provider: str = "custom"

    # 🔍 [语法] str 默认空
    # 🔍 [作用] API 密钥（明文，仅本地存储；推荐改用 api_key_env 从环境变量注入）
    api_key: str = ""

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 从环境变量导入 Key 时的变量名（本地演示模式可用，避免明文落库）
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
    # 🔍 [作用] 生成温度
    temperature: float = 0.7

    # 🔍 [语法] bool 默认 False
    # 🔍 [作用] 是否启用
    is_enabled: bool = False

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 自定义系统提示词
    system_prompt: str = ""


# =============================================================================
# 提供商预设（6 家）
# =============================================================================

# 🔍 [语法] dict literal
# 🔍 [作用] 6 家 LLM 提供商预设（选择即自动填充 URL + 默认模型）
PROVIDER_PRESETS = {
    # 🔍 [语法] OpenRouter 预设
    # 🔍 [作用] 聚合 200+ 模型
    "openrouter": {
        "name": "OpenRouter", "description": "聚合200+模型",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "openai/gpt-4o",
        "get_api_key_url": "https://openrouter.ai/keys",
        "model_examples": ["openai/gpt-4o", "anthropic/claude-3.5-sonnet", "google/gemini-2.0-flash", "deepseek/deepseek-r1"],
    },
    # 🔍 [语法] ModelScope 预设
    # 🔍 [作用] 阿里达摩院通义千问
    "modelscope": {
        "name": "ModelScope（魔搭）", "description": "阿里达摩院·通义千问",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "default_model": "qwen-plus",
        "get_api_key_url": "https://bailian.console.aliyun.com/",
        "model_examples": ["qwen-plus", "qwen-max", "qwen-turbo", "deepseek-v3"],
    },
    # 🔍 [语法] 硅基流动预设
    # 🔍 [作用] 注册送额度，DeepSeek/Qwen/GLM
    "siliconflow": {
        "name": "硅基流动 (SiliconFlow)", "description": "DeepSeek/Qwen/GLM 等开源模型",
        "base_url": "https://api.siliconflow.cn/v1",
        "default_model": "deepseek-ai/DeepSeek-V3",
        "get_api_key_url": "https://cloud.siliconflow.cn/account/ak",
        "model_examples": ["deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1", "Qwen/Qwen2.5-72B-Instruct", "Pro/zai-org/GLM-4"],
    },
    # 🔍 [语法] MiniMax 预设
    # 🔍 [作用] 国产 abab6.5s
    "minimax": {
        "name": "MiniMax", "description": "国产大模型·abab6.5s",
        "base_url": "https://api.minimax.chat/v1",
        "default_model": "abab6.5s-chat",
        "get_api_key_url": "https://platform.minimaxi.com/user-center/basic-information/interface-key",
        "model_examples": ["abab6.5s-chat", "abab5.5-chat"],
    },
    # 🔍 [语法] TeamoRouter 预设
    "teamorouter": {
        "name": "TeamoRouter", "description": "多模型聚合路由",
        "base_url": "https://api.teamorouter.com/v1",
        "default_model": "gpt-4o",
        "get_api_key_url": "https://teamorouter.com/dashboard",
        "model_examples": ["gpt-4o", "claude-3.5-sonnet", "gemini-2.0-flash"],
    },
    # 🔍 [语法] custom 兜底
    # 🔍 [作用] 任意 OpenAI 兼容 API
    "custom": {
        "name": "自定义 OpenAI 兼容 API", "description": "任意兼容 OpenAI Chat Completions 格式",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o",
        "get_api_key_url": "",
        "model_examples": ["gpt-4o", "gpt-4-turbo", "claude-3-opus"],
    },
}


# =============================================================================
# 环境变量 Key 注入辅助
# =============================================================================

# 🔍 [语法] def + str 返回
# 🔍 [作用] 解析某配置实际可用的环境变量 Key（优先 api_key_env，回退全局 LEARN2EARN_LLM_API_KEY）
def _resolve_env_api_key(cfg: "LLMConfig") -> str:
    # 🔍 [语法] 优先读取本配置指定的环境变量名
    env_key = ""
    if cfg.api_key_env.strip():
        env_key = os.environ.get(cfg.api_key_env.strip(), "").strip()
    # 🔍 [语法] 回退到全局注入变量（向后兼容 2026-08 修复）
    if not env_key:
        env_key = os.environ.get("LEARN2EARN_LLM_API_KEY", "").strip()
    return env_key


# 🔍 [语法] def + bool 返回
# 🔍 [作用] 是否本地演示模式（未配置云数据库时为真）；仅此模式开放"从环境变量导入"
def is_local_demo_mode() -> bool:
    # 🔍 [语法] 延迟导入
    # 🔍 [作用] 避免与 cloud_db 形成循环依赖
    try:
        from ..cloud_db import cloud_is_configured
        return not cloud_is_configured()
    except Exception:
        # 🔍 [语法] 异常兜底
        # 🔍 [作用] 检测失败时保守地视为非本地模式（不暴露环境变量名）
        return False


# =============================================================================
# MultiLLMConfig - 多配置管理器
# =============================================================================

# 🔍 [语法] class
# 🔍 [作用] 管理多个 LLM API 配置（最多 10 个）
class MultiLLMConfig:
    """多配置管理器"""

    # 🔍 [语法] 类常量
    # 🔍 [作用] 最多 10 个配置
    MAX_CONFIGS = 10

    # 🔍 [语法] __init__
    # 🔍 [作用] 从文件加载或初始化空
    def __init__(self):
        # 🔍 [语法] 默认激活名
        # 🔍 [作用] 当前激活的配置名
        self.active_config: str = "default"

        # 🔍 [语法] Dict[str, LLMConfig]
        # 🔍 [作用] name → LLMConfig 映射
        self.configs: Dict[str, LLMConfig] = {}

    # 🔍 [语法] def + Dict 返回
    # 🔍 [作用] 转可 JSON 序列化的字典
    def to_dict(self) -> Dict:
        return {
            "active_config": self.active_config,
            # 🔍 [语法] dict comprehension
            # 🔍 [作用] 所有 LLMConfig 转字典
            "configs": {name: c.model_dump() for name, c in self.configs.items()},
        }

    # 🔍 [语法] classmethod
    # 🔍 [作用] 从字典恢复实例
    @classmethod
    def from_dict(cls, data: Dict) -> "MultiLLMConfig":
        mgr = cls()
        # 🔍 [语法] .get with default
        # 🔍 [作用] 默认值兼容旧配置
        mgr.active_config = data.get("active_config", "default")
        # 🔍 [语法] for 恢复每个配置
        for name, cfg_data in data.get("configs", {}).items():
            mgr.configs[name] = LLMConfig(**cfg_data)
        # 🔍 [语法] 回退逻辑
        # 🔍 [作用] active_config 指向不存在的配置时回退
        if mgr.active_config not in mgr.configs and mgr.configs:
            mgr.active_config = list(mgr.configs.keys())[0]
        return mgr

    # 🔍 [语法] def + bool 返回
    # 🔍 [作用] 新增配置（重名或超限返回 False）
    def add_config(self, config: LLMConfig) -> bool:
        # 🔍 [语法] 双重校验
        # 🔍 [作用] 重名 + 超限
        if config.name in self.configs:
            return False
        if len(self.configs) >= self.MAX_CONFIGS:
            return False
        # 🔍 [语法] dict 赋值
        self.configs[config.name] = config
        return True

    # 🔍 [语法] def + bool 返回
    # 🔍 [作用] 删除配置（不能删激活的）
    def delete_config(self, name: str) -> bool:
        # 🔍 [语法] 保护激活配置
        if name == self.active_config:
            return False
        if name in self.configs:
            del self.configs[name]
            return True
        return False

    # 🔍 [语法] def + Optional 返回
    # 🔍 [作用] 获取当前激活配置
    # 🔍 [安全] 2026-08 修复：明文 Key 不入库；api_key 为空时优先从 api_key_env 注入，回退到全局 LEARN2EARN_LLM_API_KEY
    def get_active(self) -> Optional[LLMConfig]:
        cfg = self.configs.get(self.active_config)
        if cfg is not None and not cfg.api_key.strip():
            # 🔍 [语法] 复用辅助函数解析环境变量 Key
            env_key = _resolve_env_api_key(cfg)
            if env_key:
                cfg = cfg.model_copy()
                cfg.api_key = env_key
        return cfg

    # 🔍 [语法] def + List 返回
    # 🔍 [作用] 列出所有配置（API Key 脱敏）
    def list_configs(self) -> List[Dict]:
        result = []
        for name, cfg in self.configs.items():
            d = cfg.model_dump()
            # 🔍 [语法] 脱敏逻辑
            # 🔍 [作用] 前 4 + **** + 后 4
            if len(cfg.api_key) > 8:
                d["api_key"] = cfg.api_key[:4] + "****" + cfg.api_key[-4:]
            else:
                d["api_key"] = "****" if cfg.api_key else ""
            # 🔍 [语法] 标记激活
            d["is_active"] = (name == self.active_config)
            # 🔍 [语法] bool
            # 🔍 [作用] 前端用此显示 Key 状态图标
            d["has_key"] = bool(cfg.api_key.strip())
            # 🔍 [安全/无感] 2026-08：配置 Key 为空但环境变量已注入时，
            #          列表如实反映"可用"，并脱敏展示环境变量 Key
            if not d["has_key"]:
                # 🔍 [语法] 复用辅助函数
                # 🔍 [作用] 同时支持本配置 api_key_env 与全局变量
                env_key = _resolve_env_api_key(cfg)
                if env_key:
                    d["has_key"] = True
                    d["api_key_env"] = cfg.api_key_env.strip() or "LEARN2EARN_LLM_API_KEY"
                    d["api_key"] = env_key[:4] + "****" + env_key[-4:] if len(env_key) > 8 else "****"
                    d["key_source"] = "env"
            result.append(d)
        return result


# =============================================================================
# 配置读写函数
# =============================================================================

# 🔍 [语法] def + 返回 MultiLLMConfig
# 🔍 [作用] 从 JSON 文件加载多配置
def load_multi_config() -> MultiLLMConfig:
    # 🔍 [语法] 早返回
    # 🔍 [作用] 文件不存在返回空
    if not os.path.exists(CONFIG_FILE):
        return MultiLLMConfig()

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            # 🔍 [语法] json.load
            # 🔍 [作用] 解析 JSON
            data = json.load(f)
        return MultiLLMConfig.from_dict(data)
    # 🔍 [语法] except 多异常
    # 🔍 [作用] JSON 解析失败或文件读取失败都返回空
    except (json.JSONDecodeError, Exception):
        return MultiLLMConfig()


# 🔍 [语法] def + 返回 None
# 🔍 [作用] 保存到 JSON 文件
def save_multi_config(mgr: MultiLLMConfig) -> None:
    # 🔍 [语法] with open + write
    # 🔍 [作用] 写入文件
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        # 🔍 [语法] ensure_ascii=False
        # 🔍 [作用] 中文不转义（直接保存）
        json.dump(mgr.to_dict(), f, ensure_ascii=False, indent=2)


# =============================================================================
# 兼容旧接口
# =============================================================================

# 🔍 [语法] def
# 🔍 [作用] 兼容旧代码：返回当前激活的单个配置
def load_config() -> LLMConfig:
    # 🔍 [语法] 委托
    # 🔍 [作用] 调用新版接口
    mgr = load_multi_config()
    # 🔍 [语法] 三元
    # 🔍 [作用] 兼容空配置情况
    active = mgr.get_active()
    return active if active else LLMConfig()


# 🔍 [语法] def
# 🔍 [作用] 兼容旧代码：用单个配置覆盖或新增
def save_config(config: LLMConfig) -> None:
    mgr = load_multi_config()
    # 🔍 [语法] or
    # 🔍 [作用] name 为空时用 "default"
    mgr.configs[config.name or "default"] = config
    # 🔍 [语法] 回退激活
    if not mgr.active_config or mgr.active_config not in mgr.configs:
        mgr.active_config = config.name or "default"
    save_multi_config(mgr)


# 🔍 [语法] def + dict 返回
# 🔍 [作用] 获取指定提供商的预设（前端用）
def get_provider_preset(provider: str) -> dict:
    # 🔍 [语法] dict.get with default
    # 🔍 [作用] 未知提供商返回 custom
    return PROVIDER_PRESETS.get(provider, PROVIDER_PRESETS["custom"])
