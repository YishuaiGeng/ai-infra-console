# AI Infra Console

[![Phase](https://img.shields.io/badge/phase-2%20Agent-f59e0b)](./DEVELOPMENT_ROADMAP.md)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-0f766e)](../LICENSE)

[English](../README.md) | 简体中文

AI Infra Console 是一个面向个人研究者、AI 开发者和小型实验室的轻量级 AI 基础设施控制平面，用于统一查看和管理 AI 服务器、NVIDIA GPU、模型文件、推理部署、下载任务与 OpenAI Compatible API。

![AI Infra Console Dashboard](./assets/dashboard-dark.png)

> [!IMPORTANT]
> Phase 0 前端仍使用一套本地 Mock 数据，尚未接入后端。Phase 1 Central API、认证、Migration、Redis、Worker 与五服务 Compose 栈已经完成。Phase 2 Agent 正在开发；真实模型下载、部署生命周期操作和 vLLM 部署尚未实现。

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

根路由 `/` 会重定向到 `/dashboard`。动态路由可使用 Mock 示例 `/servers/srv-lab-4090-01` 和 `/deployments/dep-qwen32`。

## 技术栈

- Next.js 16、React 19、TypeScript
- Tailwind CSS 4、shadcn/ui、Base UI
- TanStack Query、TanStack Table 9
- React Hook Form、Zod
- Zustand、Recharts、Lucide React、next-themes、Sonner
- FastAPI、SQLAlchemy、Pydantic、Alembic、PostgreSQL、Redis、RQ
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
| `npm run check` | 执行全部 Web 和 API 检查 |
| `docker compose up -d --build` | 启动五服务本地栈 |

## 目录结构

```text
ai-infra-console/
├── apps/
│   ├── api/                 # FastAPI、Migration、Worker 和测试
│   └── web/                 # Next.js 应用
│       └── src/
│           ├── app/         # App Router 页面与布局
│           ├── components/  # 基础 UI 与业务组件
│           ├── config/      # 导航和产品配置
│           ├── features/    # 页面级功能组合
│           ├── mocks/       # 唯一 Mock 数据源
│           ├── stores/      # 客户端 UI 状态
│           └── types/       # 领域类型
├── compose.yaml
├── docs/                    # Roadmap、阶段计划和运维文档
├── CONTRIBUTING.md
├── SECURITY.md
└── package.json             # npm workspace 入口
```

Phase 2 正按照 [`docs/phases/PHASE_2_AGENT.md`](./phases/PHASE_2_AGENT.md) 的代码级计划新增 `apps/agent`。

## Roadmap

| Phase | 范围 | 状态 |
| --- | --- | --- |
| 0 | UI Foundation | 已完成 |
| 1 | Central API、数据库、Redis、认证 | 已完成 |
| 2 | Agent 注册、心跳、硬件采集 | 进行中 |
| 3 | 接入真实服务器和 GPU | 计划中 |
| 4 | 模型目录扫描与 Inventory | 计划中 |
| 5 | Hugging Face / ModelScope 下载 | 计划中 |
| 6 | Docker / vLLM 部署生命周期 | 计划中 |
| 7 | OpenAI Compatible API 测试 | 计划中 |
| 8 | 历史指标与通知 | 计划中 |
| 9 | Accessibility 与 UI Polish | 计划中 |

项目会在每个 Phase 结束后停下审查，不跨阶段提前实现。完整安排见 [开发 Roadmap](./DEVELOPMENT_ROADMAP.md) 和 [产品需求文档](../AI%20Infrastructure%20Control%20Center.md)。

## 安全边界

AI Infra Console 面向敏感基础设施。未来 Agent 只允许执行明确列入白名单的操作，项目范围内不提供任意远程 Shell、SSH Terminal、`/exec`、`/shell` 或 `/command` API。

不要提交真实服务器记录、账号密码、Registration Token、模型平台 Token 或私有地址。根目录的 `服务器资料/` 已被 `.gitignore` 明确排除。开发后端或 Agent 前请先阅读 [SECURITY.md](../SECURITY.md)。

## 参与贡献

欢迎提交 Issue 和范围清晰的 Pull Request。请先阅读 [CONTRIBUTING.md](../CONTRIBUTING.md)，遵守当前 Phase 边界，并为可见 UI 变更附上截图。

## License

本项目使用 [Apache License 2.0](../LICENSE)。
