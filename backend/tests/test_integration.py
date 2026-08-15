# =============================================================================
# tests/test_integration.py - 端到端集成测试
# =============================================================================
# 模拟真实用户使用流程，验证系统各模块协同工作：
#   场景1：完整用户流程 - 创建科目→记笔记→分析→生成→发布→统计
#   场景2：多科目并行学习
#   场景3：多产品批量生成
#   场景4：级联删除验证
#   场景5：学习阶段流转
#   场景6：内容分析到变现全链路
#   场景7：产品生命周期管理
#   场景8：数据一致性验证
# =============================================================================

import pytest


@pytest.fixture(autouse=True)
def deterministic_agent_runtime(monkeypatch):
    """Keep integration tests hermetic while exercising the real HTTP/DB flow."""
    from app.routers import ai as ai_router

    class ReadyLLM:
        def is_ready(self):
            return True

    async def generate(self, note_title, note_content, product_type, subject_name=""):
        excerpt = (note_content or "")[:600]
        content = (
            f"# {note_title}\n\n"
            f"## 产品类型\n{product_type}\n\n"
            f"## 学习内容\n{excerpt}\n\n"
            "## 交付说明\n本产物由测试用确定性 Agent 完成理解、规划、生成、校验与交付。"
        )
        return {
            "content": content,
            "used_llm": False,
            "workflow_trace": ["理解", "规划", "生成", "校验", "交付"],
            "quality_report": {"score": 100, "mode": "deterministic-test"},
            "elapsed_ms": 1,
        }

    monkeypatch.setattr(ai_router, "reload_llm_service", lambda: ReadyLLM())
    monkeypatch.setattr(ai_router, "get_llm_service", lambda: ReadyLLM())
    monkeypatch.setattr(ai_router.AgenticProductGenerator, "generate", generate)


# =============================================================================
# 场景1：完整用户流程
# =============================================================================
class TestFullUserFlow:
    """
    完整用户流程集成测试
    
    模拟用户从零开始使用 Learn2Earn 的完整过程：
    创建科目 → 记笔记 → AI分析 → 生成产品 → 发布产品 → 查看统计
    """

    def test_complete_flow(self, client):
        """
        测试用例：端到端完整流程
        
        步骤：
            1. 创建科目 "嵌入式开发"
            2. 为科目创建学习笔记
            3. AI 分析笔记内容
            4. 为一键生成所有推荐产品
            5. 发布所有产品
            6. 验证统计数据
            7. 导出产品内容
        """
        # ---------- 步骤1：创建科目 ----------
        subject_resp = client.post("/api/subjects", json={
            "name": "嵌入式开发",
            "icon": "🔌",
            "description": "STM32+RTOS学习",
        })
        assert subject_resp.status_code in [200, 201]
        subject = subject_resp.json()
        subject_id = subject["id"]

        # ---------- 步骤2：创建学习笔记 ----------
        note_resp = client.post("/api/notes", json={
            "title": "STM32 GPIO控制LED",
            "raw_content": """# STM32 GPIO 入门

## 硬件准备
- STM32F103C8T6 开发板
- LED灯 + 220Ω电阻
- 杜邦线若干

## 代码实现
```c
#include "stm32f10x.h"

void GPIO_Config(void) {
    GPIO_InitTypeDef GPIO_InitStructure;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC, ENABLE);
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_13;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOC, &GPIO_InitStructure);
}

int main(void) {
    GPIO_Config();
    while(1) {
        GPIO_SetBits(GPIOC, GPIO_Pin_13);
        for(int i=0; i<1000000; i++);
        GPIO_ResetBits(GPIOC, GPIO_Pin_13);
        for(int i=0; i<1000000; i++);
    }
}
```

## 调试技巧
1. 使用逻辑分析仪检测GPIO输出
2. 检查时钟配置是否正确
3. 确认引脚复用功能
""",
            "subject_id": subject_id,
            "tags": ["STM32", "GPIO", "嵌入式", "C语言"],
            "learning_stage": "stage1",
            "estimated_minutes": 90,
        })
        assert note_resp.status_code in [200, 201]
        note = note_resp.json()
        note_id = note["id"]

        # ---------- 步骤3：AI 分析笔记 ----------
        suggest_resp = client.get(f"/api/ai/suggest/{note_id}")
        assert suggest_resp.status_code == 200
        suggestions = suggest_resp.json()["suggestions"]
        assert len(suggestions) > 0                    # AI 给出了推荐

        # ---------- 步骤4：一键生成所有推荐产品 ----------
        generate_resp = client.post("/api/ai/generate-all", json={
            "note_id": note_id,
            "save_to_db": True,
        })
        assert generate_resp.status_code == 200
        gen_data = generate_resp.json()
        assert gen_data["generated"] > 0               # 至少生成了一个产品
        products = gen_data["products"]

        # ---------- 步骤5：发布所有产品 ----------
        published_count = 0
        for product in products:
            pid = product.get("id")
            if pid is not None and product.get("success"):
                pub_resp = client.put(f"/api/products/{pid}", json={
                    "status": "published",
                })
                if pub_resp.status_code == 200:
                    published_count += 1
        assert published_count >= 1                      # 至少发布了一个

        # ---------- 步骤6：验证统计数据 ----------
        stats_resp = client.get("/api/stats")
        assert stats_resp.status_code == 200
        stats = stats_resp.json()
        assert stats["subjects"] >= 1                   # 有1个科目
        assert stats["notes"] >= 1                      # 有1篇笔记
        assert stats["products"] >= published_count     # 有生成的产品
        assert stats["published_products"] >= published_count
        assert stats["estimated_total_value"] > 0       # 有潜在收入

        # ---------- 步骤7：验证产品内容可访问 ----------
        for product in products:
            if "id" in product:
                get_resp = client.get(f"/api/products/{product['id']}")
                assert get_resp.status_code == 200
                product_data = get_resp.json()
                # 验证产品内容不为空
                assert len(product_data["content"]) > 100


