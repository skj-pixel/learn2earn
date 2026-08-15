# Learn2Earn — V5.1.3 Bugfix2 发行版

> **边学边生产知识付费产品** — 把学习过程直接变成可计价、可发布的赚钱过程。
>
> 杭州 AI 教育赛道 · 五层长期记忆 · 14 种产品形态 · 三段式 Agent 流水线

[![Version](https://img.shields.io/badge/version-V5.1.3--Bugfix2-green)](#) [![Backend](https://img.shields.io/badge/backend-FastAPI-009688)](#) [![Frontend](https://img.shields.io/badge/frontend-React%2018-61DAFB)](#) [![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)](#)

---

## 这是什么？

Learn2Earn 是一个面向自学者 / 知识工作者 / 高校学生的 AI 辅助型学习变现引擎：

1. 录入你的**学习笔记**
2. 系统自动调用多家大模型
3. 按 14 种产品形态（PPT / 小红书 SOP / 课程大纲 / 一人公司 / 演讲稿 / IMA 知识库 / 提示词包 / 工作流 / 软件教程 / 技能封装 / 反思日志 / 知识图谱 / 拆解卡片 / 短贴文）一键产出
4. **可售卖的知识付费产品**直接落到产品库

**核心差异化**：

- **五层长期记忆（MemoryBear）**：感知 / 工作 / 情节 / 显性 / 隐性，跨会话保持学习上下文
- **三段式 Agent 流水线**：分析 → 规划 → 生成 → 增强，反幻觉 + 思考链清除 + 评分
- **多 LLM 兼容**：内置 OpenRouter / ModelScope / 硅基流动 / 自定义 6 家 provider
- **Skill 插件系统**：每种产品类型独立配置推荐技能包
- **历史数据隔离**：每个版本独立数据库（`%LOCALAPPDATA%\Learn2Earn\version-data\`）

---

## 仓库结构

```
.
├── backend/                 # FastAPI + SQLAlchemy 后端
│   ├── app/
│   │   ├── main.py          # FastAPI 入口
│   │   ├── models.py        # Subject / Note / Product ORM
│   │   ├── routers/         # 10 个 APIRouter
│   │   ├── services/        # 生成器 / 记忆 / RAG / 质量 / Skill
│   │   └── bundled_skills/  # 预置技能包
│   ├── tests/               # pytest 测试
│   └── requirements.txt
├── frontend/                # Vite + React 18 前端
│   ├── src/
│   │   ├── components/      # 18 个 React 组件
│   │   ├── store/           # Zustand 状态
│   │   └── utils/
│   └── package.json
├── scripts/                 # 启动 / 准备 / 验证
│   ├── start_local_demo_fast.ps1   # 主启动器
│   ├── prepare_local_demo_once.ps1 # 首次准备
│   └── verify_local_launcher.ps1
├── security/                # 安全模块（混淆 / 加密 / 完整性）
├── vendor/                  # MemoryBear Python 引擎
├── docs/                    # 算法 / 架构 / 用户手册
├── hangzhou_contest/        # 评分引擎 / 看板
├── migrations/              # Alembic 数据库迁移
├── tests_minimal/           # 离线快速测试
├── tools/                   # 工具脚本
├── 启动Learn2Earn-V5.1.3-Bugfix2版.bat  ← **你点开要用的**
├── 启动Learn2Earn本地演示版.bat
├── 停止Learn2Earn本地演示版.bat
├── 首次准备依赖和构建产物.bat           ← **首次必跑**
└── requirements.txt
```

---

## 部署步骤（Windows 10 / 11）

### 1. 准备环境

| 组件 | 最低版本 | 说明 |
|---|---|---|
| Python | 3.10+ | 推荐 3.12；[python.org](https://www.python.org/downloads/) 下载，**安装时勾选 Add to PATH** |
| Node.js | 18+ | 仅构建前端需要；[nodejs.org](https://nodejs.org/) 下载 LTS |
| 磁盘 | ≥ 5 GB | 含前后端虚拟环境 + 前端依赖 |
| 内存 | ≥ 4 GB | LLM 调用建议 8 GB+ |

确认两个命令可执行：

```cmd
python --version
node --version
```

### 2. 克隆仓库

```bash
git clone https://github.com/<your-account>/Learn2Earn.git
cd Learn2Earn
```

### 3. 首次准备（必须）

双击 **首次准备依赖和构建产物.bat**。

它会自动：

1. 创建 Python 虚拟环境 `.venv`
2. 安装后端依赖（`backend/requirements.txt`）
3. 安装前端依赖（`frontend/node_modules/`，约 200MB）
4. 构建前端（`frontend/dist/`，约 1MB）
5. 初始化 SQLite 数据库

> 💡 首次需要 5–15 分钟（视网络速度）。

### 4. 启动服务

双击 **启动Learn2Earn-V5.1.3-Bugfix2版.bat**。

- 后端自动监听 9000-9010 之间首个空闲端口
- 浏览器自动打开 `http://127.0.0.1:<port>/`
- 窗口保持打开状态，关窗口即停服务

### 5. 配置 LLM（必做）

进入 **设置 → LLM 配置**，任选一种：

| Provider | base_url | Key 来源 |
|---|---|---|
| OpenRouter | `https://openrouter.ai/api/v1` | `OPENROUTER_API_KEY` |
| ModelScope（魔搭） | `https://dashscope.aliyuncs.com/compatible-mode/v1` | DashScope API Key |
| 硅基流动 | `https://api.siliconflow.cn/v1` | SiliconFlow Key |
| 自定义（OpenAI 兼容） | 用户填写 | 任意 |

也可通过系统环境变量 `LEARN2EARN_LLM_API_KEY` 全局注入（推荐做法）。

### 6. 停止服务

双击 **停止Learn2Earn本地演示版.bat**。

---

## 故障排查

| 症状 | 原因 | 修复 |
|---|---|---|
| 双击 .bat 闪退 | 系统未启用 PowerShell 或 .ps1 关联被破坏 | 在 PowerShell 跑 `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |
| 启动报 `port 9000 in use` | 上次未正常停止 | 跑 `停止Learn2Earn本地演示版.bat` |
| 启动报 `unable to open database file` | 数据库路径错乱 | 重新跑 `首次准备依赖和构建产物.bat` |
| 启动报 `python` 找不到 | 未装 Python | 装 Python 3.12，**勾选 Add to PATH** |
| 启动报 `node` 找不到 | 未装 Node | 装 Node 18+ LTS |
| LLM 401 | API Key 错误 | 在「设置 → LLM 配置」重填 |
| LLM 429 | 速率限制 | 切换 provider，或降低 max_tokens |
| 浏览器空白 | `frontend/dist` 未构建 | 跑 `首次准备依赖和构建产物.bat` |
| 浏览器 JS 报错 | 缓存 | `Ctrl+Shift+R` 硬刷新 |
| 启动器找不到脚本 | 仓库不完整 | 重新 `git clone`（不要只 copy 部分目录） |

---

## 开发与测试

### 冒烟测试

```bash
.venv\Scripts\activate
pytest tests_minimal/ -v
```

### 全量测试

```bash
pytest backend/tests/ -v
```

### 单独启动后端

```bash
.venv\Scripts\activate
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 9000 --reload
```

### 前端开发模式

```bash
cd frontend
npm install
npm run dev
```

---

## 数据与隐私

- **本地优先**：默认 SQLite，所有数据留在 `backend/app/learn2earn.db` 与 `%LOCALAPPDATA%\Learn2Earn\version-data\`。
- **云模式可选**：在 `backend/app/cloud_db.py` 配置 Supabase / 自托管 PostgREST。
- **LLM 调用**：所有提示词与笔记内容会发送给所选 LLM provider；**请勿输入敏感个人信息**。
- **API Key**：默认从 `LEARN2EARN_LLM_API_KEY` 环境变量读取；UI 配置写入 `backend/app/services/llm_config.json`（已加入 .gitignore）。

---

## 许可证

私有项目（Private License）。未经作者授权不得商业使用。

---

## 致谢

- FastAPI / React / Vite / SQLAlchemy
- 杭州开源人工智能基金会（GOAI 开放资源）
- X-CUBE-AI / STM32 / 嵌入式开源社区
- 所有为 Learn2Earn 提过 PR / 反馈的用户

---

> 📌 **遇到问题先看这里**：90% 的部署问题都可以通过 `首次准备依赖和构建产物.bat` 重新准备解决。
