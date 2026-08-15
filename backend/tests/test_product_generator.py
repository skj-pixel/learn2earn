# =============================================================================
# tests/test_product_generator.py - AI 产品生成器单元测试
# =============================================================================
# 全面测试 ProductGenerator 核心引擎的各个功能：
#   1. analyze_content()      - 内容分析
#   2. _extract_keywords()    - 关键词提取
#   3. _segment_content()     - 内容分段
#   4. _estimate_difficulty() - 难度估算
#   5. generate_article()     - 文章生成
#   6. generate_ppt() - PPT大纲生成
#   7. generate_sop()         - SOP生成
#   8. generate_prompt_template() - 提示词生成
#   9. generate_course_outline()  - 课程大纲生成
#   10. generate_interview_qa()   - 面试题库生成
#   11. generate_code_doc()       - 源码文档生成
#   12. generate_workflow()       - 流程图生成
#   13. generate_quiz()           - 测试题生成
#   14. generate_checklist()      - 清单生成
#   15. generate_flashcard()      - 记忆卡片生成
#   16. generate_script()         - 视频脚本生成
#   17. generate_product_intro()  - 产品文案生成
#   18. generate_mindmap()        - 思维导图生成
#   19. suggest_products()        - 智能推荐
#   20. generate()                - 统一生成入口
#   21. get_product_info()        - 产品信息查询
# =============================================================================

import pytest
from app.services.product_generator import product_generator, PRODUCT_TYPES


# =============================================================================
# 测试数据
# =============================================================================

# 短内容样本（<200字）- 用于测试基础推荐
SHORT_CONTENT = """Python入门学习笔记
今天学习了变量和数据类型。
Python有int、float、str、list、dict等类型。
"""

# 中等内容样本（>200字）- 用于测试中级推荐
MEDIUM_CONTENT = """# Python函数进阶

## 装饰器
装饰器是一种设计模式，允许在不修改原函数的情况下增强其功能。

## 闭包
闭包是指内部函数可以访问外部函数的变量。

## 代码示例
```python
def my_decorator(func):
    def wrapper(*args, **kwargs):
        print("Before")
        result = func(*args, **kwargs)
        print("After")
        return result
    return wrapper

@my_decorator
def say_hello(name):
    print(f"Hello, {name}!")
    
say_hello("World")
```

## 常见错误
1. 忘记返回 wrapper 函数
2. 装饰器的参数传递问题
3. 多层装饰器的执行顺序

## 实战建议
学习装饰器的关键在于理解高阶函数和闭包的概念。
建议先掌握这些基础知识再来学习装饰器。
"""

# 长内容样本（>800字）- 用于测试高级推荐
LONG_CONTENT = """# C语言指针完全指南

## 第一章：指针基础

### 1.1 什么是指针
指针是C语言中最强大的特性之一，它存储的是另一个变量的内存地址。
理解指针是掌握C语言高级编程的关键。

### 1.2 指针的声明与初始化
```c
int *p;        // 声明一个整型指针
int a = 10;
p = &a;        // p现在存储a的地址
printf("%d", *p);  // 解引用，输出10
```

### 1.3 指针运算
指针可以进行加减运算。当我们对一个指针加1时，
它指向的是下一个同类型元素的位置。

```c
int arr[] = {1, 2, 3, 4, 5};
int *p = arr;
printf("%d", *(p + 2));  // 输出3
```

## 第二章：指针与数组

### 2.1 数组名即是地址
在C语言中，数组名本身就是一个指向数组首元素的指针。

### 2.2 指针数组与数组指针
- 指针数组：int *p[5] - 5个指针构成的数组
- 数组指针：int (*p)[5] - 指向有5个元素的数组的指针

## 第三章：指针与函数

### 3.1 函数指针
函数指针可以让我们把函数当作参数传递。

### 3.2 回调函数
通过函数指针实现回调机制。

## 第四章：动态内存分配

### 4.1 malloc与free
使用malloc分配内存，使用free释放内存。

## 第五章：常见错误与调试

### 5.1 野指针
野指针是指向非法内存地址的指针，使用它会导致程序崩溃。
初始化指针为NULL是一个良好的编程习惯。

### 5.2 内存泄漏
动态分配的内存没有被释放会导致内存泄漏。
每次malloc必须配对一个free调用。

### 5.3 段错误
访问未分配或受保护的内存区域会触发段错误（Segmentation Fault）。
使用gdb等调试工具可以快速定位问题。

## 第六章：高级主题

### 6.1 二级指针
二级指针是指向指针的指针，常用于函数中修改指针的值。
典型应用：链表操作、动态二维数组分配。

### 6.2 指针与结构体
通过指针访问结构体成员使用 -> 运算符。
这是实现链表、树等数据结构的基础。

### 6.3 void指针
void指针可以指向任何类型的数据，但不能直接解引用。
需要先强制类型转换后才能使用。

## 第七章：面试常见问题

### 7.1 指针与引用的区别
指针可以为NULL，引用必须初始化。这是面试中最常问的基础问题之一。

### 7.2 如何避免内存泄漏
使用智能指针、RAII模式、内存检测工具如Valgrind。
在C语言项目中尤其要注意动态内存的管理。

### 7.3 指针在多线程中的使用
多线程环境下使用指针需要考虑数据竞争和同步问题。

## 总结
掌握指针是C语言的核心竞争力。
面试和实际项目中指针都是重点考察内容。
学习嵌入式开发和系统编程时，指针的深入理解至关重要。
建议通过大量实战练习来巩固指针知识，并不断优化代码性能。
"""