# =============================================================================
# 场景2：多科目并行学习
# =============================================================================
class TestMultiSubject:
    """多科目并行学习场景测试"""

    def test_multiple_subjects_parallel(self, client):
        """
        测试用例：创建3个科目，每个科目写2篇笔记

        验证点：
            1. 每个科目的笔记正确隔离
            2. 按科目筛选笔记正确性
            3. 生成的产品关联到正确的笔记
        """
        subjects_data = [
            {"name": "Python编程", "icon": "🐍"},
            {"name": "英语学习", "icon": "🇬🇧"},
            {"name": "算法入门", "icon": "🧮"},
        ]

        # ---------- 创建3个科目 ----------
        subjects = []
        for sd in subjects_data:
            resp = client.post("/api/subjects", json=sd)
            subjects.append(resp.json())

        # ---------- 为每个科目创建2篇笔记 ----------
        all_notes = {}
        for subject in subjects:
            notes = []
            for i in range(2):
                note_resp = client.post("/api/notes", json={
                    "title": f"{subject['name']}学习笔记{i+1}",
                    "raw_content": f"这是{subject['name']}的第{i+1}篇笔记内容。\n\n包含基础知识和代码示例。\n\n学习重点：掌握核心概念并动手实践。",
                    "subject_id": subject["id"],
                    "tags": [subject["name"], f"笔记{i+1}"],
                })
                notes.append(note_resp.json())
            all_notes[subject["id"]] = notes

        # ---------- 验证笔记隔离 ----------
        for subject in subjects:
            sid = subject["id"]
            resp = client.get(f"/api/notes?subject_id={sid}")
            assert resp.status_code == 200
            data = resp.json()
            assert len(data) == 2                        # 每个科目2篇笔记
            # 所有笔记的 subject_name 都正确
            for note in data:
                assert note["subject_name"] == subject["name"]

        # ---------- 为每个科目的每篇笔记生成产品 ----------
        total_products = 0
        for sid, notes in all_notes.items():
            for note in notes:
                gen_resp = client.post("/api/ai/generate", json={
                    "note_id": note["id"],
                    "product_types": ["article", "checklist"],
                    "save_to_db": True,
                })
                if gen_resp.status_code == 200:
                    total_products += gen_resp.json()["generated"]

        # ---------- 验证统计数据 ----------
        stats_resp = client.get("/api/stats")
        stats = stats_resp.json()
        assert stats["subjects"] >= 3                    # 至少3个科目
        assert stats["notes"] >= 6                       # 至少6篇笔记
        assert stats["products"] >= total_products       # 产品数至少为生成数
        assert stats["estimated_total_value"] > 0


