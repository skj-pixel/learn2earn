# 🔍 [语法] 模块级 docstring（占位）
# 🔍 [作用] 标记模块用途——AI 产品生成核心路由（11 个端点）
# 🔍 [陷阱] 占位 TODO 应人工补全
"""
把学习过程变成赚钱过程的app/backend/app/routers/ai.py 模块

模块用途: TODO 自动扫描生成的占位说明,需要人工补全。
"""
# =============================================================================
# routers/ai.py - AI 产品生成 API 路由
# =============================================================================
# 核心接口：
#   GET    /api/ai/product-types      - 产品类型列表
#   POST   /api/ai/analyze            - 分析笔记
#   POST   /api/ai/generate           - 生成产品
#   POST   /api/ai/generate-all       - 一键生成
#   GET    /api/ai/suggest/{note_id}  - 推荐产品
#   POST   /api/ai/batch-generate      - 批量生成
#   POST   /api/ai/plan               - 架构规划
#   POST   /api/ai/generate-from-plan - 从规划生成
#   POST   /api/ai/fast-generate      - 极速生成
#   POST   /api/ai/regenerate         - 重新生成
#   POST   /api/ai/polish              - 内容抛光
#   POST   /api/ai/quality/*          - 质量增强
# =============================================================================

# 🔍 [语法] FastAPI 核心导入
from fastapi import APIRouter, Depends, HTTPException

# 🔍 [语法] SQLAlchemy Session
from sqlalchemy.orm import Session

# 🔍 [语法] typing
from typing import Optional

# 🔍 [语法] Pydantic
from pydantic import BaseModel

# 🔍 [语法] 相对导入
from ..database import get_db
from ..models import Note, Subject, Product
from ..auth import get_current_user
from ..cloud_db import table

# 🔍 [语法] 核心 AI 引擎
# 🔍 [作用] 整个应用最重要的 AI 引擎
from ..services.product_generator import product_generator, PRODUCT_TYPES
from ..services.agentic_product_generator import AgenticProductGenerator
from ..services.llm_service import get_llm_service, reload_llm_service
from ..services.strategy_compat import list_strategies


# --------------- 路由器 ---------------
router = APIRouter(prefix="/api/ai", tags=["ai"])


