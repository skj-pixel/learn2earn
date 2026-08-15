# 🔍 [语法] 模块级 docstring
# 🔍 [作用] F05 单元测试：LLM 配置"从环境变量导入 Key"
"""
F05 验收测试：LLM 配置支持从环境变量导入 API Key。

覆盖：
    1. api_key_env 指定变量名时，get_active() 能从该变量注入 Key
    2. api_key_env 未设置但全局 LEARN2EARN_LLM_API_KEY 存在时回退注入
    3. 两者皆无时 api_key 保持空（不误注入）
    4. api_key_env 优先于全局变量
    5. list_configs() 在环境变量可用时如实标记 has_key / key_source=env / api_key_env
    6. is_local_demo_mode() 返回布尔（不抛异常）
"""

import os
import pytest

# 🔍 [语法] 相对导入
# 🔍 [作用] 被测模块
from app.services.llm_config import (
    LLMConfig,
    MultiLLMConfig,
    _resolve_env_api_key,
    is_local_demo_mode,
)


# 🔍 [语法] pytest fixture
# 🔍 [作用] 每个用例前后清理相关环境变量，避免污染其他测试
@pytest.fixture(autouse=True)
def _clean_env():
    keys = ["F05_TEST_KEY", "F05_TEST_KEY_2", "LEARN2EARN_LLM_API_KEY"]
    saved = {k: os.environ.get(k) for k in keys}
    for k in keys:
        os.environ.pop(k, None)
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def _mgr_with(active: LLMConfig) -> MultiLLMConfig:
    # 🔍 [语法] 构造只含一个激活配置的管理器
    mgr = MultiLLMConfig()
    mgr.configs[active.name] = active
    mgr.active_config = active.name
    return mgr


def test_api_key_env_injected_via_get_active():
    # 🔍 [作用] api_key_env 指向的变量能被注入到激活配置
    os.environ["F05_TEST_KEY"] = "sk-from-env"
    cfg = LLMConfig(name="default", api_key_env="F05_TEST_KEY")
    mgr = _mgr_with(cfg)
    active = mgr.get_active()
    assert active is not None
    assert active.api_key == "sk-from-env"


def test_fallback_to_global_env_when_api_key_env_empty():
    # 🔍 [作用] 未设 api_key_env 时回退到全局 LEARN2EARN_LLM_API_KEY
    os.environ["LEARN2EARN_LLM_API_KEY"] = "sk-global"
    cfg = LLMConfig(name="default")
    mgr = _mgr_with(cfg)
    active = mgr.get_active()
    assert active.api_key == "sk-global"


def test_no_injection_when_both_missing():
    # 🔍 [作用] 两者皆无时 api_key 保持空字符串
    cfg = LLMConfig(name="default", api_key="")
    mgr = _mgr_with(cfg)
    active = mgr.get_active()
    assert active.api_key == ""


def test_api_key_env_takes_precedence_over_global():
    # 🔍 [作用] api_key_env 优先于全局变量
    os.environ["F05_TEST_KEY"] = "sk-specific"
    os.environ["LEARN2EARN_LLM_API_KEY"] = "sk-global"
    cfg = LLMConfig(name="default", api_key_env="F05_TEST_KEY")
    mgr = _mgr_with(cfg)
    active = mgr.get_active()
    assert active.api_key == "sk-specific"


def test_resolve_env_api_key_helper_priority():
    # 🔍 [作用] 辅助函数同样遵循优先级
    os.environ["F05_TEST_KEY"] = "a"
    os.environ["F05_TEST_KEY_2"] = "b"
    os.environ["LEARN2EARN_LLM_API_KEY"] = "c"
    cfg = LLMConfig(api_key_env="F05_TEST_KEY_2")
    assert _resolve_env_api_key(cfg) == "b"
    # 🔍 [作用] 清空 api_key_env 后应回退到全局
    cfg2 = LLMConfig(api_key_env="")
    assert _resolve_env_api_key(cfg2) == "c"


def test_list_configs_reflects_env_key():
    # 🔍 [作用] 环境变量可用时，列表标记 has_key 与来源
    os.environ["F05_TEST_KEY"] = "sk-list"
    cfg = LLMConfig(name="default", api_key_env="F05_TEST_KEY")
    mgr = _mgr_with(cfg)
    listed = mgr.list_configs()
    assert len(listed) == 1
    d = listed[0]
    assert d["has_key"] is True
    assert d["key_source"] == "env"
    assert d["api_key_env"] == "F05_TEST_KEY"


def test_is_local_demo_mode_returns_bool():
    # 🔍 [作用] 本地演示模式判定函数稳定返回布尔，不抛异常
    assert isinstance(is_local_demo_mode(), bool)
