# =============================================================================
# tests/test_models.py - 数据模型单元测试
# =============================================================================
# 测试所有 ORM 模型的：
#   1. 创建和持久化（CRUD）
#   2. to_dict() 序列化
#   3. ORM 关系（一对多、多对一）
#   4. 级联删除
#   5. 字段默认值
# =============================================================================

import pytest                              # pytest 框架
from app.models import Subject, Note, Product  # 被测试的 ORM 模型


# =============================================================================
# Subject 模型测试类
# =============================================================================
class TestSubject:
    """Subject（科目）模型的单元测试"""

    def test_create_subject(self, db_session):
        """
        测试用例：创建科目并验证字段
        验证点：所有字段值正确写入数据库
        """
        # ---- 创建 Subject 对象 ----
        subject = Subject(
            name="嵌入式开发",           # 科目名称
            icon="🔌",                   # 自定义图标
            description="STM32 + RTOS",  # 描述
            color="#10b981",             # 绿色主题
            total_hours=12.5,            # 累计学习 12.5 小时
        )
        db_session.add(subject)          # 加入数据库会话
        db_session.commit()              # 提交事务
        db_session.refresh(subject)      # 刷新以获取数据库生成的字段

        # ---- 验证字段值 ----
        assert subject.id is not None            # id 应由数据库自动生成
        assert subject.name == "嵌入式开发"       # 名称正确
        assert subject.icon == "🔌"              # 图标正确
        assert subject.description == "STM32 + RTOS"  # 描述正确
        assert subject.color == "#10b981"        # 颜色正确
        assert subject.total_hours == 12.5       # 时长正确
        assert subject.created_at is not None    # 创建时间自动填入
        assert subject.updated_at is not None    # 更新时间自动填入

    def test_subject_defaults(self, db_session):
        """
        测试用例：科目字段默认值
        验证点：未指定值时使用预先定义的默认值
        """
        # 只提供必填字段 name
        subject = Subject(name="测试科目")
        db_session.add(subject)
        db_session.commit()
        db_session.refresh(subject)

        # ---- 验证默认值 ----
        assert subject.icon == "📚"              # 默认图标：书本
        assert subject.description == ""         # 默认描述：空字符串
        assert subject.color == "#6366f1"        # 默认颜色：紫色
        assert subject.total_hours == 0          # 默认时长：0

    def test_subject_to_dict(self, db_session):
        """
        测试用例：to_dict() 序列化
        验证点：
            1. 返回 dict 类型
            2. 包含所有字段
            3. 时间字段为 ISO 格式字符串
            4. note_count 默认为 0
        """
        subject = Subject(name="数据科学")
        db_session.add(subject)
        db_session.commit()
        db_session.refresh(subject)

        d = subject.to_dict()                    # 调用序列化方法

        # ---- 验证类型和字段 ----
        assert isinstance(d, dict)               # 返回值是 dict
        assert d["id"] == subject.id             # id 匹配
        assert d["name"] == "数据科学"           # 名称匹配
        assert d["icon"] == "📚"                 # 图标匹配
        assert d["color"] == "#6366f1"           # 颜色匹配
        assert d["note_count"] == 0              # 新科目笔记数为 0
        # 时间应为 ISO 8601 格式字符串
        assert isinstance(d["created_at"], str)
        assert isinstance(d["updated_at"], str)

    def test_subject_update(self, db_session):
        """
        测试用例：更新科目字段
        验证点：字段更新后值正确变化
        """
        subject = Subject(name="原名称", total_hours=5)
        db_session.add(subject)
        db_session.commit()

        # ---- 更新字段 ----
        subject.name = "新名称"
        subject.total_hours = 10
        db_session.commit()
        db_session.refresh(subject)

        assert subject.name == "新名称"
        assert subject.total_hours == 10

    def test_delete_subject_cascades(self, db_session):
        """
        测试用例：级联删除科目 → 笔记 → 产品
        验证点：删除科目后，关联的笔记和产品也被删除
        """
        # ---- 创建科目 → 笔记 → 产品 的完整链条 ----
        subject = Subject(name="测试级联")
        db_session.add(subject)
        db_session.commit()

        note = Note(title="测试笔记", subject_id=subject.id)
        db_session.add(note)
        db_session.commit()

        product = Product(
            title="测试产品",
            product_type="article",
            subject_id=subject.id,
            note_id=note.id,
            content="产品内容",
        )
        db_session.add(product)
        db_session.commit()

        # ---- 验证创建成功 ----
        assert db_session.query(Note).count() == 1
        assert db_session.query(Product).count() == 1

        # ---- 删除科目 ----
        db_session.delete(subject)
        db_session.commit()

        # ---- 验证级联删除 ----
        assert db_session.query(Note).count() == 0     # 笔记已被删除
        assert db_session.query(Product).count() == 0   # 产品已被删除