# =============================================================================
# 测试 analyze_content() - 内容分析
# =============================================================================
class TestAnalyzeContent:
    """内容分析功能测试"""

    def test_analyze_empty_content(self):
        """
        测试用例：空内容分析
        预期：返回 error 字段
        """
        result = product_generator.analyze_content("")
        assert "error" in result
        assert result["error"] == "内容为空"

    def test_analyze_whitespace_content(self):
        """
        测试用例：纯空白内容
        预期：返回 error
        """
        result = product_generator.analyze_content("   \n  \t  ")
        assert "error" in result

    def test_analyze_short_content(self):
        """
        测试用例：分析短内容
        验证点：字数、行数、关键词、难度等元信息
        """
        result = product_generator.analyze_content(SHORT_CONTENT, "Python")

        # ---- 基本统计 ----
        assert "word_count" in result
        assert result["word_count"] > 0
        assert "line_count" in result
        assert result["line_count"] > 0

        # ---- 关键词 ----
        assert "keywords" in result
        assert isinstance(result["keywords"], list)
        assert "Python" in result["keywords"]       # 应检测到 Python

        # ---- 分段 ----
        assert "segments" in result
        assert isinstance(result["segments"], list)

        # ---- 难度 ----
        assert "difficulty" in result
        assert result["difficulty"] in ["beginner", "intermediate", "advanced"]

        # ---- 阅读时间 ----
        assert "estimated_reading_time" in result
        assert result["estimated_reading_time"] >= 1

    def test_analyze_with_subject_name(self):
        """
        测试用例：带科目名称的分析
        验证点：subject 字段正确返回
        """
        result = product_generator.analyze_content(MEDIUM_CONTENT, "Python编程")
        assert result["subject"] == "Python编程"

    def test_analyze_long_content(self):
        """
        测试用例：长内容分析
        验证点：字数 > 800，阅读时间 > 2分钟
        """
        result = product_generator.analyze_content(LONG_CONTENT)
        assert result["word_count"] > 800
        assert result["estimated_reading_time"] >= 2


