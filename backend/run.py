# 🔍 [语法] 模块级 docstring（三引号字符串）
# 🔍 [作用] 描述本文件用途——FastAPI 后端启动入口
# 🔍 [关联] 配合 backend/app/main.py 使用
# 🔍 [陷阱] 修改此文件需同步更新 README
"""
run.py - 后端启动脚本

最简的 uvicorn 启动入口。
开发时使用：python3 run.py
生产环境建议直接使用：uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

# 🔍 [语法] import 标准库模块
# 🔍 [作用] uvicorn 提供 ASGI 服务器；sys 提供系统路径操作；os 提供操作系统接口
# 🔍 [关联] uvicorn 会在启动时导入 app.main:app
# 🔍 [陷阱] uvicorn 版本需 >= 0.20，否则 reload 行为不同
import uvicorn
import sys
import os

# 🔍 [语法] sys.path.insert(0, path) — 在模块搜索路径最前面插入
# 🔍 [作用] 将当前文件所在目录（backend/）加入 sys.path，确保 uvicorn 能找到 `app.main:app`
# 🔍 [示例] uvicorn 接收字符串路径 "app.main:app"，会执行 from app.main import app
# 🔍 [陷阱] 如果不插入，uvicorn 可能因找不到 app 模块而 ImportError
sys.path.insert(0, os.path.dirname(__file__))

# 🔍 [语法] if __name__ == "__main__": 入口保护惯用法
# 🔍 [作用] 防止该文件被 import 时误启动服务器
# 🔍 [示例] `import run` 不会启动；`python run.py` 会启动
# 🔍 [陷阱] 如果删除此判断，其他模块 import run 时会触发服务器启动（灾难）
if __name__ == "__main__":

    # 🔍 [语法] uvicorn.run() 阻塞调用（启动后不返回）
    # 🔍 [作用] 启动 ASGI 服务器并保持运行
    # 🔍 [关联] 第一个参数 "app.main:app" 是 Python 模块路径格式
    # 🔍 [陷阱] 此处字符串不是文件路径，而是 Python 模块导入路径
    uvicorn.run(

        # 🔍 [语法] 模块路径字符串：模块.子模块:变量
        # 🔍 [作用] uvicorn 会动态导入 app.main 模块，并取出其中的 app 实例（FastAPI 实例）
        # 🔍 [示例] 等价于：from app.main import app; uvicorn.run(app, ...)
        # 🔍 [陷阱] 字符串大小写敏感；写错模块名会报 "Could not import module"
        "app.main:app",

        # 🔍 [语法] 关键字参数 host="0.0.0.0"
        # 🔍 [作用] 监听所有网卡（容器/远程可访问），而不仅是 127.0.0.1
        # 🔍 [陷阱] 生产环境建议绑 0.0.0.0 时配合 Nginx 反向代理 + 防火墙
        host="0.0.0.0",

        # 🔍 [语法] port=8000（整数）
        # 🔍 [作用] 监听 8000 端口（HTTP 常用端口）
        # 🔍 [陷阱] 小于 1024 的端口需要 root 权限
        port=8000,

        # 🔍 [语法] reload=True（布尔）
        # 🔍 [作用] 监控文件变化自动重启服务器（开发体验）
        # 🔍 [陷阱] 仅开发用！生产必须设 False（避免内存泄漏 + 多 worker 冲突）
        # 🔍 [陷阱] Windows 上 reload 可能不稳定，建议改用 watchfiles
        reload=True,
    )
