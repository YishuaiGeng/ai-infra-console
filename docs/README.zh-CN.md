# AI Infra Console

[English](../README.md) | 简体中文

AI Infra Console 是一个可自托管的 AI 基础设施控制台，用于统一监控 GPU 服务器、查看 NVIDIA GPU 资源、管理本地模型文件、执行模型下载、控制 vLLM 部署、测试 OpenAI-compatible Endpoint，并审计关键操作。

它面向个人研究者、AI 开发者和小型实验室，适合管理自己账号下的服务器资源；目标不是替代 Kubernetes 或 Slurm，而是提供一个更轻量、更聚焦的 AI Server / GPU / Model Runtime 运维界面。

![AI Infra Console Dashboard](./assets/dashboard-dark.png)

> 真实服务器账号、私有地址、Token、注册令牌、模型平台 Token 和本地 `服务器资料/` 目录不得提交到 Git。生产密钥请放在环境变量或专用密钥管理系统中。

## 功能概览

- GPU 优先的 Dashboard：服务器状态、GPU 分配、模型数量、部署健康状态和最近 24 小时资源趋势。
- Central API：JWT 会话、Admin/Viewer 角色、请求 ID、稳定错误结构和审计日志。
- 出站 Agent：采集主机指标、NVIDIA GPU 指标、GPU 进程、Docker/Ollama 能力、模型目录、下载任务、部署状态、健康检查和日志。
- 模型目录识别：Safetensors、PyTorch bin、GGUF、Hugging Face cache 和本地 Ollama。
- Hugging Face / ModelScope 搜索，以及由 Agent 执行的下载、取消、重试和删除流程。
- vLLM 部署生命周期：创建、启动、停止、重启、重试、删除、固定端口、精确 GPU 选择、健康检查和受限日志。
- OpenAI-compatible Endpoint 展示、复制、健康信息和受限 `/v1/chat/completions` 测试。
- 监控历史：CPU、RAM、磁盘、网络、GPU 利用率、显存、温度和功耗。
- 派生通知：服务器离线、磁盘不足、GPU 高温、显存接近满载、下载失败和部署失败。

## API 资源管理

项目已实现独立的 API 资源管理模块，用于登记和管理外部模型平台账号、加密 Credential、可用模型、健康状态、余额、额度和供应商支持的使用量数据。

该模块定位为 API 资产台账与用量同步控制台，不是 API Gateway，不接管正常业务请求，也不提供请求转发、协议转换、负载均衡或二级 API Key。

当前支持 OpenAI 与 Generic OpenAI-compatible Adapter；OpenAI 可同步组织级 Usage/Costs，兼容平台可同步模型并人工维护余额与用量快照。完整产品边界、数据模型、后端接口、Provider Adapter、安全方案、前端页面、测试策略和验收要求见 [API 资源管理模块开发文档](./API_RESOURCE_MANAGEMENT.md)。

## 架构

```text
Browser
  -> Next.js Web Console / BFF
  -> FastAPI Central API
  -> PostgreSQL, Redis, RQ
  <- Python Agent 出站心跳和任务轮询
  <- 服务器指标、GPU 遥测、模型目录、下载任务、部署状态和日志
```

Agent 只出站连接 Central，不开放入站端口，不提供远程 Shell、SSH Terminal 或任意命令执行接口。所有可变更操作都必须是类型化、白名单、可审计、受角色保护的操作。

## 服务器部署

```bash
git clone https://github.com/YishuaiGeng/ai-infra-console.git
cd ai-infra-console
cp .env.example .env
```

首次启动前请编辑 `.env`：

- `AI_INFRA_JWT_SECRET`：至少 32 字符的唯一随机密钥。
- `AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD`：首次管理员密码。
- `AI_INFRA_POSTGRES_PASSWORD`：强数据库密码。
- `AI_INFRA_MUTABLE_SERVER_NAMES`：Central 允许执行模型下载/删除/部署操作的服务器名称列表。
- 备份服务器、只读服务器或仅做 inventory 的服务器不要加入 mutable allowlist。

启动 Central：

```bash
docker compose up -d --build
```

Web 控制台默认地址：

```text
http://<server-host>:3000
```

首次管理员账号由以下变量创建：

```text
AI_INFRA_BOOTSTRAP_ADMIN_USERNAME
AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD
```

## Agent 接入

Agent 可部署在每台被管理服务器上，环境文件可参考 `deploy/systemd/agent.env.example`。

关键配置：

- `AI_INFRA_AGENT_CENTRAL_URL`：Agent 可访问的 Central URL。
- `AI_INFRA_AGENT_TOKEN`：一次性注册令牌。
- `AI_INFRA_AGENT_ALLOWED_MODEL_DIRECTORIES`：允许扫描的本地模型根目录。
- `AI_INFRA_AGENT_DEFAULT_MODEL_DIRECTORY`：模型下载默认目录。
- `AI_INFRA_AGENT_ENABLE_MODEL_MUTATIONS`：是否允许下载/删除模型。
- `AI_INFRA_AGENT_ENABLE_DEPLOYMENTS`：是否允许托管 vLLM 容器生命周期。
- `AI_INFRA_AGENT_VLLM_IMAGE`：经过审核并固定的 vLLM 镜像引用。

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `npm run dev` | 启动 Web 开发服务 |
| `npm run build` | 构建生产版 Web |
| `npm run check:web` | 执行 Web lint、类型检查、测试和构建 |
| `npm run check:api` | 执行 API lint、类型检查和测试 |
| `npm run check:agent` | 执行 Agent lint、类型检查和测试 |
| `npm run security:scan` | 扫描敏感文件和危险命令接口 |
| `npm run check` | 执行完整 Web、API、Agent 和安全检查 |
| `docker compose up -d --build` | 启动完整本地/服务器 Compose 栈 |

## 安全边界

AI Infra Console 面向敏感基础设施，默认不提供以下能力：

- 通用远程 Shell 或 SSH Terminal
- `/exec`、`/shell`、`/command` 或任意脚本接口
- 任意 Docker 镜像、volume 或主机路径修改接口
- Agent 入站监听
- 默认修改备份或只读服务器

更多说明见 [SECURITY.md](../SECURITY.md)。
