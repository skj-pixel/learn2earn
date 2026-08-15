# tests_minimal — 入口与核心模块的最小化测试

## 目标
仅对**入口与核心模块**（8 个文件）做基础校验：
- 入口：`backend/run.py`、`backend/app/main.py`、`frontend/src/main.jsx`、`frontend/src/App.jsx`
- 核心：`backend/app/database.py`、`backend/app/models.py`、`backend/app/services/llm_service.py`、`backend/app/routers/notes.py`、`frontend/src/store/useStore.js`

## 覆盖范围（共 8 个测试）
1. FastAPI 应用入口（lifespan + 路由挂载）
2. 数据库模块契约（无需建库）
3. ORM 模型 to_dict（含 None 安全处理）
4. LLM 服务可配置性（不发真实请求）
5. notes 路由 Pydantic 模型
6. 前端 useStore 导出形态
7. 根端点响应
8. 笔记列表端点契约

## 不依赖
- 不连真实 LLM（mock 掉）
- 不连真实 SQLite（使用 in-memory 或绕开）
- 不依赖网络

## 运行
```bash
cd /mnt/d/简历fy项目/把学习过程变成赚钱过程的app
python3 -m pytest tests_minimal/ -v
```
