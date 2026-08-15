# =============================================================================
# tests/test_routers.py - API 路由层单元测试
# =============================================================================
# 使用 FastAPI TestClient 测试所有 REST API 端点：
#   1. Subject (科目) CRUD
#   2. Note (笔记) CRUD  
#   3. Product (产品) CRUD
#   4. AI 分析/生成接口
#   5. 统计接口
#   6. 错误处理（404/400）
# =============================================================================

import pytest
from app.services.llm_config import LLMConfig


class _RouterFakeLLM:
    def __init__(self):
        self.config = LLMConfig(
            provider="fake",
            api_key="fake-key",
            base_url="http://fake.local/v1",
            model="fake-model",
            max_tokens=4096,
            is_enabled=True,
        )

    def is_ready(self):
        return True

    async def chat(self, user_message: str, max_tokens=None, temperature=None, timeout=120):
        if "评审" in user_message or "审计" in user_message:
            return "OK"
        if "制定生成计划" in user_message:
            return "LLM_PLAN_MARKER\n- 目标用户：初学者\n- 交付边界：只基于源笔记"
        return "# LLM_MARKER\n\n## 可交付正文\n基于源笔记生成的高质量知识付费产品。"


@pytest.fixture(autouse=True)
def _avoid_real_llm_calls(monkeypatch):
    import app.routers.ai as ai_router

    fake_llm = _RouterFakeLLM()
    monkeypatch.setattr(ai_router, "reload_llm_service", lambda: fake_llm)
    monkeypatch.setattr(ai_router, "get_llm_service", lambda: fake_llm)


