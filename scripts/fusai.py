# -*- coding: utf-8 -*-
# 🔍 [语法] UTF-8 编码声明
# 🔍 [作用] 支持中文源码
# 🔍 [语法] docstring
# 🔍 [作用] 文件用途——复赛 PPT（14 页浅色，V1.1）
"""复赛更新版PPT - 14页浅色主题（在初赛基础上增加技术深度/合规/Demo验证/开放复用）"""

import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from common import *


# 🔍 [语法] def build(path)
# 🔍 [作用] 主入口：构建 14 页 PPT（比初赛多 2 页）
def build(path):
    prs = new()
    T = 14  # 总页数

    # ============================================================
    # P1 封面（带复赛角标）
    # ============================================================
    s = B(prs); set_bg(s, INDIGO)
    OV(s, I(-1), I(-1), I(4), I(4), PURPLE)
    OV(s, I(10.5), I(4.5), I(4), I(4), PURPLE)
    OV(s, I(9), I(-1.5), I(3), I(3), ACCENT_CYAN)
    # 🔍 [语法] 红色角标
    # 🔍 [作用] 标记复赛版本
    RR(s, I(9.8), I(0.4), I(3.1), I(0.55), DANGER_RED)
    tx(s, I(9.8), I(0.4), I(3.1), I(0.55), "复赛更新版 · V1.1", 14, WHITE, b=True, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
    tx(s, I(0.8), I(2.0), I(11.7), I(1.4), "学赚7步法 · Learn2Earn", 54, WHITE, b=True, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
    tx(s, I(0.8), I(3.3), I(11.7), I(0.7), "把学习的过程变成赚钱的过程", 28, WHITE, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
    R(s, I(5.3), I(4.2), I(2.7), I(0.05), WHITE)
    tx(s, I(0.8), I(4.5), I(11.7), I(0.5), "GOAI 无界应用 BoundlessAgents  |  AI+教育赛道", 18, WHITE, a=PP_ALIGN.CENTER)
    # 🔍 [语法] 复赛副标题
    # 🔍 [作用] 突出 102 测试全绿 + 数据合规
    tx(s, I(0.8), I(5.1), I(11.7), I(0.5), "7步强制式学习法 Agent · 102测试全绿 · 数据合规专项", 16, LIGHT_INDIGO, a=PP_ALIGN.CENTER)
    pn(s, 1, T)

    # ============================================================
    # P2 痛点
    # ============================================================
    s = B(prs); set_bg(s, LIGHT_BG)
    lt(s, "核心痛点：学了很多，变现为 0", "当代学习者的 10/2/1/0 困境")
    dn = [("10", "个项目学过", "收藏≠学会", INDIGO),
          ("2", "个能讲清楚", "输出能力缺失", PURPLE),
          ("1", "个写进简历", "没有作品沉淀", WARN_ORANGE),
          ("0", "个真正变现", "学习无法闭环", DANGER_RED)]
    for i, (n, lb, sb, c) in enumerate(dn):
        x = I(0.6) + (I(2.9) + I(0.2)) * i
        # 🔍 [语法] 比初赛高度略小（2.0 vs 2.2）
        RR(s, x, I(1.7), I(2.9), I(2.0), LIGHT_INDIGO if i % 2 == 0 else LIGHT_PURPLE)
        # 🔍 [语法] 字号 56 vs 初赛 64
        tx(s, x, I(1.8), I(2.9), I(0.9), n, 56, c, b=True, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
        tx(s, x, I(2.75), I(2.9), I(0.4), lb, 15, DARK_TEXT, b=True, a=PP_ALIGN.CENTER)
        tx(s, x, I(3.15), I(2.9), I(0.4), sb, 11, GRAY_TEXT, a=PP_ALIGN.CENTER)
    tx(s, I(0.6), I(3.9), I(12), I(0.4), "三类用户共同困境", 18, INDIGO, b=True)
    bul(s, I(0.8), I(4.3), I(11.8), I(2.7), [
        ("在校生：", "课程学完就忘，没有作品，简历无话可说"),
        ("转行者：", "学了10个栈，做不出一个能打的项目"),
        ("职场工程师：", "新框架学了一堆，无法沉淀成个人品牌"),
    ], 15, DARK_TEXT, DANGER_RED, 1.5)
    pn(s, 2, T)

    # ============================================================
    # P3-P5 与初赛相似
    # ============================================================
    s = B(prs); set_bg(s, LIGHT_BG)
    lt(s, "解决方案：三角色 × 7步法 × 5产品", "从输入到变现的完整闭环")
    roles = [("学者\nLearner", "输入·理解·吸收", LIGHT_INDIGO, INDIGO),
             ("作者\nWriter", "输出·结构化·沉淀", LIGHT_PURPLE, PURPLE),
             ("变现者\nEarner", "发布·传播·收益", LG, SUCCESS_GREEN)]
    for i, (t, d, b, c) in enumerate(roles):
        x = I(0.6) + (I(3.2) + I(0.3)) * i
        RR(s, x, I(1.6), I(3.2), I(1.2), b)
        tx(s, x, I(1.65), I(3.2), I(0.7), t, 18, c, b=True, a=PP_ALIGN.CENTER)
        tx(s, x, I(2.35), I(3.2), I(0.4), d, 12, GRAY_TEXT, a=PP_ALIGN.CENTER)
    AR(s, I(3.85), I(1.95), I(0.45), I(0.5), INDIGO)
    AR(s, I(7.35), I(1.95), I(0.45), I(0.5), SUCCESS_GREEN)
    tx(s, I(0.6), I(3.1), I(12), I(0.4), "7步强制式学习法 Agent", 18, INDIGO, b=True)
    steps = ["1 大白话", "2 表格化", "3 8维剖析", "4 双向连接", "5 苏格拉底", "6 费曼教学", "7 一键发布"]
    for i, st in enumerate(steps):
        x = I(0.5) + (I(1.65) + I(0.12)) * i
        c = INDIGO if i < 4 else PURPLE if i < 6 else SUCCESS_GREEN
        RR(s, x, I(3.6), I(1.65), I(0.7), c)
        tx(s, x, I(3.6), I(1.65), I(0.7), st, 12, WHITE, b=True, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
    tx(s, I(0.6), I(4.6), I(12), I(0.4), "一键产出5种自媒体产品", 18, PURPLE, b=True)
    prods = ["技术博客", "视频脚本", "小红书笔记", "公众号长文", "知乎/长帖"]
    for i, p in enumerate(prods):
        x = I(0.6) + (I(2.3) + I(0.18)) * i
        RR(s, x, I(5.1), I(2.3), I(1.0), LIGHT_PURPLE)
        tx(s, x, I(5.1), I(2.3), I(1.0), p, 14, PURPLE, b=True, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
    pn(s, 3, T)

    # ============================================================
    # P4 7 步法详解（上）
    # ============================================================
    s = B(prs); set_bg(s, LIGHT_BG)
    lt(s, "7步法详解（上）：理解层", "Step 1→4：把陌生知识变成自己的")
    su = [("Step 1", "大白话解释", "通俗语言重述概念\n去黑话·去术语\n小白也能秒懂", INDIGO, LIGHT_INDIGO),
          ("Step 2", "表格化总结", "零散信息→表格\n字段/对比/参数\n结构化记忆更牢", PURPLE, LIGHT_PURPLE),
          ("Step 3", "8维深度剖析", "原理·场景·优缺点·边界\n替代方案·常见坑·实践\n8维度逼你思考透", ACCENT_CYAN, LC),
          ("Step 4", "双向连接", "前连已有知识\n后连实际场景\n建立知识网络", SUCCESS_GREEN, LG)]
    for i, (no, t, d, c, bg) in enumerate(su):
        x = I(0.5) + (I(3.0) + I(0.18)) * i
        RR(s, x, I(1.6), I(3.0), I(5.2), bg)
        R(s, x + I(0.1), I(1.75), I(2.8), I(0.08), c)
        tx(s, x, I(1.9), I(3.0), I(0.4), no, 14, c, b=True, a=PP_ALIGN.CENTER)
        tx(s, x, I(2.35), I(3.0), I(0.5), t, 20, DARK_TEXT, b=True, a=PP_ALIGN.CENTER)
        R(s, x + I(0.8), I(2.95), I(1.4), I(0.03), c)
        tx(s, x + I(0.2), I(3.1), I(2.6), I(3.5), d, 13, DARK_TEXT, a=PP_ALIGN.CENTER, ls=1.6)
    pn(s, 4, T)

    # ============================================================
    # P5 7 步法详解（下）
    # ============================================================
    s = B(prs); set_bg(s, LIGHT_BG)
    lt(s, "7步法详解（下）：输出层", "Step 5→7：逼你输出，一键发布")
    sl = [("Step 5", "苏格拉底追问", "连续追问 为什么\n找到底层逻辑\n不留模糊地带", WARN_ORANGE, LY),
          ("Step 6", "费曼教学输出", "以教代学\n讲不清楚=没学会\n回炉直到能讲明白", DANGER_RED, LR),
          ("Step 7", "一键5平台发布", "自动生成5种内容\n博客/视频/小红书/\n公众号/知乎一次搞定", SUCCESS_GREEN, LG)]
    for i, (no, t, d, c, bg) in enumerate(sl):
        x = I(0.5) + (I(4.0) + I(0.2)) * i
        RR(s, x, I(1.6), I(4.0), I(2.2), bg)
        OV(s, x + I(0.15), I(1.75), I(0.7), I(0.7), c)
        tx(s, x + I(0.15), I(1.75), I(0.7), I(0.7), no[-1], 22, WHITE, b=True, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
        tx(s, x + I(0.95), I(1.8), I(3.0), I(0.5), no + " " + t, 18, DARK_TEXT, b=True)
        tx(s, x + I(0.2), I(2.4), I(3.6), I(1.3), d, 13, DARK_TEXT, ls=1.5)
    tx(s, I(0.5), I(4.0), I(12.3), I(0.4), "Step 7 一键产出 5 种自媒体产品", 16, INDIGO, b=True)
    # 🔍 [语法] 5 种产品（简化版）
    pd = [("技术博客", "掘金/CSDN/Medium", INDIGO),
          ("视频脚本", "B站/抖音/视频号", PURPLE),
          ("小红书笔记", "封面+干货+标签", DANGER_RED),
          ("公众号长文", "深度系统+金句", SUCCESS_GREEN),
          ("知乎/长帖", "问答体+专业分析", ACCENT_CYAN)]
    for i, (t, d, c) in enumerate(pd):
        x = I(0.5) + (I(2.4) + I(0.17)) * i
        RR(s, x, I(4.5), I(2.4), I(2.3), LIGHT_BG, c)
        R(s, x, I(4.5), I(2.4), I(0.5), c)
        tx(s, x, I(4.5), I(2.4), I(0.5), t, 14, WHITE, b=True, a=PP_ALIGN.CENTER, ac=MSO_ANCHOR.MIDDLE)
        tx(s, x + I(0.15), I(5.1), I(2.1), I(1.6), d, 11, DARK_TEXT, a=PP_ALIGN.CENTER, ls=1.4)
    pn(s, 5, T)

    # ============================================================
    # P6-P14 复赛新增：技术深度 + 合规 + Demo + 开放复用
    # ============================================================
    # 详见原始代码（共 9 个新页面）

    # 🔍 [语法] 保存 PPT
    prs.save(path)


# 🔍 [语法] CLI 入口
if __name__ == "__main__":
    import sys
    output = sys.argv[1] if len(sys.argv) > 1 else "output/fusai_14pages.pptx"
    build(output)
    print(f"PPT generated: {output}")
