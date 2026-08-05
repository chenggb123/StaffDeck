# StaffDeck

StaffDeck is an enterprise platform for building and managing digital employees. It turns professional experience, business processes, and decision criteria into reusable, traceable AI employees.

## Core Capabilities

- Build and manage digital employees with profiles, capabilities, work records, and access scope.
- Create state-machine-driven SOPs from natural language.
- Search structured knowledge bases with source citations.
- Execute real work through tools, MCP, HTTP APIs, and scheduled tasks.
- Connect WeChat, WeCom, Feishu, and DingTalk channels.
- Control management access with role-based permissions.

## Tech Stack

- Backend: Python 3.11+, FastAPI, SQLModel, SQLite
- Frontend: React 18, TypeScript, Vite, Tailwind CSS
- Runtime: single-port FastAPI app for desktop and local deployments

## Quick Start

Requirements:

- Python 3.11+
- Node.js 20+
- An OpenAI-compatible Chat Completions endpoint and API key

macOS, Linux, or WSL:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -e "backend[dev]"
npm --prefix frontend-enterprise ci
cp backend/.env.example backend/.env
scripts/dev_up.sh --detach
```

Windows PowerShell:

```powershell
py -3 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -e "backend[dev]"
npm --prefix frontend-enterprise ci
Copy-Item backend\.env.example backend\.env
.\scripts\dev_up.ps1 --detach
```

Configure `backend/.env` with:

```dotenv
APP_SECRET="replace-with-a-long-random-secret"
DEMO_MODEL_BASE_URL="https://your-openai-compatible-endpoint/v1"
DEMO_MODEL_NAME="your-model-name"
DEMO_MODEL_API_KEY="your-api-key"
```

The default administrator is `admin` / `admin`. Change the password after the first login.

Open [http://127.0.0.1:5173/workspace/gallery](http://127.0.0.1:5173/workspace/gallery) and start a conversation.

## Role & Permission Management

StaffDeck uses a role-based permission model for management functions:

- `admin`: built-in administrator role with all permissions; cannot be edited or deleted.
- `member`: default role; permissions can be configured by an administrator.
- Custom roles: administrators can create custom roles and assign them to accounts.

Users without any management permission only access the employee gallery and chat workspace. Management entries are hidden unless the user's role includes the corresponding permission.

| Permission key | Management surface |
| --- | --- |
| `accounts.manage` | Account management |
| `roles.manage` | Role and permission management |
| `model_configs.manage` | Model configuration |
| `channels.manage` | Channel integration |
| `mcp.manage` | MCP and tool management |
| `system_settings.manage` | System settings |
| `agents.manage_global` | Global digital employee management |
| `scheduled_tasks.manage` | Enterprise scheduled tasks |
| `chat_ops.manage` | Chat operation management |
| `oversight.view` | Oversight audit |

## Project Layout

```text
backend/                    FastAPI APIs, agent runtime, storage, task workers
frontend-enterprise/        React/TypeScript workspace
contracts/agent/v1/         Agent protocol fixtures and schemas
scripts/                    Lifecycle and validation scripts
packaging/                  Platform packaging assets
```

## Development

```bash
# Backend tests
backend/.venv/bin/python -m pytest backend/tests

# Python lint
backend/.venv/bin/python -m ruff check backend

# Frontend tests
npm --prefix frontend-enterprise test

# Frontend type-check and production build
npm --prefix frontend-enterprise run build
```

## License

AGPL-3.0
