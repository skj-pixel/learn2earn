"""
conftest.py - 让 tests_minimal 在任意工作目录下都可被 pytest 找到

将 backend 目录加入 sys.path，避免在每个测试文件里重复 path 操作。
"""
import os
import sys

# backend/ 的绝对路径
BACKEND_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend")
)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)
