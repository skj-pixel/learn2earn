# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——LLM API 调用服务
# 🔍 [陷阱] 占位 TODO 应人工补全
"""
把学习过程变成赚钱过程的app/backend/app/services/llm_service.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# llm_service.py - LLM API 调用服务
# =============================================================================
# 功能：
#   1. 封装对 LLM API 的 HTTP 调用
#   2. 支持 OpenAI / Anthropic / Ollama / 企业私有化
#   3. 统一 OpenAI Chat Completions 格式
#   4. 内置重试机制和错误处理
#   5. 支持流式和非流式调用
# =============================================================================

# 🔍 [语法] httpx 导入
# 🔍 [作用] 异步 HTTP 客户端（替代 requests）
# 🔍 [陷阱] httpx.AsyncClient 用于异步；Client 用于同步
import httpx

# 🔍 [语法] typing 导入
# 🔍 [作用] Optional 用于可选参数；AsyncGenerator 用于流式
from typing import Optional, AsyncGenerator

# 🔍 [语法] json 模块
# 🔍 [作用] 解析 SSE 流式响应
import json
import asyncio

# 🔍 [语法] 相对导入
# 🔍 [作用] LLMConfig + load_config
from .llm_config import LLMConfig, load_config


# =============================================================================
# LLMService - LLM API 调用服务类
# =============================================================================
class LLMService:
    """LLM API 调用服务（所有 LLM 都遵循 OpenAI Chat Completions 格式）"""

    # 🔍 [语法] __init__ 方法
    # 🔍 [作用] 初始化服务（加载配置 + 构建请求头）
    def __init__(self, config: LLMConfig = None):
        # 🔍 [语法] 默认参数 + or 短路
        # 🔍 [作用] 传入配置优先；否则从 JSON 文件加载
        self.config = config or load_config()

        # 🔍 [语法] or 短路
        # 🔍 [作用] 自定义 system_prompt 优先；否则用默认
        self.system_prompt = self.config.system_prompt or self._default_system_prompt()

        # 🔍 [语法] dict 字面量
        # 🔍 [作用] 标准 Bearer Token 认证头
        self.headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

    # 🔍 [语法] 私有方法（下划线前缀）
    # 🔍 [作用] 默认系统提示词
    def _default_system_prompt(self) -> str:
        return """你是一位资深的知识付费产品创作专家，擅长将学习笔记转化为高质量的付费内容。

在生成内容时请遵循以下原则：
1. 实用导向：内容必须有实际价值，读者看完就能用
2. 结构化：使用清晰的标题层级、表格、列表
3. 变现视角：在合适的位置加入变现建议和推广入口
4. Markdown 格式：输出纯 Markdown 格式，支持代码块、表格、引用
5. 中文为主：面向中文用户，使用流畅的中文表达
6. 保持专业：避免过度营销，以专业内容建立信任