# =============================================================================
# 测试 _extract_keywords() - 关键词提取
# =============================================================================
class TestExtractKeywords:
    """关键词提取功能测试"""

    def test_extract_python_keywords(self):
        """
        测试用例：Python 相关内容 → 提取到 Python、pandas 等关键词
        """
        result = product_generator.analyze_content(
            "使用Python和pandas进行数据分析", "数据分析"
        )
        keywords = result["keywords"]
        assert "Python" in keywords
        assert "pandas" in keywords                   # pandas 库

    def test_extract_embedded_keywords(self):
        """
        测试用例：嵌入式相关内容 → 提取到 STM32、嵌入式
        """
        result = product_generator.analyze_content(
            "STM32嵌入式开发实战教程", "嵌入式"
        )
        keywords = result["keywords"]
        assert "STM32" in keywords or "嵌入式" in keywords

    def test_extract_latin_term_adjacent_to_cjk(self):
        result = product_generator.analyze_content("Rust所有权与借用机制")
        assert "Rust" in result["keywords"]

    def test_extract_no_tech_keywords(self):
        """
        测试用例：无技术关键词的普通文本
        验证点：返回空列表或少量匹配
        """
        result = product_generator.analyze_content("今天天气真好，适合出去散步。")
        # 可能匹配到零个或少数关键词
        assert isinstance(result["keywords"], list)


# =============================================================================
# 测试 _segment_content() - 内容分段
# =============================================================================
class TestSegmentContent:
    """内容分段功能测试"""

    def test_segment_with_headers(self):
        """
        测试用例：包含 Markdown 标题的内容
        验证点：正确识别标题并分段
        """
        content = """# 标题一
这是第一部分的内容

# 标题二
这是第二部分的内容"""
        result = product_generator.analyze_content(content)
        segments = result["segments"]

        # 应有两段内容
        assert len(segments) >= 2

        # 验证第一段标题
        titles = [s["title"] for s in segments]
        assert "标题一" in titles or any("标题一" in t for t in titles)

    def test_segment_flat_content(self):
        """
        测试用例：无标题的平铺内容
        验证点：至少有一段
        """
        result = product_generator.analyze_content("这是没有标题的内容段落。")
        assert len(result["segments"]) >= 1


# =============================================================================
# 测试 _estimate_difficulty() - 难度估算
# =============================================================================
class TestEstimateDifficulty:
    """难度估算功能测试"""

    def test_beginner_content(self):
        """
        测试用例：入门级别的学习内容
        验证点：difficulty == "beginner"
        """
        result = product_generator.analyze_content(
            "Python入门基础教程，初学者必看，Hello World程序"
        )
        assert result["difficulty"] == "beginner"

    def test_advanced_content(self):
        """
        测试用例：高级技术内容
        验证点：difficulty == "advanced"
        """
        result = product_generator.analyze_content(
            "深入理解Python内核源码架构，性能优化底层原理"
        )
        assert result["difficulty"] == "advanced"

    def test_intermediate_content(self):
        """
        测试用例：中性内容（无明确难度提示词）
        验证点：difficulty == "intermediate"
        """
        result = product_generator.analyze_content(
            "Python中的面向对象编程，使用类和对象"
        )
        assert result["difficulty"] == "intermediate"


