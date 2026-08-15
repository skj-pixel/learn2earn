import asyncio
from copy import deepcopy

import httpx

from app.services.llm_config import LLMConfig
from app.services.llm_service import LLMService


class FakeResponse:
    status_code = 200
    text = ""

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


class FakeAsyncClient:
    def __init__(self, responses, *args, **kwargs):
        self.responses = responses
        self.requests = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def post(self, url, headers, json):
        self.requests.append(deepcopy(json))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


def service():
    return LLMService(LLMConfig(
        provider="custom",
        api_key="test-key",
        base_url="https://example.test/v1",
        model="test-model",
        is_enabled=True,
    ))


def test_chat_retries_once_when_provider_returns_empty_content(monkeypatch):
    client = FakeAsyncClient([
        {"choices": [{"message": {"content": ""}}]},
        {"choices": [{"message": {"content": "第二次返回正文"}}]},
    ])
    monkeypatch.setattr("app.services.llm_service.httpx.AsyncClient", lambda *a, **k: client)

    result = asyncio.run(service().chat("生成内容", max_tokens=8192))

    assert result == "第二次返回正文"
    assert len(client.requests) == 2
    assert client.requests[1]["max_tokens"] == client.requests[0]["max_tokens"]


def test_chat_extracts_text_from_structured_message_content(monkeypatch):
    client = FakeAsyncClient([{
        "choices": [{"message": {"content": [
            {"type": "text", "text": "结构化"},
            {"type": "text", "text": "正文"},
        ]}}],
    }])
    monkeypatch.setattr("app.services.llm_service.httpx.AsyncClient", lambda *a, **k: client)

    assert asyncio.run(service().chat("生成内容")) == "结构化\n正文"


def test_chat_retries_once_after_transient_timeout(monkeypatch):
    client = FakeAsyncClient([
        httpx.ReadTimeout("provider timed out"),
        {"choices": [{"message": {"content": "超时重试成功"}}]},
    ])
    monkeypatch.setattr("app.services.llm_service.httpx.AsyncClient", lambda *a, **k: client)

    assert asyncio.run(service().chat("生成内容")) == "超时重试成功"
    assert len(client.requests) == 2
