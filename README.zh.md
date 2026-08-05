# StaffDeck

StaffDeck 是一套面向企业的数字员工构建与管理平台，将专业经验、业务流程和判断标准沉淀为可复用、可追溯的数字员工。

## 核心能力

- 构建和管理数字员工，包括员工档案、能力配置、工作记录和访问范围。
- 通过自然语言生成状态机驱动的 SOP，并支持版本管理和分支演化。
- 基于结构化知识库检索，并保留来源引用。
- 通过工具、MCP、HTTP API 和定时任务执行真实业务操作。
- 接入微信、企业微信、飞书和钉钉渠道。
- 使用角色权限控制管理端访问。

## 技术栈

- 后端：Python 3.11+、FastAPI、SQLModel、SQLite
- 前端：React 18、TypeScript、Vite、Tailwind CSS
- 运行时：单端口 FastAPI 应用，支持桌面端和本地部署

## 快速开始

环境要求：

- Python 3.11+
- Node.js 20+
- OpenAI Chat Completions 兼容的模型接口和 API Key

macOS、Linux 或 WSL：

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e "backend[dev]"
npm --prefix frontend-enterprise ci
cp backend/.env.example backend/.env
scripts/dev_up.sh --detach
```

Windows PowerShell：

```powershell
py -3 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
npm --prefix frontend-enterprise ci
Copy-Item backend\.env.example backend\.env
.\scripts\dev_up.ps1 --detach
```

配置 `backend/.env`：

```dotenv
APP_SECRET="请替换为足够长的随机字符串"
DEMO_MODEL_BASE_URL="https://你的OpenAI兼容接口/v1"
DEMO_MODEL_NAME="你的模型名"
DEMO_MODEL_API_KEY="你的API-Key"
```

默认管理员账号为 `admin` / `admin`，请在首次登录后修改密码。

打开 [http://127.0.0.1:5173/workspace/gallery](http://127.0.0.1:5173/workspace/gallery) 开始对话。

## 角色权限管理

StaffDeck 使用基于角色的权限模型控制管理端功能：

- `admin`：内置管理员角色，默认拥有全部权限，不可编辑或删除。
- `member`：默认成员角色，权限可由管理员配置。
- 自定义角色：管理员可以创建自定义角色，并分配给账号。

没有任何管理权限的用户只能进入员工广场和聊天工作区，管理端入口会按权限隐藏。

| 权限点 | 管理功能 |
| --- | --- |
| `accounts.manage` | 账号管理 |
| `roles.manage` | 角色权限管理 |
| `model_configs.manage` | 模型配置 |
| `channels.manage` | 渠道接入 |
| `mcp.manage` | MCP 与工具管理 |
| `system_settings.manage` | 系统设置 |
| `agents.manage_global` | 全局数字员工管理 |
| `scheduled_tasks.manage` | 企业定时任务 |
| `chat_ops.manage` | 会话管理操作 |
| `oversight.view` | 监督审计 |

## 项目结构

```text
backend/                    FastAPI API、Agent 运行时、存储和任务 worker
frontend-enterprise/        React/TypeScript 工作台
contracts/agent/v1/         Agent 协议 fixtures 和 schema
scripts/                    生命周期和校验脚本
packaging/                  平台打包资源
```

## 开发命令

```bash
# 后端测试
backend/.venv/bin/python -m pytest backend/tests

# Python 代码检查
backend/.venv/bin/python -m ruff check backend

# 前端测试
npm --prefix frontend-enterprise test

# 前端类型检查和生产构建
npm --prefix frontend-enterprise run build
```

## License

AGPL-3.0
