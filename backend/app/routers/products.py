# 🔍 [语法] typing.Optional
# 🔍 [作用] 可选参数类型
from typing import Optional

# 🔍 [语法] FastAPI 导入
from fastapi import APIRouter, Depends, HTTPException

# 🔍 [语法] Pydantic BaseModel
from pydantic import BaseModel

# 🔍 [语法] 相对导入
from ..auth import get_current_user
from ..cloud_db import table


# 🔍 [语法] APIRouter 实例化
# 🔍 [作用] 产品路由：URL 前缀 /api/products
router = APIRouter(prefix="/api/products", tags=["products"])


# 🔍 [语法] Pydantic BaseModel
# 🔍 [作用] 创建产品请求体
class ProductCreate(BaseModel):
    # 🔍 [语法] str 必填
    # 🔍 [作用] 产品标题
    title: str

    # 🔍 [语法] str 必填
    # 🔍 [作用] 产品类型（13 种之一）
    product_type: str

    # 🔍 [语法] str 默认空
    # 🔍 [作用] Markdown 内容
    content: str = ""

    # 🔍 [语法] int 必填
    # 🔍 [作用] 所属科目 ID
    subject_id: int

    # 🔍 [语法] Optional[int]
    # 🔍 [作用] 源笔记 ID（可空：产品可独立存在）
    note_id: Optional[int] = None

    # 🔍 [语法] float 默认 0
    # 🔍 [作用] AI 建议售价
    price_suggestion: float = 0

    # 🔍 [语法] list 默认空
    # 🔍 [作用] 推荐售卖平台
    platform_suggestion: list = []

    # 🔍 [语法] list 默认空
    # 🔍 [作用] 关键词
    keywords: list = []

    # 🔍 [语法] str 默认空
    # 🔍 [作用] 预估收益范围描述
    estimated_value: str = ""

    # 🔍 [语法] str 默认 markdown
    # 🔍 [作用] 导出格式
    export_format: str = "markdown"

    # 🔍 [语法] str 默认 draft
    # 🔍 [作用] 状态（draft / published / archived）
    status: str = "draft"


# 🔍 [语法] BaseModel
# 🔍 [作用] 更新产品请求体
class ProductUpdate(BaseModel):
    # 🔍 [语法] 所有字段 Optional
    # 🔍 [作用] PATCH 语义
    title: str | None = None
    content: str | None = None
    price_suggestion: float | None = None
    platform_suggestion: list | None = None
    keywords: list | None = None
    estimated_value: str | None = None
    status: str | None = None


# 🔍 [语法] @router.get + 多查询参数
# 🔍 [作用] GET /api/products 列表（多维过滤）
@router.get("")
def list_products(
    # 🔍 [语法] 4 个 Optional 参数
    # 🔍 [作用] 支持 4 维过滤
    subject_id: Optional[int] = None,
    note_id: Optional[int] = None,
    product_type: Optional[str] = None,
    status: Optional[str] = None,
    task_id: Optional[int] = None,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] 双模式数据访问
    # 🔍 [作用] 把所有过滤参数传给 table()
    items = table("products", user).list({
        "subject_id": subject_id,
        "note_id": note_id,
        "product_type": product_type,
        "status": status,
    })
    # 🔍 [作用] task_id 存储在 products.generation_meta 里，SQL 不能直接过滤，
    #          所以查全量后在 Python 端二次过滤；任务页跳转（?taskId=N）依赖此链路。
    if task_id is not None:
        items = [item for item in items if (item.get("generation_meta") or {}).get("task_id") == task_id]
    return items


# 🔍 [语法] @router.post
# 🔍 [作用] POST /api/products 创建产品
@router.post("")
def create_product(
    data: ProductCreate,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] 外键校验
    # 🔍 [作用] 校验科目存在
    if not table("subjects", user).get(data.subject_id):
        raise HTTPException(status_code=404, detail="科目不存在")

    # 🔍 [语法] 条件外键校验
    # 🔍 [作用] 如果提供了 note_id 则必须存在
    if data.note_id and not table("notes", user).get(data.note_id):
        raise HTTPException(status_code=404, detail="笔记不存在")

    # 🔍 [语法] data.model_dump()
    # 🔍 [作用] Pydantic v2 转字典
    return table("products", user).create(data.model_dump())


# 🔍 [语法] @router.get + path
# 🔍 [作用] GET /api/products/{product_id}
@router.get("/{product_id}")
def get_product(
    product_id: int,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] 单条查询
    # 🔍 [作用] 返回产品详情
    product = table("products", user).get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return product


# 🔍 [语法] @router.put
# 🔍 [作用] PUT /api/products/{product_id}
@router.put("/{product_id}")
def update_product(
    product_id: int,
    data: ProductUpdate,
    user: dict = Depends(get_current_user),
):
    # 🔍 [语法] exclude_none=True
    # 🔍 [作用] 部分更新（只更新非空字段）
    product = table("products", user).update(product_id, data.model_dump(exclude_none=True))
    if not product:
        raise HTTPException(status_code=404, detail="产品不存在")
    return product


# 🔍 [语法] @router.delete
# 🔍 [作用] DELETE /api/products/{product_id}
# 🔍 [陷阱] ⚠️ 当前是硬删除（不可恢复）
@router.delete("/{product_id}")
def delete_product(product_id: int, user: dict = Depends(get_current_user)):
    # 🔍 [语法] 获取表实例
    products = table("products", user)
    if not products.get(product_id):
        raise HTTPException(status_code=404, detail="产品不存在")
    products.delete(product_id)
    return {"ok": True}