# 🔍 [语法] 私有辅助函数
# 🔍 [作用] 加载笔记上下文（含科目名 + 原始内容）
# 🔍 [关联] 多个端点复用此函数
def _load_note_context(note_id: int, user: dict) -> tuple[dict, dict | None, str]:
    # 🔍 [语法] tuple 返回
    # 🔍 [作用] 返回 (note, subject, raw_content) 三元组
    note = table("notes", user).get(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    # 🔍 [语法] 二次查询
    # 🔍 [作用] 查科目名（用于 AI prompt）
    subject = table("subjects", user).get(note["subject_id"])

    # 🔍 [语法] or 链式
    # 🔍 [作用] 优先 raw_content，回退 content
    raw_content = note.get("raw_content") or note.get("content") or ""

    # 🔍 [语法] strip() 校验
    # 🔍 [作用] 内容为空时 400 错误
    if not raw_content.strip():
        raise HTTPException(status_code=400, detail="笔记内容为空，无法生成产品")

    return note, subject, raw_content


# =============================================================================
# Pydantic 请求模型
# =============================================================================

# 🔍 [语法] BaseModel
# 🔍 [作用] 按指定类型生成产品请求体
class GenerateRequest(BaseModel):
    # 🔍 [语法] int 必填
    # 🔍 [作用] 源笔记 ID
    note_id: int

    # 🔍 [语法] list[str] 必填
    # 🔍 [作用] 要生成的产品类型列表
    # 🔍 [示例] ["article", "sop", "mindmap"]
    product_types: list[str]

    # 🔍 [语法] bool 默认 True
    # 🔍 [作用] 是否保存到数据库（False 用于预览）
    save_to_db: bool = True

    # 🔍 [语法] bool 默认 False
    # 🔍 [作用] 是否覆盖同类型已有产品（重新生成）
    regenerate: bool = False


# 🔍 [语法] BaseModel
# 🔍 [作用] 一键生成请求体
class GenerateAllRequest(BaseModel):
    note_id: int
    save_to_db: bool = True


# 🔍 [语法] BaseModel
# 🔍 [作用] 内容分析请求体
class AnalyzeRequest(BaseModel):
    content: str
    subject_name: str = ""


# =============================================================================
# API 端点
# =============================================================================

# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/ai/product-types
@router.get("/product-types")
def get_product_types():
    """获取所有支持的知识付费产品类型"""
    # 🔍 [语法] dict comprehension
    # 🔍 [作用] 从 PRODUCT_TYPES 全局字典提取展示信息
    return [
        {
            "type": key,
            "name": info["name"],
            "icon": info["icon"],
            "price_range": info["price_range"],
            "platforms": info["platforms"],
        }
        for key, info in PRODUCT_TYPES.items()
    ]


# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/ai/strategies 暴露三轴策略登记（前端发现可选算法/技术）
@router.get("/strategies")
def get_strategies(user: dict = Depends(get_current_user)):
    """获取生成算法 / 质量技术登记（skill 由用户安装，不在此静态列出）"""
    return list_strategies()


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/ai/analyze 分析笔记
@router.post("/analyze")
def analyze_content(data: AnalyzeRequest):
    """分析学习内容的元信息和智能推荐"""
    if not data.content.strip():
        return {"analysis": {"error": "内容为空，无法分析"}, "suggestions": []}

    # 🔍 [语法] product_generator.analyze_content
    # 🔍 [作用] 调用 AI 引擎分析（字数/难度/关键词）
    analysis = product_generator.analyze_content(data.content, data.subject_name)
    # 🔍 [语法] suggest_products
    # 🔍 [作用] 智能推荐适合的产品类型
    suggestions = product_generator.suggest_products(data.content, data.subject_name)
    # 🔍 [语法] for 循环增强
    # 🔍 [作用] 为每个推荐附加 PRODUCT_TYPES 详情
    detailed_suggestions = []
    for s in suggestions:
        info = PRODUCT_TYPES.get(s["type"], {})
        detailed_suggestions.append({
            "type": s["type"],
            "reason": s["reason"],
            "name": info.get("name", s["type"]),
            "icon": info.get("icon", "📦"),
            "price_range": info.get("price_range", (0, 0)),
            "platforms": info.get("platforms", []),
        })
    return {"analysis": analysis, "suggestions": detailed_suggestions}


# 🔍 [语法] @router.post + Depends
# 🔍 [作用] POST /api/ai/generate 生成产品（核心端点）
@router.post("/generate")
async def generate_products(data: GenerateRequest, user: dict = Depends(get_current_user)):
    """根据笔记生成指定的知识付费产品"""
    note, subject, raw_content = _load_note_context(data.note_id, user)
    subject_name = subject["name"] if subject else ""
    reload_llm_service()
    llm = get_llm_service()
    if not llm.is_ready():
        raise HTTPException(
            status_code=400,
            detail="LLM 服务未配置或未启用。请先在 LLM 设置中启用 MiniMax 或其他 OpenAI 兼容模型。",
        )

    generator = AgenticProductGenerator(llm)
    results = []
    for ptype in data.product_types:
        if ptype not in PRODUCT_TYPES:
            results.append({"type": ptype, "error": f"不支持的产品类型: {ptype}"})
            continue
        info = PRODUCT_TYPES[ptype]

        try:
            generated = await generator.generate(
                note_title=note["title"],
                note_content=raw_content,
                product_type=ptype,
                subject_name=subject_name,
            )
        except Exception as e:
            raise HTTPException(
                status_code=502,
                detail=f"LLM API 调用失败：{str(e)}。请检查 MiniMax API Key、模型名、Base URL 和网络连接。",
            )

        content = generated["content"]
        price = info["price_range"][0]

        product_data = {
            "type": ptype,
            "name": info["name"],
            "icon": info["icon"],
            "content": content,
            "price_suggestion": float(price),
            "platform_suggestion": info["platforms"][:3],
            "success": True,
            "used_llm": generated.get("used_llm", True),
            "workflow_trace": generated.get("workflow_trace", []),
            "quality_report": generated.get("quality_report", {}),
            "elapsed_ms": generated.get("elapsed_ms", 0),
        }

        if data.save_to_db:
            if data.regenerate:
                table("products", user).delete_matching({"note_id": note["id"], "product_type": ptype})

            product = table("products", user).create({
                "title": f"[{info['icon']}] {note['title']} - {info['name']}",
                "product_type": ptype,
                "content": content,
                "subject_id": note["subject_id"],
                "note_id": note["id"],
                "price_suggestion": float(price),
                "platform_suggestion": info["platforms"][:3],
                "keywords": [note["title"]] + (note.get("tags") or []),
                "status": "draft",
            })
            product_data["id"] = product["id"]

        results.append(product_data)

    return {
        "note_id": data.note_id,
        "note_title": note["title"],
        "generated": len(results),
        "products": results,
    }


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/ai/generate-all 一键生成全部
@router.post("/generate-all")
async def generate_all_products(data: GenerateAllRequest, user: dict = Depends(get_current_user)):
    """一键生成所有 AI 推荐的知识付费产品"""
    note, subject, raw_content = _load_note_context(data.note_id, user)

    # 🔍 [语法] 复用 recommend
    # 🔍 [作用] AI 推荐 → 提取类型 → 复用 generate_products
    suggestions = product_generator.suggest_products(raw_content, subject["name"] if subject else "")
    suggested_types = [s["type"] for s in suggestions]

    # 🔍 [语法] 内部请求复用
    # 🔍 [作用] 调 generate_products 端点
    req = GenerateRequest(
        note_id=data.note_id,
        product_types=suggested_types,
        save_to_db=data.save_to_db,
    )
    return await generate_products(req, user)


# 🔍 [语法] @router.get + path
# 🔍 [作用] GET /api/ai/suggest/{note_id}
@router.get("/suggest/{note_id}")
def suggest_for_note(note_id: int, user: dict = Depends(get_current_user)):
    """为指定的笔记智能推荐适合的产品类型"""
    note, subject, raw_content = _load_note_context(note_id, user)
    subject_name = subject["name"] if subject else ""
    analysis = product_generator.analyze_content(raw_content, subject_name)
    suggestions = product_generator.suggest_products(raw_content, subject_name)
    detailed = []
    for s in suggestions:
        info = PRODUCT_TYPES.get(s["type"], {})
        detailed.append({
            "type": s["type"], "reason": s["reason"],
            "name": info.get("name", s["type"]), "icon": info.get("icon", "📦"),
            "price_range": info.get("price_range", (0, 0)),
            "platforms": info.get("platforms", []),
        })
    return {"note_id": note_id, "note_title": note["title"], "analysis": analysis, "suggestions": detailed}


# =============================================================================
# 批量生成端点
# =============================================================================

# 🔍 [语法] BaseModel
# 🔍 [作用] 批量生成请求
class BatchGenerateRequest(BaseModel):
    note_ids: list[int]
    product_types: Optional[list[str]] = None
    output_root: str = "output"


# 🔍 [语法] async + Depends(get_db)
# 🔍 [作用] POST /api/ai/batch-generate
@router.post("/batch-generate")
async def batch_generate_products(
    data: BatchGenerateRequest,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """批量并行生成多篇笔记的知识付费产品"""
    # 🔍 [语法] 早返回校验
    if not data.note_ids:
        raise HTTPException(status_code=400, detail="笔记 ID 列表不能为空")

    # 🔍 [语法] 局部 import
    from ..services.batch_generator import BatchGenerator
    from ..services.llm_service import LLMService, reload_llm_service, get_llm_service

    # 🔍 [语法] reload + get
    # 🔍 [作用] 确保使用最新配置
    reload_llm_service()
    llm = get_llm_service()

    # 🔍 [语法] is_ready 检查
    if not llm.is_ready():
        raise HTTPException(status_code=400, detail="LLM 服务未配置或未启用。批量生成需要配置 LLM API。")

    # 🔍 [语法] BatchGenerator 构造
    output_root = data.output_root
    if output_root and (".." in output_root.replace("\\", "/").split("/") or output_root.startswith(("/", "\\"))):
        raise HTTPException(status_code=400, detail="输出目录必须位于项目内，不能使用绝对路径或上级目录")
    batch_gen = BatchGenerator(output_root=output_root, llm_service=llm, user_id=user["id"])

    try:
        # 🔍 [语法] await generate_batch
        # 🔍 [作用] 异步批量执行
        report = await batch_gen.generate_batch(
            note_ids=data.note_ids, db_session=db, product_types=data.product_types,
        )
        return report
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/ai/chunk-info
@router.get("/chunk-info")
def get_chunk_info():
    """获取所有产品类型的分块信息（用于前端展示生成预估）"""
    from ..services.chunked_generator import ChunkedGenerator
    chunked_types = ChunkedGenerator.list_supported_types()
    return {
        "chunked_types": chunked_types,
        "total_definitions": len(chunked_types),
        "note": "采用分块生成后，每种产品的质量显著提升，但耗时增加。建议使用批量并行模式。",
    }


# =============================================================================
# 产品架构规划端点
# =============================================================================

# 🔍 [语法] BaseModel
# 🔍 [作用] 规划请求
class PlanRequest(BaseModel):
    note_id: int
    auto_confirm: bool = False


# 🔍 [语法] async + Depends
# 🔍 [作用] POST /api/ai/plan
@router.post("/plan")
async def generate_plan(data: PlanRequest, user: dict = Depends(get_current_user)):
    """产品架构规划（Blueprint）"""
    note, subject, raw_content = _load_note_context(data.note_id, user)
    subject_name = subject["name"] if subject else ""
    # 🔍 [语法] 推荐 + 分析
    suggestions = product_generator.suggest_products(raw_content, subject_name)
    analysis = product_generator.analyze_content(raw_content, subject_name)

    # 🔍 [语法] 计算总收入
    # 🔍 [作用] 累加所有推荐产品价格
    product_items = []
    total_revenue = 0
    for idx, suggestion in enumerate(suggestions, 1):
        ptype = suggestion["type"]
        info = PRODUCT_TYPES.get(ptype, {})
        price = float((info.get("price_range") or (0, 0))[0])
        total_revenue += price
        product_items.append({
            "type": ptype, "icon": info.get("icon", "📦"),
            "suggested_title": f"{note['title']} - {info.get('name', ptype)}",
            "reason": suggestion.get("reason", "适合从当前笔记转化为轻量知识产品"),
            "price_suggestion": price, "platforms": info.get("platforms", [])[:3],
        })

    # 🔍 [语法] 构造 JSON
    # 🔍 [作用] 规划概览
    plan_json = {
        "overview": {
            "difficulty": analysis.get("difficulty", "入门到进阶"),
            "unique_value": f"围绕「{note['title']}」沉淀可复用的知识产品组合。",
            "total_potential_revenue": total_revenue,
        },
        "product_items": product_items,
    }

    # 🔍 [语法] 构造 Markdown
    # 🔍 [作用] 人类可读的规划文档
    plan_markdown = "\n".join(
        ["# 知识付费产品蓝图", "", f"源笔记：{note['title']}", ""]
        + [f"- {item['icon']} {item['suggested_title']}：{item['reason']}" for item in product_items]
    )

    # 🔍 [语法] 构造响应
    result = {
        "plan_markdown": plan_markdown, "plan_json": plan_json,
        "note_title": note["title"], "note_id": note["id"],
        "product_count": len(product_items), "total_revenue": total_revenue,
        # 🔍 [语法] 估算时间
        # 🔍 [作用] 每产品 2 分钟
        "timeline": {"estimated_minutes": max(1, len(product_items) * 2)},
    }

    # 🔍 [语法] 自动确认模式
    # 🔍 [作用] auto_confirm=True 直接生成
    if data.auto_confirm and product_items:
        # 🔍 [语法] 内部请求复用
        gen_req = GenerateRequest(
            note_id=data.note_id,
            product_types=[item["type"] for item in product_items],
            save_to_db=True,
        )
        gen_result = await generate_products(gen_req, user)
        result["auto_generated"] = True
        result["generation_result"] = gen_result
        result["message"] = f"规划完成并已生成 {gen_result['generated']} 个产品"
    return result


# 🔍 [语法] BaseModel
# 🔍 [作用] 从规划生成的请求
class GenerateFromPlanRequest(BaseModel):
    note_id: int
    product_types: list[str]
    save_to_db: bool = True


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/ai/generate-from-plan
@router.post("/generate-from-plan")
async def generate_from_plan(data: GenerateFromPlanRequest, user: dict = Depends(get_current_user)):
    """确认规划后，正式生成选定的知识付费产品"""
    # 🔍 [语法] 内部请求复用
    # 🔍 [作用] 复用 generate_products 逻辑
    generate_req = GenerateRequest(
        note_id=data.note_id,
        product_types=data.product_types,
        save_to_db=data.save_to_db,
    )
    return await generate_products(generate_req, user)


# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/ai/plan-info
@router.get("/plan-info")
def get_plan_info():
    """获取规划引擎使用说明（供前端展示）"""
    return {
        "name": "知识付费产品架构规划引擎",
        "description": "在正式生成知识付费产品之前，先产出一份详细的产品架构方案",
        "workflow": [
            "1. 记完学习笔记", "2. 点击「生成规划」→ 获得产品架构方案",
            "3. 审核方案：调整优先级、砍掉不想要的产品",
            "4. 点击「确认并生成」→ 正式生成所有选定产品",
        ],
        "benefits": [
            "避免盲目生成不适合的产品（节省 token 和时间）",
            "确保多产品内容互补而非重复", "统一定价策略和分发渠道",
            "生成前即可看到完整产出全景图",
        ],
    }


# =============================================================================
# 快速生成端点
# =============================================================================

# 🔍 [语法] BaseModel
# 🔍 [作用] 快速生成请求
class FastGenerateRequest(BaseModel):
    note_id: int
    save_to_db: bool = True


# 🔍 [语法] async + Depends
# 🔍 [作用] POST /api/ai/fast-generate
@router.post("/fast-generate")
async def fast_generate(data: FastGenerateRequest, user: dict = Depends(get_current_user)):
    """快速模式：规划+全部产品生成 → 单次LLM调用完成"""
    note, subject, raw_content = _load_note_context(data.note_id, user)
    suggestions = product_generator.suggest_products(raw_content, subject["name"] if subject else "")
    product_types = [item["type"] for item in suggestions]

    # 🔍 [语法] 复用 generate_products
    gen_result = await generate_products(GenerateRequest(note_id=data.note_id, product_types=product_types, save_to_db=data.save_to_db), user)

    return {
        "success": True, "mode": "fast-compatible",
        "product_count": gen_result["generated"],
        "products": gen_result["products"],
        "plan": {
            "product_items": [
                {"type": item["type"], "suggested_title": f"{note['title']} - {PRODUCT_TYPES.get(item['type'], {}).get('name', item['type'])}"}
                for item in suggestions
            ],
            "total_revenue": sum(float(p.get("price_suggestion") or 0) for p in gen_result["products"]),
        },
        "total_time_ms": 0, "token_saved_pct": 0,
    }


# =============================================================================
# 重新生成端点
# =============================================================================

# 🔍 [语法] BaseModel
# 🔍 [作用] 重新生成单个产品请求
class RegenerateRequest(BaseModel):
    product_id: int


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/ai/regenerate
@router.post("/regenerate")
async def regenerate_product(data: RegenerateRequest, user: dict = Depends(get_current_user)):
    """对某个已生成的产品进行重新生成（覆盖原有内容）"""
    # 🔍 [语法] 查询产品
    product = table("products", user).get(data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")

    # 🔍 [语法] 查找源笔记
    note = table("notes", user).get(product["note_id"])
    if not note:
        raise HTTPException(status_code=404, detail="源笔记不存在")

    # 🔍 [语法] or 链式
    raw_content = note.get("raw_content") or note.get("content") or ""
    if not raw_content.strip():
        raise HTTPException(status_code=400, detail="笔记内容为空")

    # 🔍 [语法] 查科目名
    subject = table("subjects", user).get(note["subject_id"])
    subject_name = subject["name"] if subject else ""

    reload_llm_service()
    llm = get_llm_service()
    if not llm.is_ready():
        raise HTTPException(
            status_code=400,
            detail="LLM 服务未配置或未启用。请先在 LLM 设置中启用 MiniMax 或其他 OpenAI 兼容模型。",
        )

    generator = AgenticProductGenerator(llm)
    try:
        generated = await generator.generate(
            note_title=note["title"],
            note_content=raw_content,
            product_type=product["product_type"],
            subject_name=subject_name,
        )
        new_content = generated["content"]
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM API 调用失败：{str(e)}。请检查 LLM 配置和网络连接。")

    # 🔍 [语法] update 覆盖
    product = table("products", user).update(data.product_id, {"content": new_content})

    return {
        "success": True,
        "message": "产品已通过 LLM Agent 工作流重新生成",
        "product": product,
        "regenerated": True,
        "used_llm": generated.get("used_llm", True),
        "workflow_trace": generated.get("workflow_trace", []),
        "quality_report": generated.get("quality_report", {}),
    }


# =============================================================================
# 内容抛光端点
# =============================================================================

# 🔍 [语法] BaseModel
# 🔍 [作用] 抛光请求
class PolishRequest(BaseModel):
    content: str
    product_type: str = ""
    title: str = ""


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/ai/polish
@router.post("/polish")
def polish_content(data: PolishRequest):
    """对已生成的内容进行抛光（纯规则引擎，不调用LLM）"""
    from ..services.content_polisher import ContentPolisher

    polisher = ContentPolisher()
    polished, stats = polisher.polish(data.content, data.product_type, data.title)
    issues = polisher.validate(polished)

    return {
        "polished": polished,
        "stats": stats,
        "issues": issues,
        "changed": polished != data.content,
    }


# =============================================================================
# 质量增强端点
# =============================================================================

# 🔍 [语法] @router.get
# 🔍 [作用] GET /api/ai/quality/techniques
@router.get("/quality/techniques")
def get_quality_techniques():
    """获取全部质量提升技巧列表"""
    from ..services.quality_enhancer import list_all_techniques
    return list_all_techniques()


# 🔍 [语法] BaseModel
# 🔍 [作用] 质量增强请求
class EnhanceRequest(BaseModel):
    content: str
    product_type: str
    note_title: str = ""
    subject_name: str = ""
    note_content: str = ""


# 🔍 [语法] async
# 🔍 [作用] POST /api/ai/quality/enhance
@router.post("/quality/enhance")
async def enhance_quality(data: EnhanceRequest):
    """对已生成的产品内容执行全链路质量增强"""
    from ..services.quality_enhancer import QualityEnhancer
    from ..services.llm_service import reload_llm_service, get_llm_service

    reload_llm_service()
    llm = get_llm_service()

    # 🔍 [语法] 增强器构造
    # 🔍 [作用] LLM 未启用时仍可使用规则引擎
    enhancer = QualityEnhancer(llm if llm.is_ready() else None)

    # 🔍 [语法] await enhance
    # 🔍 [作用] 执行 7 步质量增强
    enhanced_content, report, enhancements = await enhancer.enhance(
        content=data.content, product_type=data.product_type,
        note_title=data.note_title, subject_name=data.subject_name,
        note_content=data.note_content,
    )

    return {
        "success": True, "enhanced_content": enhanced_content,
        "quality_report": report.to_dict(), "enhancements": enhancements,
        "changed": enhanced_content != data.content,
    }


# 🔍 [语法] async
# 🔍 [作用] POST /api/ai/quality/score
@router.post("/quality/score")
async def score_content(data: EnhanceRequest):
    """对产品内容进行多维度质量评分（不修改内容）"""
    from ..services.quality_enhancer import QualityScorer
    # 🔍 [语法] QualityScorer 规则引擎
    # 🔍 [作用] 无需 LLM 的纯规则评分
    scorer = QualityScorer()

    # 🔍 [语法] await score
    report = await scorer.score(
        content=data.content, product_type=data.product_type,
        note_title=data.note_title, subject_name=data.subject_name,
        note_content=data.note_content,
    )
    return report.to_dict()


# 🔍 [语法] @router.post 同步
# 🔍 [作用] POST /api/ai/quality/check-hallucination
@router.post("/quality/check-hallucination")
def check_hallucination(data: EnhanceRequest):
    """检查生成内容是否存在幻觉（纯规则引擎）"""
    from ..services.quality_enhancer import HallucinationChecker
    checker = HallucinationChecker()
    result = checker.check(data.content, data.note_content)
    return result