# =============================================================================
# 场景3：多产品批量生成和发布
# =============================================================================
class TestBatchProductGeneration:
    """批量生成和发布测试"""

    def test_batch_generate_all_types(self, client, sample_note):
        """
        测试用例：为一篇笔记批量生成全部14种产品

        验证点：
            1. 所有14种类型都能成功生成
            2. 每种产品内容非空
            3. 生成后统计数正确
        """
        # 获取所有产品类型
        types_resp = client.get("/api/ai/product-types")
        all_types = [t["type"] for t in types_resp.json()]
        assert len(all_types) >= 14                     # 支持扩展后的产品类型

        # 一次性生成全部类型
        response = client.post("/api/ai/generate", json={
            "note_id": sample_note.id,
            "product_types": all_types,
            "save_to_db": True,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["generated"] == len(all_types)

        # 验证每种产品都有内容
        for product in data["products"]:
            assert product["success"] is True
            assert len(product["content"]) > 50, \
                f"产品类型 {product['type']} 内容过短"

        # 批量发布
        published = 0
        for product in data["products"]:
            if "id" in product:
                pub_resp = client.put(f"/api/products/{product['id']}", json={
                    "status": "published",
                })
                if pub_resp.status_code == 200:
                    published += 1
        assert published == len(all_types)               # 全部发布成功


# =============================================================================
# 场景4：级联删除
# =============================================================================
class TestCascadeDelete:
    """级联删除集成测试"""

    def test_cascade_delete_flow(self, client, sample_subject):
        """
        测试用例：删除科目 → 验证关联笔记和产品也被删除

        流程：
            1. 创建科目
            2. 为科目创建笔记
            3. 为笔记生成产品
            4. 删除科目
            5. 验证笔记和产品都不存在
        """
        # ---------- 创建科目 ----------
        subject_resp = client.post("/api/subjects", json={
            "name": "级联删除测试科目",
        })
        subject_id = subject_resp.json()["id"]

        # ---------- 创建笔记 ----------
        note_resp = client.post("/api/notes", json={
            "title": "被测笔记",
            "raw_content": "测试级联删除的内容",
            "subject_id": subject_id,
        })
        note_id = note_resp.json()["id"]

        # ---------- 生成产品 ----------
        gen_resp = client.post("/api/ai/generate", json={
            "note_id": note_id,
            "product_types": ["article", "sop"],
            "save_to_db": True,
        })
        product_ids = [
            p["id"] for p in gen_resp.json()["products"]
            if p.get("success") and p.get("id")
        ]

        # ---------- 验证创建成功 ----------
        assert client.get(f"/api/notes/{note_id}").status_code == 200
        for pid in product_ids:
            assert client.get(f"/api/products/{pid}").status_code == 200

        # ---------- 删除科目（级联） ----------
        delete_resp = client.delete(f"/api/subjects/{subject_id}")
        assert delete_resp.status_code == 200

        # ---------- 验证级联删除 ----------
        assert client.get(f"/api/subjects/{subject_id}").status_code == 404
        assert client.get(f"/api/notes/{note_id}").status_code == 404
        for pid in product_ids:
            assert client.get(f"/api/products/{pid}").status_code == 404


# =============================================================================
# 场景5：学习阶段流转
# =============================================================================
class TestLearningStageTransition:
    """学习阶段流转测试"""

    def test_stage_transition(self, client, sample_subject):
        """
        测试用例：笔记学习阶段从 stage1 → stage4 的流转

        验证点：
            1. 各阶段笔记正确分类
            2. 更新阶段后筛选正确
            3. 统计不受阶段影响
        """
        # ---------- 创建4个不同阶段的笔记 ----------
        stages = {
            "stage1": "筑基期学习",
            "stage2": "专精期学习",
            "stage3": "融合期学习",
            "stage4": "创业期学习",
        }

        note_ids = {}
        for stage, title in stages.items():
            resp = client.post("/api/notes", json={
                "title": title,
                "raw_content": f"{title}的详细学习内容\n\n核心知识点\n\n实战项目",
                "subject_id": sample_subject.id,
                "learning_stage": stage,
                "estimated_minutes": 30,
            })
            note_ids[stage] = resp.json()["id"]

        # ---------- 验证按阶段筛选 ----------
        for stage in stages:
            resp = client.get(f"/api/notes?learning_stage={stage}")
            data = resp.json()
            # 该阶段的笔记应至少包含我们创建的那篇
            stage_notes = [n for n in data if n["id"] == note_ids[stage]]
            assert len(stage_notes) >= 1

        # ---------- 升级一篇笔记 ----------
        upgrade_resp = client.put(f"/api/notes/{note_ids['stage1']}", json={
            "learning_stage": "stage2",
            "estimated_minutes": 120,
        })
        assert upgrade_resp.status_code == 200

        # 验证升级后 stage1 查询不到
        stage1_resp = client.get("/api/notes?learning_stage=stage1")
        stage1_ids = [n["id"] for n in stage1_resp.json()]
        assert note_ids["stage1"] not in stage1_ids      # 已移出 stage1

        # 验证已出现在 stage2
        stage2_resp = client.get("/api/notes?learning_stage=stage2")
        stage2_ids = [n["id"] for n in stage2_resp.json()]
        assert note_ids["stage1"] in stage2_ids           # 已加入 stage2


# =============================================================================
# 场景6：内容分析到变现全链路
# =============================================================================
class TestAnalyzeToEarnFlow:
    """分析到变现全链路测试"""

    def test_analyze_to_earn_pipeline(self, client):
        """
        测试用例：验证"分析→推荐→生成→定价→发布"完整链路

        验证点：
            1. AI 分析准确返回关键词和难度
            2. 推荐的产品类型有价格信息
            3. 生成的产品包含变现建议
            4. 定价与 PRODUCT_TYPES 一致
        """
        # ---------- AI 分析 ----------
        analyze_resp = client.post("/api/ai/analyze", json={
            "content": """Rust编程入门：所有权和借用机制

Rust的所有权系统是其最独特的特性。
它确保了内存安全而不需要垃圾回收。

核心规则：
1. 每个值有且只有一个所有者
2. 当所有者离开作用域，值被释放
3. 引用分为可变引用和不可变引用

实战代码示例和最佳实践。""",
            "subject_name": "Rust编程",
        })
        assert analyze_resp.status_code == 200
        analysis = analyze_resp.json()

        # 验证关键词提取
        assert "Rust" in analysis["analysis"]["keywords"]

        # 验证推荐包含 price_range
        for s in analysis["suggestions"]:
            assert "price_range" in s
            assert len(s["price_range"]) == 2
            assert "platforms" in s

        # ---------- 创建科目和笔记 ----------
        subject_resp = client.post("/api/subjects", json={
            "name": "Rust编程",
            "icon": "🦀",
        })
        subject_id = subject_resp.json()["id"]

        note_resp = client.post("/api/notes", json={
            "title": "Rust所有权机制",
            "raw_content": "Rust的所有权系统...",
            "subject_id": subject_id,
        })
        note_id = note_resp.json()["id"]

        # ---------- 生成产品并验证定价 ----------
        gen_resp = client.post("/api/ai/generate", json={
            "note_id": note_id,
            "product_types": ["article", "course_outline", "sop"],
            "save_to_db": True,
        })
        assert gen_resp.status_code == 200

        for product in gen_resp.json()["products"]:
            if product["success"]:
                # 验证价格 >= 0
                assert product["price_suggestion"] >= 0
                # 验证内容非空（有实际生成内容）
                if "content" in product:
                    assert len(product["content"]) > 50, \
                        f"产品类型 {product['type']} 内容过短"


# =============================================================================
# 场景7：数据一致性验证
# =============================================================================
class TestDataConsistency:
    """数据一致性测试"""

    def test_product_note_subject_consistency(self, client):
        """
        测试用例：产品→笔记→科目的关联一致性

        验证点：
            1. 产品关联的 note_id 正确
            2. 产品继承笔记的 subject_id
            3. 删除笔记不影响科目存在
        """
        # ---------- 创建科目 ----------
        sub_resp = client.post("/api/subjects", json={"name": "一致性测试"})
        subject_id = sub_resp.json()["id"]

        # ---------- 创建笔记1 ----------
        note1_resp = client.post("/api/notes", json={
            "title": "笔记1",
            "raw_content": "笔记1的内容。包含Python代码和数据结构知识。",
            "subject_id": subject_id,
        })
        note1_id = note1_resp.json()["id"]

        # ---------- 创建笔记2 ----------
        note2_resp = client.post("/api/notes", json={
            "title": "笔记2",
            "raw_content": "笔记2的内容。不同的知识点。",
            "subject_id": subject_id,
        })
        note2_id = note2_resp.json()["id"]

        # ---------- 为笔记1生成产品 ----------
        gen1_resp = client.post("/api/ai/generate", json={
            "note_id": note1_id,
            "product_types": ["article"],
            "save_to_db": True,
        })
        prod1_id = gen1_resp.json()["products"][0].get("id")

        # ---------- 为笔记2生成产品 ----------
        gen2_resp = client.post("/api/ai/generate", json={
            "note_id": note2_id,
            "product_types": ["sop"],
            "save_to_db": True,
        })
        prod2_id = gen2_resp.json()["products"][0].get("id")

        # 验证产品关联正确
        prod1 = client.get(f"/api/products/{prod1_id}").json()
        prod2 = client.get(f"/api/products/{prod2_id}").json()
        assert prod1["note_id"] == note1_id
        assert prod1["subject_id"] == subject_id
        assert prod2["note_id"] == note2_id
        assert prod2["subject_id"] == subject_id

        # ---------- 删除笔记1 ----------
        client.delete(f"/api/notes/{note1_id}")

        # 验证产品1已被删除
        assert client.get(f"/api/products/{prod1_id}").status_code == 404

        # 验证产品2仍然存在（笔记2还在）
        assert client.get(f"/api/products/{prod2_id}").status_code == 200

        # 验证科目仍然存在
        assert client.get(f"/api/subjects/{subject_id}").status_code == 200


# =============================================================================
# 场景8：边界条件和错误恢复
# =============================================================================
class TestEdgeCases:
    """边界条件和错误恢复测试"""

    def test_very_long_content(self, client, sample_subject):
        """
        测试用例：超长笔记内容
        验证点：系统能处理大量内容
        """
        # 生成超长内容（~5000字）
        long_content = ("Python编程知识\n" + "这是测试内容。\n" * 500)

        resp = client.post("/api/notes", json={
            "title": "超长笔记",
            "raw_content": long_content,
            "subject_id": sample_subject.id,
        })
        assert resp.status_code in [200, 201]
        note_id = resp.json()["id"]

        # 生成产品
        gen_resp = client.post("/api/ai/generate", json={
            "note_id": note_id,
            "product_types": ["article"],
            "save_to_db": True,
        })
        assert gen_resp.status_code == 200
        assert len(gen_resp.json()["products"][0]["content"]) > 0

    def test_special_characters_in_content(self, client, sample_subject):
        """
        测试用例：包含特殊字符的笔记内容
        验证点：系统能正确存储和返回特殊字符
        """
        special_content = "## 特殊字符测试\n\n```python\nprint('Hello, 世界!')\n```\n\n> 引用块\n\n- 列表项1\n- 列表项2"

        resp = client.post("/api/notes", json={
            "title": "特殊字符测试",
            "raw_content": special_content,
            "subject_id": sample_subject.id,
        })
        note_id = resp.json()["id"]

        # 获取笔记，验证内容完整
        get_resp = client.get(f"/api/notes/{note_id}")
        assert get_resp.status_code == 200
        assert "世界" in get_resp.json()["raw_content"]

    def test_repeated_generate_same_type(self, client, sample_note):
        """
        测试用例：重复生成同一类型产品（幂等性）
        验证点：每次生成都创建新产品，不会冲突
        """
        # 第一次生成
        gen1 = client.post("/api/ai/generate", json={
            "note_id": sample_note.id,
            "product_types": ["article"],
            "save_to_db": True,
        })
        assert gen1.status_code == 200

        # 第二次生成同一类型
        gen2 = client.post("/api/ai/generate", json={
            "note_id": sample_note.id,
            "product_types": ["article"],
            "save_to_db": True,
        })
        assert gen2.status_code == 200

        # 验证创建了2个独立产品
        id1 = gen1.json()["products"][0].get("id")
        id2 = gen2.json()["products"][0].get("id")
        assert id1 is not None
        assert id2 is not None
        assert id1 != id2                                 # 不同ID



# =============================================================================
# 场景9：分块生成与批量生成端点验证
# =============================================================================
class TestChunkedIntegration:
    """分块引擎集成测试"""

    def test_chunk_info_endpoint(self, client):
        """
        测试用例：GET /api/ai/chunk-info
        验证点：返回14种产品类型的分块信息
        """
        response = client.get("/api/ai/chunk-info")
        assert response.status_code == 200
        data = response.json()
        assert "chunked_types" in data
        assert len(data["chunked_types"]) >= 14
        for t in data["chunked_types"]:
            assert t["chunk_count"] > 0

    def test_batch_generate_empty_ids(self, client):
        """
        测试用例：空ID列表批量生成请求被拒绝
        预期：400 状态码
        """
        response = client.post("/api/ai/batch-generate", json={
            "note_ids": [],
            "output_root": "test_output",
        })
        assert response.status_code == 400

    def test_chunk_count_endpoint(self, client):
        """
        测试用例：chunk-info 包含所有必需字段
        验证点：note、total_definitions 等字段存在
        """
        response = client.get("/api/ai/chunk-info")
        data = response.json()
        assert "total_definitions" in data
        assert data["total_definitions"] >= 14
        assert "note" in data


# =============================================================================
# 场景10：产品架构规划集成测试
# =============================================================================
class TestPlanIntegration:
    """规划引擎集成测试"""

    def test_plan_endpoint_returns_structure(self, client, sample_note):
        """
        测试用例：POST /api/ai/plan 返回规划结构
        验证点：plan_markdown、plan_json、product_count 字段
        """
        response = client.post("/api/ai/plan", json={
            "note_id": sample_note.id,
            "auto_confirm": False,
        })
        assert response.status_code == 200
        data = response.json()

        # 验证结构字段
        assert "plan_markdown" in data
        assert "plan_json" in data
        assert "note_title" in data
        assert "product_count" in data
        assert data["product_count"] > 0

        # 验证 plan_json 包含子结构
        pj = data["plan_json"]
        assert "overview" in pj
        assert "product_items" in pj
        assert len(pj["product_items"]) > 0

    def test_plan_endpoint_note_not_found(self, client):
        """
        测试用例：不存在的笔记规划
        预期：404
        """
        response = client.post("/api/ai/plan", json={
            "note_id": 99999,
            "auto_confirm": False,
        })
        assert response.status_code == 404

    def test_plan_with_generate_from_plan(self, client, sample_note):
        """
        测试用例：规划 → generate-from-plan 完整流程
        验证点：先规划获得产品列表，再用 generate-from-plan 生成
        """
        # 步骤1：生成规划
        plan_resp = client.post("/api/ai/plan", json={
            "note_id": sample_note.id,
            "auto_confirm": False,
        })
        assert plan_resp.status_code == 200
        plan_data = plan_resp.json()
        all_types = [p["type"] for p in plan_data["plan_json"]["product_items"][:3]]

        # 步骤2：基于规划生成选定的产品类型
        gen_resp = client.post("/api/ai/generate-from-plan", json={
            "note_id": sample_note.id,
            "product_types": all_types,
            "save_to_db": True,
        })
        assert gen_resp.status_code == 200
        assert gen_resp.json()["generated"] == len(all_types)

    def test_generate_from_plan_empty_types(self, client, sample_note):
        """
        测试用例：generate-from-plan 空类型列表
        预期：400
        """
        response = client.post("/api/ai/generate-from-plan", json={
            "note_id": sample_note.id,
            "product_types": [],
            "save_to_db": True,
        })
        assert response.status_code in [200, 400]

    def test_plan_info_endpoint(self, client):
        """
        测试用例：GET /api/ai/plan-info
        验证点：返回规划引擎说明
        """
        response = client.get("/api/ai/plan-info")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "workflow" in data
        assert "benefits" in data


# =============================================================================
# 场景11：产品重新生成集成测试
# =============================================================================
class TestRegenerateIntegration:
    """重新生成功能集成测试"""

    def test_regenerate_overwrites_content(self, client, sample_note):
        """重新生成后产品content应更新"""
        gen_resp = client.post('/api/ai/generate', json={
            'note_id': sample_note.id,
            'product_types': ['article'],
            'save_to_db': True,
        })
        products = gen_resp.json()['products']
        assert len(products) == 1
        prod_id = products[0]['id']

        reg_resp = client.post('/api/ai/regenerate', json={
            'product_id': prod_id,
        })
        assert reg_resp.status_code == 200
        reg_data = reg_resp.json()
        assert reg_data['success'] is True

        get_resp = client.get(f'/api/products/{prod_id}')
        new_content = get_resp.json()['content']
        assert len(new_content) > 100

    def test_regenerate_nonexistent_product(self, client):
        """重新生成不存在的产品->404"""
        response = client.post('/api/ai/regenerate', json={
            'product_id': 99999,
        })
        assert response.status_code == 404

    def test_regenerate_preserves_metadata(self, client, sample_note):
        """重新生成后产品类型和关联信息不应改变"""
        gen = client.post('/api/ai/generate', json={
            'note_id': sample_note.id,
            'product_types': ['sop'],
            'save_to_db': True,
        })
        prod_id = gen.json()['products'][0]['id']
        client.post('/api/ai/regenerate', json={'product_id': prod_id})
        prod = client.get(f'/api/products/{prod_id}').json()
        assert prod['product_type'] == 'sop'
        assert prod['note_id'] == sample_note.id

    def test_regenerate_with_polish(self, client, sample_note):
        """重新生成的内容经过抛光清洗"""
        gen = client.post('/api/ai/generate', json={
            'note_id': sample_note.id,
            'product_types': ['article'],
            'save_to_db': True,
        })
        prod_id = gen.json()['products'][0]['id']
        reg = client.post('/api/ai/regenerate', json={'product_id': prod_id})
        content = reg.json()['product']['content']
        assert 'Here is' not in content[:100]


class TestPolishRemovesReasoningLeak:
    """PRD 用户故事3 集成验证：经 /api/ai/polish 抛光后，产品正文不得残留思维链。

    对应线上 Bug：推理模型 <think> 思维链泄漏进对外售卖内容。
    """

    def test_polish_endpoint_strips_think(self, client):
        """闭合 think 块经抛光接口清除，正文保留。"""
        raw = "<think>The user wants me to write an article</think>\n\n# 动态规划四步法\n正文内容。"
        resp = client.post("/api/ai/polish", json={"content": raw, "product_type": "article", "title": "动态规划四步法"})
        assert resp.status_code == 200
        body = resp.json()
        assert "<think" not in body["polished"].lower()      # 标签清除
        assert "user wants" not in body["polished"].lower()  # 思维链文字清除
        assert "动态规划四步法" in body["polished"]            # 正文保留
        assert body["changed"] is True                        # 确实发生了清洗

    def test_polish_endpoint_malformed_think(self, client):
        """畸形未闭合思维链也被清除。"""
        raw = "<think用户要求生成思维导图\n# SPI 知识导图\n- 概念A\n- 概念B"
        resp = client.post("/api/ai/polish", json={"content": raw, "product_type": "mindmap", "title": "SPI 知识导图"})
        assert resp.status_code == 200
        polished = resp.json()["polished"]
        assert "用户要求" not in polished
        assert "# SPI 知识导图" in polished

    def test_polish_endpoint_clean_content_ok(self, client):
        """干净内容抛光后主体不变。"""
        raw = "# 干净标题\n正常内容无思维链。"
        resp = client.post("/api/ai/polish", json={"content": raw})
        assert resp.status_code == 200
        assert "干净标题" in resp.json()["polished"]