# =============================================================================
# Note 模型测试类
# =============================================================================
class TestNote:
    """Note（笔记）模型的单元测试"""

    def test_create_note(self, db_session, sample_subject):
        """
        测试用例：创建笔记并验证
        验证点：字段值、外键关联正确
        """
        note = Note(
            title="Python装饰器",
            raw_content="装饰器是Python的重要特性...",
            subject_id=sample_subject.id,        # 外键关联到测试科目
            tags=["Python", "高级"],
            learning_stage="stage2",             # 专精期
            estimated_minutes=60,
            is_completed=False,
        )
        db_session.add(note)
        db_session.commit()
        db_session.refresh(note)

        # ---- 验证 ----
        assert note.id is not None
        assert note.title == "Python装饰器"
        assert note.raw_content == "装饰器是Python的重要特性..."
        assert note.subject_id == sample_subject.id
        assert note.tags == ["Python", "高级"]
        assert note.learning_stage == "stage2"
        assert note.estimated_minutes == 60
        assert note.is_completed is False

    def test_note_to_dict(self, db_session, sample_subject):
        """
        测试用例：Note.to_dict() 序列化
        验证点：包含 subject_name 和 product_count
        """
        note = Note(
            title="测试笔记",
            subject_id=sample_subject.id,
        )
        db_session.add(note)
        db_session.commit()
        db_session.refresh(note)

        d = note.to_dict()

        # ---- 验证 ----
        assert d["title"] == "测试笔记"
        assert d["subject_id"] == sample_subject.id
        assert d["subject_name"] == "Python编程"   # 通过 ORM 关系获取
        assert d["product_count"] == 0              # 还没有生成产品
        assert d["tags"] == []                      # JSON 字段默认值
        assert d["learning_stage"] == "stage1"      # 默认阶段

    def test_note_delete_cascades_products(self, db_session, sample_subject):
        """
        测试用例：删除笔记 → 级联删除关联的产品
        验证点：笔记删除后，关联的产品也被删除
        """
        # ---- 创建笔记 + 两个产品 ----
        note = Note(title="有产品的笔记", subject_id=sample_subject.id)
        db_session.add(note)
        db_session.commit()

        p1 = Product(title="产品1", product_type="article",
                     subject_id=sample_subject.id, note_id=note.id)
        p2 = Product(title="产品2", product_type="sop",
                     subject_id=sample_subject.id, note_id=note.id)
        db_session.add_all([p1, p2])
        db_session.commit()

        assert db_session.query(Product).count() == 2  # 确认有 2 个产品

        # ---- 删除笔记 ----
        db_session.delete(note)
        db_session.commit()

        # ---- 验证产品也被删除 ----
        assert db_session.query(Product).count() == 0


# =============================================================================
# Product 模型测试类
# =============================================================================
class TestProduct:
    """Product（知识付费产品）模型的单元测试"""

    def test_create_product(self, db_session, sample_subject, sample_note):
        """
        测试用例：创建产品并验证所有字段
        验证点：product_type、价格、平台、状态等
        """
        product = Product(
            title="Python列表推导式技术文章",
            product_type="article",              # 产品类型：技术文章
            content="# Python列表推导式\n\n## 概述\n...",
            subject_id=sample_subject.id,
            note_id=sample_note.id,
            price_suggestion=19.0,               # 建议售价 19 元
            platform_suggestion=["CSDN", "掘金", "知乎"],  # 推荐平台
            keywords=["Python", "列表推导式", "基础"],
            estimated_value="¥19-59",
            export_format="markdown",
            status="draft",                      # 初始状态：草稿
        )
        db_session.add(product)
        db_session.commit()
        db_session.refresh(product)

        # ---- 验证所有字段 ----
        assert product.id is not None
        assert product.title == "Python列表推导式技术文章"
        assert product.product_type == "article"
        assert "Python列表推导式" in product.content
        assert product.subject_id == sample_subject.id
        assert product.note_id == sample_note.id
        assert product.price_suggestion == 19.0
        assert product.platform_suggestion == ["CSDN", "掘金", "知乎"]
        assert product.keywords == ["Python", "列表推导式", "基础"]
        assert product.status == "draft"

    def test_product_to_dict(self, db_session, sample_subject):
        """
        测试用例：Product.to_dict() 序列化
        验证点：JSON 字段安全处理（None → []）
        """
        product = Product(
            title="仅有标题的产品",
            product_type="quiz",
            subject_id=sample_subject.id,
            # 不指定 price_suggestion → 默认 0
            # 不指定 platform_suggestion → 默认 []
        )
        db_session.add(product)
        db_session.commit()

        d = product.to_dict()

        assert d["title"] == "仅有标题的产品"
        assert d["product_type"] == "quiz"
        assert d["price_suggestion"] == 0         # 默认值
        assert d["platform_suggestion"] == []      # JSON None → []
        assert d["keywords"] == []                 # JSON None → []
        assert d["status"] == "draft"              # 默认状态
        assert d["export_format"] == "markdown"    # 默认导出格式

    def test_product_status_transition(self, db_session, sample_subject):
        """
        测试用例：产品状态转换：draft → published → archived
        验证点：状态可以自由更新
        """
        product = Product(
            title="状态测试",
            product_type="article",
            subject_id=sample_subject.id,
        )
        db_session.add(product)
        db_session.commit()

        # ---- 草稿 → 发布 ----
        product.status = "published"
        db_session.commit()
        db_session.refresh(product)
        assert product.status == "published"

        # ---- 发布 → 归档 ----
        product.status = "archived"
        db_session.commit()
        db_session.refresh(product)
        assert product.status == "archived"

    def test_product_without_note(self, db_session, sample_subject):
        """
        测试用例：产品不关联任何笔记（note_id=None）
        验证点：note_id 可为空
        """
        product = Product(
            title="独立产品",
            product_type="checklist",
            subject_id=sample_subject.id,
            note_id=None,                        # 明确设为 None
        )
        db_session.add(product)
        db_session.commit()

        assert product.id is not None
        assert product.note_id is None           # 没有关联笔记