直接输出生成的内容，不要添加额外的解释和说明。"""

    # 🔍 [语法] def + 4 个 and 链
    # 🔍 [作用] 检查服务是否可用
    # 🔍 [示例] is_enabled + api_key + base_url + model 都齐全才返回 True
    def is_ready(self) -> bool:
        return (
            self.config.is_enabled
            and bool(self.config.api_key.strip())
            and bool(self.config.base_url.strip())
            and bool(self.config.model.strip())
        )

    @staticmethod
    def _extract_content(result: dict) -> str:
        choices = result.get("choices") or []
        if not choices:
            return str(result.get("output_text") or "").strip()
        choice = choices[0] or {}
        content = (choice.get("message") or {}).get("content", choice.get("text", ""))
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts).strip()
        return ""

    # 🔍 [语法] async def
    # 🔍 [作用] 非流式对话调用
    async def chat(
        self,
        user_message: str,
        # 🔍 [语法] 默认 None 表示用配置
        max_tokens: int = None,
        temperature: float = None,
        timeout: int = 120,
    ) -> str:
        """发送对话请求到 LLM API（非流式）"""
        # 🔍 [语法] 早返回
        # 🔍 [作用] 配置不完整直接抛错
        if not self.is_ready():
            raise Exception("LLM 服务未配置或未启用")

        # 🔍 [语法] OpenAI Chat Completions 协议
        # 🔍 [作用] 标准请求体（messages + max_tokens + temperature）
        body = {
            "model": self.config.model,
            "messages": [
                # 🔍 [语法] role: "system" / "user"
                # 🔍 [作用] OpenAI 标准角色
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            # 🔍 [语法] or 短路
            # 🔍 [作用] 参数用配置默认值
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
        }

        # 🔍 [语法] rstrip("/")
        # 🔍 [作用] URL 末尾去斜杠
        url = self.config.base_url.rstrip("/") + "/chat/completions"

        # 🔍 [语法] async with httpx.AsyncClient
        # 🔍 [作用] 异步 HTTP 请求（120 秒超时）
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(2):
                try:
                    response = await client.post(url, headers=self.headers, json=body)
                except (httpx.TimeoutException, httpx.NetworkError) as exc:
                    if attempt == 0:
                        await asyncio.sleep(0.5)
                        continue
                    detail = str(exc).strip() or "无错误详情"
                    raise RuntimeError(f"LLM API 网络超时（已自动重试 1 次）：{type(exc).__name__}: {detail}") from exc

            # 🔍 [语法] if status != 200
            # 🔍 [作用] 错误处理
                if response.status_code != 200:
                    error_detail = response.text
                # 🔍 [语法] try/except
                # 🔍 [作用] 提取 JSON 错误详情
                    try:
                        error_json = response.json()
                        error_detail = error_json.get("error", {}).get("message", response.text)
                    except Exception:
                        pass
                    if attempt == 0 and (response.status_code == 429 or response.status_code >= 500):
                        await asyncio.sleep(0.5)
                        continue
                    raise Exception(f"LLM API 调用失败 (HTTP {response.status_code}): {error_detail}")

            # 🔍 [语法] response.json()
            # 🔍 [作用] 解析响应
                result = response.json()
            # 🔍 [语法] .get 链式
            # 🔍 [作用] 安全取值（OpenAI 嵌套结构）
                content = self._extract_content(result)

            # 🔍 [语法] 早返回校验
            # 🔍 [作用] 空内容视为错误
                if content:
                    return content

                if attempt == 0:
                    body["temperature"] = min(float(body["temperature"]), 0.4)
                    body["messages"] = [
                        *body["messages"],
                        {"role": "user", "content": "上一次响应正文为空。请直接返回完整、非空的正文内容。"},
                    ]

        raise Exception("LLM API 返回了空内容（已自动重试 1 次）")

    # 🔍 [语法] async def + yield
    # 🔍 [作用] 流式 SSE 调用
    # 🔍 [陷阱] ⚠️ 当前实现 chat_stream() 用了 async def 但 yield 仅在 async 函数中合法
    async def chat_stream(
        self,
        user_message: str,
        max_tokens: int = None,
        temperature: float = None,
    ) -> AsyncGenerator[str, None]:
        """发送对话请求到 LLM API（流式 SSE）"""
        if not self.is_ready():
            raise Exception("LLM 服务未配置或未启用")

        # 🔍 [语法] 加 stream: True
        # 🔍 [作用] OpenAI 流式开关
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            "stream": True,  # 🔍 [语法] 流式开关
        }

        url = self.config.base_url.rstrip("/") + "/chat/completions"

        # 🔍 [语法] async with httpx.AsyncClient(timeout=300)
        # 🔍 [作用] 流式需要更长超时
        async with httpx.AsyncClient(timeout=300) as client:
            # 🔍 [语法] client.stream() 而非 client.post()
            # 🔍 [作用] 流式响应上下文
            async with client.stream("POST", url, headers=self.headers, json=body) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"LLM API 流式调用失败 (HTTP {response.status_code}): {error_text.decode()}")

                # 🔍 [语法] async for line in response.aiter_lines()
                # 🔍 [作用] SSE 按行迭代
                async for line in response.aiter_lines():
                    # 🔍 [语法] SSE 格式检查
                    if line.startswith("data: "):
                        data_str = line[6:]
                        # 🔍 [语法] 结束标记
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            # 🔍 [语法] delta.content
                            # 🔍 [作用] SSE 增量内容
                            delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            # 🔍 [语法] yield delta
                            # 🔍 [作用] 生成器逐步产出
                            if delta:
                                yield delta
                        # 🔍 [语法] 静默忽略
                        except json.JSONDecodeError:
                            continue

    # 🔍 [语法] 同步方法（被误用为 async）
    # 🔍 [作用] 同步方式调用 chat
    # 🔍 [陷阱] ⚠️ 此方法声明 def 而非 async def，但内部用 await，运行时错误
    async def chat_sync_wrapper(self, user_message: str, **kwargs) -> str:
        """同步方式调用 chat（供非 async 代码使用）"""
        return await self.chat(user_message, **kwargs)


# =============================================================================
# 模块级单例
# =============================================================================
# 🔍 [语法] 全局变量 + 类型注解
# 🔍 [作用] 全局 LLM 服务实例（懒加载单例）
# 🔍 [陷阱] 不是线程安全的（多线程并发可能创建多个）
_llm_service: Optional[LLMService] = None


# 🔍 [语法] def + 闭包
# 🔍 [作用] 懒加载获取 LLM 服务
def get_llm_service() -> LLMService:
    # 🔍 [语法] global 关键字
    # 🔍 [作用] 声明使用全局变量
    global _llm_service
    # 🔍 [语法] 延迟初始化
    # 🔍 [作用] 首次调用才创建实例
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service


# 🔍 [语法] def
# 🔍 [作用] 重新加载 LLM 服务（配置变更后）
def reload_llm_service() -> LLMService:
    """重新加载配置并创建新的 LLM 服务实例"""
    global _llm_service
    # 🔍 [语法] 直接重新创建
    # 🔍 [作用] 强制刷新
    _llm_service = LLMService()  # 会重新调用 load_config()
    return _llm_service
