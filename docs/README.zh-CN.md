# AI Infra Console

[![Phase](https://img.shields.io/badge/phase-4%20Model%20Inventory-2563eb)](./DEVELOPMENT_ROADMAP.md)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-0f766e)](../LICENSE)

[English](../README.md) | 简体中文

AI Infra Console 是一个面向个人研究者、AI 开发者和小型实验室的轻量级 AI 基础设施控制平面，用于统一查看和管理 AI 服务器、NVIDIA GPU、模型文件、推理部署、下载任务与 OpenAI Compatible API。

![AI Infra Console Dashboard](./assets/dashboard-dark.png)

> [!IMPORTANT]
> Server 和 GPU 页面现已接入真实 Central API 与出站 Agent 数据。Phase 4 正在以受限目录扫描替换 Installed Models 的剩余 Fixture；模型下载和部署生命周期仍属于后续阶段。

## Phase 0 界面覆盖范围（Mock 驱动）

- GPU 优先的 Dashboard，首先展示当前可用设备。
- 服务器列表与详情，覆盖主机、GPU、模型和进程视图。
- GPU Table/Card 双视图，以及服务器、型号、状态和 Available Only 过滤。
- Hugging Face、ModelScope 模型库和带客户端校验的下载表单。
- 同一模型在多台服务器上的安装位置管理。
- Deployment 列表、配置、生命周期操作、指标和终端式日志。
- 模拟下载进度、返回合成响应的 Mock API 测试、Activity Audit Log 和 Settings。
- Light、Dark、System 主题与桌面、平板、基础移动端响应式布局。
- 所有页面共用统一 Mock 数据，确保统计和关联关系一致。

## Phase 1 后端（已完成）

- FastAPI 应用、`/api/v1`、Liveness、Readiness 和 OpenAPI 文档。
- 面向 PostgreSQL 的 SQLAlchemy 15 表初始 Schema 和 Alembic Migration。
- Username/Password 登录、Argon2 Hash、短期 JWT Bearer Token、Admin/Viewer 角色。
- 统一 API 错误格式、结构化日志、Request ID 透传和登录审计。
- Redis + RQ Worker，只允许注册任务函数，不提供任意命令执行入口。
- Web、API、PostgreSQL、Redis、Worker 五服务 Compose 定义。
- 后端 Lint、类型、Migration、认证、错误、健康检查和 Worker 自动化测试。

## Phase 2 Agent（已完成）

- 仅主动出站连接的 Python Agent、严格环境配置和结构化日志。
- Admin 签发的单 Agent 注册 Token，仅存摘要，并支持轮换与吊销。
- 注册和心跳 API 持久化主机指标、GPU Inventory、GPU 指标与 GPU Process。
- 使用 `psutil` 采集主机，检测 Docker/Ollama，NVIDIA 采集优先 NVML 并固定回退 `nvidia-smi`。
- 只允许三个只读白名单操作；不监听入站端口，不提供通用命令执行。
- 非 root 容器、加固 systemd 模板、wheel 安装脚本、退避重试和 CPU-only 降级。

## Phase 3 基础设施接入（已完成）

- 已认证的服务器、服务器详情、GPU 和基础设施汇总 Read API。
- 使用 Secure HttpOnly Cookie 的同源 Web BFF，API Bearer Token 不进入客户端存储。
- Redis SSE 失效通知与有界轮询恢复机制。
- Dashboard、Servers、Server Detail 和 GPU 双视图均使用真实数据，覆盖在线、离线、CPU-only 和多 GPU 节点。
- Admin 独占注册与 Agent Token 生命周期操作，Viewer 保留只读权限。
- 三服务器 Compose Smoke 覆盖 Migration、Agent Heartbeat、SSE、Web BFF 和权限边界。

## 产品主链路

以下是产品目标链路；Phase 0 只在浏览器中模拟相关交互。

```text
查看服务器和 GPU
  -> 找到可用 GPU
  -> 查看或下载模型
  -> 选择服务器和 GPU
  -> 使用 vLLM 或 Ollama 部署
  -> 查看日志和健康状态
  -> 复制或测试 OpenAI Compatible Endpoint
  -> 停止部署并释放 GPU
```

## 页面

| 区域 | 路由 |
| --- | --- |
| Overview | `/dashboard` |
| Infrastructure | `/servers`、`/servers/[id]`、`/gpus` |
| Models | `/models/library`、`/models`、`/deployments`、`/deployments/[id]`、`/downloads` |
| Services | `/apis` |
| System | `/activity`、`/settings` |

根路由 `/` 会重定向到 `/dashboard`。服务器详情使用真实 API 返回的 ID；`/deployments/dep-qwen32` 在 Phase 6 前仍是 Fixture 示例。

## 技术栈

- Next.js 16、React 19、TypeScript
- Tailwind CSS 4、shadcn/ui、Base UI
- TanStack Query、TanStack Table 9
- React Hook Form、Zod
- Zustand、Recharts、Lucide React、next-themes、Sonner
- FastAPI、SQLAlchemy、Pydantic、Alembic、PostgreSQL、Redis、RQ
- Agent 使用 psutil、NVIDIA Management Library、Docker SDK 和 HTTPX
- uv、Ruff、mypy、pytest

## 本地启动

环境要求：

- Node.js 20.9 或更高版本
- npm 10 或更高版本
- 后端开发需要 Python 3.11 或更高版本、uv 0.9 或更高版本
- 完整服务栈需要 Docker Engine 和 Compose v2

在仓库根目录执行：

```bash
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000)。如果端口已被占用，Next.js 会在终端显示实际使用的本地地址。

启动完整 Compose 服务栈前，请根据 `.env.example` 配置本地 `.env`，再执行 `docker compose up -d --build`。详细说明见 [后端开发文档](./BACKEND_DEVELOPMENT.md)。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `npm run dev` | 启动前端开发服务器 |
| `npm run lint` | 执行 ESLint |
| `npm run typecheck` | 执行 TypeScript 检查 |
| `npm run build` | 构建生产版本 |
| `npm run start` | 启动已构建的生产版本 |
| `npm run check:api` | 执行 API Lint、类型检查和测试 |
| `npm run api:smoke` | 临时启动 API、Redis、认证和 Worker 冒烟测试 |
| `npm run check:agent` | 执行 Agent Lint、严格类型检查和测试 |
| `npm run security:scan` | 检查通用命令接口与 Git 敏感文件边界 |
| `npm run check` | 执行全部 Web、API、Agent 与安全边界检查 |
| `docker compose up -d --build` | 启动五服务本地栈 |

可执行 `uv run --project apps/agent ai-infra-agent collect` 生成本机硬件快照。Token 签发与 systemd 运维见 [Agent 运维文档](./AGENT_OPERATIONS.md)。

## 目录结构

```text
ai-infra-console/
├── apps/
│   ├── api/                 # FastAPI、Migration、Worker 和测试
│   ├── agent/               # 出站 Agent、采集器、客户端和测试
│   └── web/                 # Next.js 应用
│       └── src/
│           ├── app/         # App Router 页面与布局
│           ├── components/  # 基础 UI 与业务组件
│           ├── config/      # 导航和产品配置
│           ├── features/    # 页面级功能组合
│           ├── mocks/       # 隔离给后续阶段使用的 Fixture
│           ├── stores/      # 客户端 UI 状态
│           └── types/       # 领域类型
├── compose.yaml
├── docs/                    # Roadmap、阶段计划和运维文档
├── CONTRIBUTING.md
├── SECURITY.md
└── package.json             # npm workspace 入口
```

Phase 3 已通过代码级、浏览器和 Linux Compose 阶段门。Phase 4 代码级计划见 [`docs/phases/PHASE_4_MODEL_INVENTORY.md`](./phases/PHASE_4_MODEL_INVENTORY.md)。

## Roadmap

| Phase | 范围 | 状态 |
| --- | --- | --- |
| 0 | UI Foundation | 已完成 |
| 1 | Central API、数据库、Redis、认证 | 已完成 |
| 2 | Agent 注册、心跳、硬件采集 | 已完成 |
| 3 | 接入真实服务器和 GPU | 已完成 |
| 4 | 模型目录扫描与 Inventory | 进行中 |
| 5 | Hugging Face / ModelScope 下载 | 计划中 |
| 6 | Docker / vLLM 部署生命周期 | 计划中 |
| 7 | OpenAI Compatible API 测试 | 计划中 |
| 8 | 历史指标与通知 | 计划中 |
| 9 | Accessibility 与 UI Polish | 计划中 |

项目在每个 Phase 结束时执行明确验收门，通过后再进入下一阶段。完整安排见 [开发 Roadmap](./DEVELOPMENT_ROADMAP.md) 和 [产品需求文档](../AI%20Infrastructure%20Control%20Center.md)。

## 安全边界

AI Infra Console 面向敏感基础设施。未来 Agent 只允许执行明确列入白名单的操作，项目范围内不提供任意远程 Shell、SSH Terminal、`/exec`、`/shell` 或 `/command` API。

不要提交真实服务器记录、账号密码、Registration Token、模型平台 Token 或私有地址。根目录的 `服务器资料/` 已被 `.gitignore` 明确排除。开发后端或 Agent 前请先阅读 [SECURITY.md](../SECURITY.md)。

## 参与贡献

欢迎提交 Issue 和范围清晰的 Pull Request。请先阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)，遵守当前 Phase 边界，并为可见 UI 变更附上截图。

## License

本项目使用 [Apache License 2.0](../LICENSE)。