# =============================================================================
# 测试所有产品生成方法
# =============================================================================
class TestProductGeneration:
    """验证所有14种产品类型都能正确生成"""

    ANALYSIS = None   # 类级别缓存 analysis 结果

    @classmethod
    def get_analysis(cls):
        """获取分析结果（懒加载，只分析一次）"""
        if cls.ANALYSIS is None:
            cls.ANALYSIS = product_generator.analyze_content(MEDIUM_CONTENT, "Python")
        return cls.ANALYSIS

    def test_generate_article(self):
        """
        测试用例：生成技术文章
        验证点：包含标题、关键词、代码块、结尾
        """
        analysis = self.get_analysis()
        article = product_generator.generate_article(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "Python装饰器" in article                # 标题
        assert "##" in article                          # Markdown 二级标题
        assert "```python" in article                   # 代码块
        assert "总结" in article                        # 结尾章节
        assert len(article) > 500                       # 内容足够长

    def test_generate_ppt(self):
        """
        测试用例：生成 PPT 大纲
        验证点：包含封面、12-15页结构、变现建议
        """
        analysis = self.get_analysis()
        ppt = product_generator.generate_ppt(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "PPT大纲" in ppt
        assert "Slide 1" in ppt                         # 第一页幻灯片
        assert "封面" in ppt                            # 封面页
        assert "变现建议" in ppt                        # 变现部分

    def test_generate_sop(self):
        """
        测试用例：生成 SOP 文档
        验证点：包含文档信息、5步操作流程、检查点
        """
        analysis = self.get_analysis()
        sop = product_generator.generate_sop(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "SOP" in sop
        assert "文档信息" in sop
        assert "操作流程" in sop
        assert "检查点" in sop

    def test_generate_prompt_template(self):
        """
        测试用例：生成 AI 提示词模板
        验证点：包含5个模板、使用指南
        """
        analysis = self.get_analysis()
        prompts = product_generator.generate_prompt_template(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "提示词模板" in prompts
        assert "模板1" in prompts                       # 第1个模板
        assert "模板5" in prompts                       # 第5个模板
        assert "ChatGPT" in prompts                     # 提及使用平台

    def test_generate_course_outline(self):
        """
        测试用例：生成课程大纲
        验证点：12课时、4周结构、变现建议
        """
        analysis = self.get_analysis()
        course = product_generator.generate_course_outline(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "课程大纲" in course
        assert "第1课" in course                               # 第一课时
        assert "第12课" in course                              # 第十二课时
        assert "第一周" in course                              # 第一周
        assert "课后作业" in course                            # 作业标识

    def test_generate_interview_qa(self):
        """
        测试用例：生成面试题库
        验证点：10题、含基础/进阶/系统设计
        """
        analysis = self.get_analysis()
        qa = product_generator.generate_interview_qa(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "面试题库" in qa
        assert "基础知识题" in qa                              # 基础部分
        assert "进阶题" in qa                                  # 进阶部分
        assert "系统设计题" in qa                              # 设计题部分

    def test_generate_code_doc(self):
        """
        测试用例：生成源码文档
        验证点：API文档格式、项目结构、使用示例
        """
        analysis = self.get_analysis()
        doc = product_generator.generate_code_doc(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "源码文档" in doc
        assert "函数说明" in doc
        assert "使用示例" in doc

    def test_generate_workflow(self):
        """
        测试用例：生成工作流程图（Mermaid）
        验证点：Mermaid 语法、主流程和子流程
        """
        analysis = self.get_analysis()
        wf = product_generator.generate_workflow(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "mermaid" in wf                              # Mermaid 代码块
        assert "flowchart" in wf                            # 流程图语法
        assert "角色与职责" in wf                           # 角色表

    def test_generate_quiz(self):
        """
        测试用例：生成自测题
        验证点：15题、单选题+判断题+简答题+实践题=100分
        """
        analysis = self.get_analysis()
        quiz = product_generator.generate_quiz(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "自测题" in quiz
        assert "单选题" in quiz                             # 单选题部分
        assert "判断题" in quiz                             # 判断题部分
        assert "简答题" in quiz                             # 简答题部分
        assert "实践题" in quiz                             # 实践题部分
        assert "满分100分" in quiz                          # 总分

    def test_generate_checklist(self):
        """
        测试用例：生成行动清单
        验证点：4阶段清单、6个避坑提醒、进度追踪表
        """
        analysis = self.get_analysis()
        checklist = product_generator.generate_checklist(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "行动清单" in checklist
        assert "避坑指南" in checklist
        assert "学习前准备" in checklist
        assert "变现准备" in checklist

    def test_generate_flashcard(self):
        """
        测试用例：生成记忆卡片
        验证点：Anki格式、正面/背面配对
        """
        analysis = self.get_analysis()
        cards = product_generator.generate_flashcard(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "记忆卡片" in cards
        assert "正面" in cards                              # 卡片正面
        assert "背面" in cards                              # 卡片背面
        assert "Anki" in cards                              # Anki 兼容提示

    def test_generate_script(self):
        """
        测试用例：生成视频脚本
        验证点：3分钟结构、时间段标注、画面+BGM+字幕
        """
        analysis = self.get_analysis()
        script = product_generator.generate_script(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "视频脚本" in script
        assert "0:00" in script                             # 开场时间
        assert "3:00" in script                             # 结束时间
        assert "BGM" in script                              # 背景音乐标注

    def test_generate_product_intro(self):
        """
        测试用例：生成产品分销文案
        验证点：3个版本（朋友圈/公众号/知乎）
        """
        analysis = self.get_analysis()
        intro = product_generator.generate_product_intro(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "产品介绍文案" in intro
        assert "版本A" in intro                             # 短文版本
        assert "版本B" in intro                             # 公众号版本
        assert "版本C" in intro                             # 知乎版本

    def test_generate_mindmap(self):
        """
        测试用例：生成思维导图
        验证点：5大分支、层级结构
        """
        analysis = self.get_analysis()
        mindmap = product_generator.generate_mindmap(
            "Python装饰器", MEDIUM_CONTENT, analysis
        )
        assert "思维导图" in mindmap
        assert "核心概念" in mindmap                        # 第1分支
        assert "关键技能" in mindmap                        # 第2分支
        assert "变现方式" in mindmap                        # 第4分支

    def test_all_product_types_in_generators(self):
        """
        测试用例：确保 PRODUCT_TYPES 和 GENERATORS 映射一致
        验证点：所有产品类型都有对应生成方法
        """
        for ptype in PRODUCT_TYPES:
            assert ptype in product_generator.GENERATORS, \
                f"产品类型 {ptype} 缺少生成方法映射"


# =============================================================================
# 测试 suggest_products() - 智能推荐
# =============================================================================
class TestSuggestProducts:
    """智能推荐功能测试"""

    def test_suggest_short_content(self):
        """
        测试用例：短内容推荐
        验证点：
            - 推荐数 ≤ 8
            - 必须包含基础产品（article, mindmap, checklist）
        """
        suggestions = product_generator.suggest_products(SHORT_CONTENT, "Python")
        assert len(suggestions) <= 8                      # 最多8个

        types = [s["type"] for s in suggestions]
        assert "article" in types                         # 必有文章
        assert "mindmap" in types                         # 必有思维导图
        assert "checklist" in types                       # 必有清单

    def test_suggest_medium_content(self):
        """
        测试用例：中等内容推荐
        验证点：应包含更多产品类型（PPT、SOP、提示词）
        """
        suggestions = product_generator.suggest_products(MEDIUM_CONTENT, "Python")
        types = [s["type"] for s in suggestions]

        # 中等内容应推荐更多类型
        assert "article" in types
        assert "ppt" in types                     # 200+ 字应有
        assert "sop" in types                             # 200+ 字应有

    def test_suggest_code_content_no_removed_type(self):
        """
        测试用例：含代码关键词内容不再推荐已移除的 code_doc
        验证点：移除 code_doc 后，代码内容只推荐基础类型，不再出现已下架类型
        """
        suggestions = product_generator.suggest_products(
            "Python编程实战：使用C++和JavaScript实现算法，代码优化",
            "编程"
        )
        types = [s["type"] for s in suggestions]
        assert "code_doc" not in types                    # 已移除类型不再推荐
        assert "article" in types                         # 基础推荐仍在

    def test_suggest_long_content(self):
        """
        测试用例：长内容推荐
        验证点：内容充足时推荐更多产品类型（至少应包含文章/导图/清单之外的重型产品）
        """
        suggestions = product_generator.suggest_products(LONG_CONTENT, "C语言")
        types = [s["type"] for s in suggestions]
        # 长内容应推荐较多产品类型
        assert len(suggestions) >= 6, f"实际推荐: {types}"
        assert "article" in types
        assert "ppt" in types or "sop" in types   # 200+ 应有
        assert "course_outline" in types or "quiz" in types or "interview_qa" in types  # 应有重型产品

    def test_suggestions_have_reason(self):
        """
        测试用例：每条推荐都有理由
        验证点：所有建议的 reason 字段非空
        """
        suggestions = product_generator.suggest_products(MEDIUM_CONTENT)
        for s in suggestions:
            assert "type" in s
            assert "reason" in s
            assert len(s["reason"]) > 0                   # 理由非空


# =============================================================================
# 测试 generate() 统一入口
# =============================================================================
class TestGenerate:
    """统一生成入口测试"""

    def test_generate_valid_type(self):
        """
        测试用例：生成有效类型的产品
        验证点：返回有效的产品内容
        """
        content = product_generator.generate(
            note_title="测试标题",
            note_content=MEDIUM_CONTENT,
            product_type="article",
            subject_name="Python",
        )
        assert isinstance(content, str)
        assert len(content) > 100
        assert "测试标题" in content

    def test_generate_invalid_type(self):
        """
        测试用例：生成无效类型
        验证点：返回错误提示（不抛异常）
        """
        content = product_generator.generate(
            note_title="测试",
            note_content=MEDIUM_CONTENT,
            product_type="invalid_type_xyz",
        )
        assert "不支持" in content                        # 错误提示

    def test_generate_all_types(self):
        """
        测试用例：遍历所有产品类型，确保都能正常生成
        验证点：每种类型都返回非空字符串
        """
        for ptype in PRODUCT_TYPES:
            content = product_generator.generate(
                note_title="测试",
                note_content=MEDIUM_CONTENT,
                product_type=ptype,
                subject_name="Python",
            )
            # 验证返回内容不为空
            assert content is not None
            assert isinstance(content, str)
            assert len(content) > 50, \
                f"产品类型 {ptype} 生成内容过短（{len(content)}字）"


# =============================================================================
# 测试 get_product_info() - 产品信息查询
# =============================================================================
class TestGetProductInfo:
    """产品信息查询测试"""

    def test_get_existing_product_info(self):
        """
        测试用例：查询已存在的产品类型信息
        验证点：返回完整的名称、图标、价格、平台信息
        """
        info = product_generator.get_product_info("article")
        assert info["name"] == "技术文章/公众号推文"
        assert info["icon"] == "📝"
        assert isinstance(info["price_range"], tuple)
        assert len(info["price_range"]) == 2
        assert len(info["platforms"]) > 0

    def test_get_nonexistent_product_info(self):
        """
        测试用例：查询不存在的产品类型
        验证点：返回默认占位信息（不抛异常）
        """
        info = product_generator.get_product_info("nonexistent_type")
        assert info["name"] == "nonexistent_type"         # 返回类型名本身
        assert info["icon"] == "📦"                       # 默认图标
        assert info["price_range"] == (0, 0)              # 默认价格

    def test_all_product_types_have_info(self):
        """
        测试用例：确保 PRODUCT_TYPES 中的每个类型在 get_product_info 有信息
        验证点：所有类型都有完整信息
        """
        for ptype in PRODUCT_TYPES:
            info = product_generator.get_product_info(ptype)
            assert "name" in info
            assert "icon" in info
            assert "price_range" in info
            assert "platforms" in info


# =============================================================================
# 测试 PRODUCT_TYPES 全局字典
# =============================================================================
class TestProductTypesDict:
    """PRODUCT_TYPES 字典的正确性验证"""

    def test_has_required_fields(self):
        """
        测试用例：所有产品类型都包含 name、icon、price_range、platforms
        """
        required = ["name", "icon", "price_range", "platforms"]
        for ptype, info in PRODUCT_TYPES.items():
            for field in required:
                assert field in info, \
                    f"产品类型 {ptype} 缺少字段 {field}"

    def test_price_range_is_tuple(self):
        """
        测试用例：price_range 是二元组
        验证点：长度为 2，最低价 < 最高价
        """
        for ptype, info in PRODUCT_TYPES.items():
            pr = info["price_range"]
            assert isinstance(pr, tuple)
            assert len(pr) == 2
            assert pr[0] <= pr[1], \
                f"产品类型 {ptype} 的最低价应 ≤ 最高价"

    def test_total_product_count(self):
        """
        测试用例：共 14 种产品类型
        """
        assert len(PRODUCT_TYPES) >= 14

    def test_removed_types_absent(self):
        """
        F03 回归：2026-08 下架的 8 种历史类型不应再出现在 PRODUCT_TYPES。
        验证点：仅旧 GenerationTask 数据可读，不可再新建。
        """
        removed = {
            "schedule_template", "speech_sop", "course_creation_sop",
            "xiaohongshu_sop", "ima_knowledge_base", "solo_company_sop",
            "software_tutorial", "code_doc",
        }
        present = set(PRODUCT_TYPES.keys())
        assert removed.isdisjoint(present), \
            f"以下类型本应已移除：{removed & present}"
        # 对外可生成类型恰好 14 种
        assert len(present) == 14