# =============================================================================
# 科目 API 测试
# =============================================================================
class TestSubjectAPI:
    """科目 CRUD API 端点测试"""

    def test_list_subjects_empty(self, client):
        """
        测试用例：空数据库的科目列表
        预期：200 状态码，返回空列表
        """
        response = client.get("/api/subjects")
        assert response.status_code == 200               # 成功
        assert response.json() == []                     # 空列表

    def test_create_subject(self, client):
        """
        测试用例：创建新科目
        验证点：201(因FastAPI自动)→实际validate是200或201
        检查返回的科目数据完整
        """
        response = client.post("/api/subjects", json={
            "name": "React前端开发",
            "icon": "⚛️",
            "description": "React从入门到精通",
            "color": "#61dafb",
        })
        assert response.status_code in [200, 201]        # 成功创建
        data = response.json()
        assert data["name"] == "React前端开发"            # 名称正确
        assert data["icon"] == "⚛️"                     # 图标正确
        assert data["description"] == "React从入门到精通"  # 描述正确
        assert "id" in data                              # 有 id

    def test_list_subjects_after_create(self, client):
        """
        测试用例：创建后列表查询
        验证点：列表中包含刚创建的科目
        """
        # 先创建一个科目
        client.post("/api/subjects", json={"name": "测试科目"})

        # 再查询列表
        response = client.get("/api/subjects")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1                            # 至少一个科目
        assert any(s["name"] == "测试科目" for s in data)  # 找到创建的科目

    def test_get_subject_by_id(self, client):
        """
        测试用例：按 ID 查询科目
        验证点：返回正确的科目数据
        """
        # 创建科目
        created = client.post("/api/subjects", json={
            "name": "单项查询测试"
        }).json()

        # 按 ID 查询
        response = client.get(f"/api/subjects/{created['id']}")
        assert response.status_code == 200
        assert response.json()["name"] == "单项查询测试"

    def test_get_subject_not_found(self, client):
        """
        测试用例：查询不存在的科目
        预期：404 状态码
        """
        response = client.get("/api/subjects/99999")
        assert response.status_code == 404               # 科目不存在
        assert "不存在" in response.json()["detail"]

    def test_update_subject(self, client):
        """
        测试用例：更新科目
        验证点：只更新传入的字段
        """
        # 创建
        created = client.post("/api/subjects", json={
            "name": "更新前名称",
            "icon": "📚",
        }).json()

        # 部分更新（只改名称）
        response = client.put(f"/api/subjects/{created['id']}", json={
            "name": "更新后名称",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "更新后名称"              # 名称已更新
        assert data["icon"] == "📚"                     # 图标未变

    def test_delete_subject(self, client):
        """
        测试用例：删除科目
        验证点：删除后查询返回 404
        """
        # 创建
        created = client.post("/api/subjects", json={
            "name": "待删除科目"
        }).json()

        # 删除
        response = client.delete(f"/api/subjects/{created['id']}")
        assert response.status_code == 200
        assert response.json()["ok"] is True

        # 验证已删除
        response = client.get(f"/api/subjects/{created['id']}")
        assert response.status_code == 404

    def test_delete_nonexistent_subject(self, client):
        """
        测试用例：删除不存在的科目
        预期：404
        """
        response = client.delete("/api/subjects/99999")
        assert response.status_code == 404


# =============================================================================
# 笔记 API 测试
# =============================================================================
class TestNoteAPI:
    """笔记 CRUD API 端点测试"""

    def test_create_note(self, client, sample_subject):
        """
        测试用例：创建笔记
        验证点：返回完整的笔记数据
        """
        response = client.post("/api/notes", json={
            "title": "Python 装饰器学习",
            "raw_content": "装饰器是 Python 的高级特性...",
            "subject_id": sample_subject.id,
            "tags": ["Python", "高级"],
            "learning_stage": "stage2",
            "estimated_minutes": 60,
        })
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["title"] == "Python 装饰器学习"
        assert data["subject_id"] == sample_subject.id
        assert "Python" in data["tags"]
        assert data["learning_stage"] == "stage2"

    def test_list_notes_by_subject(self, client, sample_subject):
        """
        测试用例：按科目筛选笔记
        验证点：只返回该科目的笔记
        """
        # 创建2篇笔记
        client.post("/api/notes", json={
            "title": "笔记1", "subject_id": sample_subject.id,
        })
        client.post("/api/notes", json={
            "title": "笔记2", "subject_id": sample_subject.id,
        })

        # 按科目 ID 筛选
        response = client.get(f"/api/notes?subject_id={sample_subject.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2                            # 至少2篇

    def test_list_note_summaries_does_not_transfer_full_large_content(self, client, sample_subject):
        raw_content = "大段正文" * 1000
        created = client.post("/api/notes", json={
            "title": "大笔记",
            "subject_id": sample_subject.id,
            "raw_content": raw_content,
        }).json()

        response = client.get(f"/api/notes?subject_id={sample_subject.id}&summary=true")
        assert response.status_code == 200
        note = next(item for item in response.json() if item["id"] == created["id"])
        assert len(note["raw_content"]) <= 500
        assert note["content_length"] == len(raw_content)

    def test_list_notes_by_stage(self, client, sample_subject):
        """
        测试用例：按学习阶段筛选
        验证点：只返回指定阶段的笔记
        """
        # 创建不同阶段的笔记
        client.post("/api/notes", json={
            "title": "筑基笔记", "subject_id": sample_subject.id,
            "learning_stage": "stage1",
        })
        client.post("/api/notes", json={
            "title": "专精笔记", "subject_id": sample_subject.id,
            "learning_stage": "stage2",
        })

        # 只查 stage1
        response = client.get("/api/notes?learning_stage=stage1")
        assert response.status_code == 200
        data = response.json()
        stages = [n["learning_stage"] for n in data]
        assert all(s == "stage1" for s in stages)        # 全部是 stage1

    def test_get_note_not_found(self, client):
        """
        测试用例：查询不存在的笔记
        预期：404
        """
        response = client.get("/api/notes/99999")
        assert response.status_code == 404

    def test_update_note(self, client, sample_subject):
        """
        测试用例：更新笔记
        验证点：字段正确更新
        """
        # 创建
        created = client.post("/api/notes", json={
            "title": "原始标题",
            "subject_id": sample_subject.id,
        }).json()

        # 更新
        response = client.put(f"/api/notes/{created['id']}", json={
            "title": "新标题",
            "is_completed": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "新标题"
        assert data["is_completed"] is True

    def test_delete_note(self, client, sample_subject):
        """
        测试用例：删除笔记
        验证点：删除后查询返回 404
        """
        created = client.post("/api/notes", json={
            "title": "待删除", "subject_id": sample_subject.id,
        }).json()

        response = client.delete(f"/api/notes/{created['id']}")
        assert response.status_code == 200

        response = client.get(f"/api/notes/{created['id']}")
        assert response.status_code == 404


# =============================================================================
# 产品 API 测试
# =============================================================================
class TestProductAPI:
    """产品 CRUD API 端点测试"""

    def test_create_product(self, client, sample_subject, sample_note):
        """
        测试用例：创建产品
        验证点：完整的产品数据
        """
        response = client.post("/api/products", json={
            "title": "Python列表推导式教程",
            "product_type": "article",
            "content": "# Python 列表推导式\n\n详细内容...",
            "subject_id": sample_subject.id,
            "note_id": sample_note.id,
            "price_suggestion": 19.0,
            "platform_suggestion": ["CSDN", "掘金"],
            "keywords": ["Python", "列表"],
        })
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["title"] == "Python列表推导式教程"
        assert data["product_type"] == "article"
        assert data["price_suggestion"] == 19.0
        assert data["status"] == "draft"                 # 默认草稿

    def test_list_products(self, client, sample_subject):
        """
        测试用例：查询产品列表
        验证点：返回所有产品
        """
        # 创建2个产品
        client.post("/api/products", json={
            "title": "产品A", "product_type": "article",
            "subject_id": sample_subject.id,
        })
        client.post("/api/products", json={
            "title": "产品B", "product_type": "sop",
            "subject_id": sample_subject.id,
        })

        response = client.get("/api/products")
        assert response.status_code == 200
        assert len(response.json()) >= 2

    def test_filter_products_by_type(self, client, sample_subject):
        """
        测试用例：按产品类型筛选
        验证点：只返回指定类型
        """
        client.post("/api/products", json={
            "title": "文章", "product_type": "article",
            "subject_id": sample_subject.id,
        })
        client.post("/api/products", json={
            "title": "SOP", "product_type": "sop",
            "subject_id": sample_subject.id,
        })

        response = client.get("/api/products?product_type=article")
        data = response.json()
        types = [p["product_type"] for p in data]
        assert all(t == "article" for t in types)

    def test_publish_product(self, client, sample_subject):
        """
        测试用例：发布产品（状态转换）
        验证点：status 从 draft 变为 published
        """
        created = client.post("/api/products", json={
            "title": "待发布", "product_type": "article",
            "subject_id": sample_subject.id,
        }).json()

        # 发布
        response = client.put(f"/api/products/{created['id']}", json={
            "status": "published",
        })
        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_delete_product(self, client, sample_subject):
        """
        测试用例：删除产品
        验证点：删除后返回 404
        """
        created = client.post("/api/products", json={
            "title": "待删除", "product_type": "article",
            "subject_id": sample_subject.id,
        }).json()

        response = client.delete(f"/api/products/{created['id']}")
        assert response.status_code == 200

        response = client.get(f"/api/products/{created['id']}")
        assert response.status_code == 404


# =============================================================================
# AI API 测试
# =============================================================================
class TestAIAPI:
    """AI 生成相关 API 端点测试"""

    def test_get_product_types(self, client):
        """
        测试用例：获取所有产品类型
        验证点：返回 14 种产品类型
        """
        response = client.get("/api/ai/product-types")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 14                            # 支持扩展后的产品类型
        # 验证第一条记录的结构
        assert "type" in data[0]
        assert "name" in data[0]
        assert "icon" in data[0]
        assert "price_range" in data[0]
        assert "platforms" in data[0]

    def test_analyze_content(self, client):
        """
        测试用例：分析笔记内容
        验证点：返回 analysis 和 suggestions
        """
        response = client.post("/api/ai/analyze", json={
            "content": "Python入门学习笔记，基础语法和数据类型。\nHello World程序。",
            "subject_name": "Python",
        })
        assert response.status_code == 200
        data = response.json()

        # 验证 analysis
        assert "analysis" in data
        assert "word_count" in data["analysis"]
        assert "keywords" in data["analysis"]

        # 验证 suggestions
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0
        # 验证 suggestion 结构
        first = data["suggestions"][0]
        assert "type" in first
        assert "reason" in first
        assert "name" in first
        assert "icon" in first

    def test_analyze_empty_content(self, client):
        """
        测试用例：分析空内容
        验证点：返回 error
        """
        response = client.post("/api/ai/analyze", json={
            "content": "",
            "subject_name": "",
        })
        assert response.status_code == 200
        data = response.json()
        assert "error" in data["analysis"]

    def test_generate_products(self, client, sample_note):
        """
        测试用例：生成指定的产品类型
        验证点：生成成功，返回产品和内容
        """
        response = client.post("/api/ai/generate", json={
            "note_id": sample_note.id,
            "product_types": ["article", "sop", "mindmap"],
            "save_to_db": True,
        })
        assert response.status_code == 200
        data = response.json()

        assert data["note_id"] == sample_note.id
        assert data["generated"] == 3                     # 生成了3个
        assert len(data["products"]) == 3

        # 验证每个产品都有内容
        for product in data["products"]:
            assert product["success"] is True
            assert len(product["content"]) > 0
            assert "type" in product
            assert "id" in product                        # 存入了数据库

    def test_generate_products_no_save(self, client, sample_note):
        """
        测试用例：生成但不保存到数据库
        验证点：返回内容但无 id
        """
        response = client.post("/api/ai/generate", json={
            "note_id": sample_note.id,
            "product_types": ["article"],
            "save_to_db": False,
        })
        assert response.status_code == 200
        data = response.json()
        # 不保存时不应有 id
        assert "id" not in data["products"][0]
        assert len(data["products"][0]["content"]) > 0

    def test_generate_products_empty_note(self, client, sample_subject):
        """
        测试用例：空笔记生成产品
        预期：400 错误
        """
        # 创建空内容笔记
        created = client.post("/api/notes", json={
            "title": "空笔记",
            "raw_content": "",
            "subject_id": sample_subject.id,
        }).json()

        response = client.post("/api/ai/generate", json={
            "note_id": created["id"],
            "product_types": ["article"],
        })
        assert response.status_code == 400               # 内容为空

    def test_generate_nonexistent_note(self, client):
        """
        测试用例：不存在的笔记生成产品
        预期：404
        """
        response = client.post("/api/ai/generate", json={
            "note_id": 99999,
            "product_types": ["article"],
        })
        assert response.status_code == 404

    def test_generate_all(self, client, sample_note):
        """
        测试用例：一键生成全部推荐产品
        验证点：生成多个产品
        """
        response = client.post("/api/ai/generate-all", json={
            "note_id": sample_note.id,
            "save_to_db": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["generated"] > 0                     # 至少生成了一个

    def test_suggest_for_note(self, client, sample_note):
        """
        测试用例：为笔记智能推荐产品类型
        验证点：返回 analysis + suggestions
        """
        response = client.get(f"/api/ai/suggest/{sample_note.id}")
        assert response.status_code == 200
        data = response.json()

        assert data["note_id"] == sample_note.id
        assert data["note_title"] == sample_note.title
        assert "analysis" in data
        assert "suggestions" in data
        assert len(data["suggestions"]) > 0

    def test_suggest_nonexistent_note(self, client):
        """
        测试用例：为不存在的笔记推荐
        预期：404
        """
        response = client.get("/api/ai/suggest/99999")
        assert response.status_code == 404


# =============================================================================
# 统计 API 测试
# =============================================================================
class TestStatsAPI:
    """统计接口测试"""

    def test_stats_empty(self, client):
        """
        测试用例：空数据库的统计
        验证点：所有计数为 0
        """
        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["subjects"] == 0
        assert data["notes"] == 0
        assert data["products"] == 0
        assert data["estimated_total_value"] == 0

    def test_stats_with_data(self, client, sample_subject, sample_note):
        """
        测试用例：有数据的统计
        验证点：统计数字正确
        """
        # 创建几个产品
        client.post("/api/products", json={
            "title": "测试产品1", "product_type": "article",
            "subject_id": sample_subject.id,
            "note_id": sample_note.id,
            "price_suggestion": 29.0,
        })
        client.post("/api/products", json={
            "title": "测试产品2", "product_type": "course_outline",
            "subject_id": sample_subject.id,
            "note_id": sample_note.id,
            "price_suggestion": 99.0,
        })

        response = client.get("/api/stats")
        assert response.status_code == 200
        data = response.json()
        assert data["subjects"] >= 1                     # 至少1个科目
        assert data["notes"] >= 1                        # 至少1篇笔记
        assert data["products"] >= 2                     # 至少2个产品
        assert data["estimated_total_value"] > 0         # 有潜在收入


# =============================================================================
# 根路径测试
# =============================================================================
class TestRootAPI:
    """根路径测试"""

    def test_root_endpoint(self, client):
        """
        测试用例：访问根路径
        验证点：返回欢迎信息
        """
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Welcome to Learn2Earn API"
        assert data["version"] == "5.1.0"
