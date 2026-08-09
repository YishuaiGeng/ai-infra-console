# AI Infra Console

[English](../README.md) | 简体中文

AI Infra Console 是一个面向个人研究者、AI 开发者和小型实验室的轻量级 AI 基础设施控制台，用于统一查看和管理服务器、NVIDIA GPU、本地模型文件、模型下载、vLLM 部署、OpenAI-compatible Endpoint 与审计日志。

![AI Infra Console Dashboard](./assets/dashboard-dark.png)

> 真实服务器账号、私有地址、Token 和本地 `服务器资料/` 目录不得提交到 Git。生产密钥请放在环境变量或你自己的密钥管理系统中。

## 当前状态

| Phase | 范围 | 状态 |
| --- | --- | --- |
| 0 | UI Foundation | 已完成 |
| 1 | Central API、数据库、Redis、认证 | 已完成 |
| 2 | 出站 Agent、心跳、硬件采集 | 已完成 |
| 3 | 真实服务器和 GPU 接入 | 已完成 |
| 4 | 模型目录扫描与 Inventory | 已完成 |
| 5 | Hugging Face / ModelScope 下载 | 已完成 |
| 6 | Docker / vLLM 部署生命周期 | 已完成 |
| 7 | OpenAI-compatible Endpoint 展示与测试 | 进行中 |
| 8 | Activity、历史指标和通知 | 进行中 |
| 9 | 可访问性与 UI 收尾 | 计划中 |

近期进展：

- `/apis` 已改为展示真实运行中 Deployment 暴露的 Endpoint。
- Test API Dialog 会通过 Central 对既有 Deployment Endpoint 发起受限 `/v1/chat/completions` 测试，浏览器不能提交任意 URL。
- `/activity` 已接入真实审计日志，并在返回前过滤敏感 detail 字段。

## 核心流程

```text
查看服务器和 GPU
  -> 找到可用 GPU
  -> 搜索或下载模型
  -> 查看模型安装位置
  -> 选择服务器和 GPU
  -> 使用 vLLM 部署
  -> 查看健康状态和日志
  -> 复制或测试 OpenAI-compatible Endpoint
  -> 停止或删除部署
  -> GPU 资源释放
```

## 本地启动

要求：

- Node.js 20.9 或更新版本
- npm 10 或更新版本
- Python 3.11 或更新版本，以及 uv 0.9 或更新版本
- 完整本地服务栈需要 Docker Engine 与 Compose v2

```bash
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000)。

完整 Compose 栈：

```bash
docker compose up -d --build
```

## 常用命令

| 命令 | 用途 |
| --- | --- |
| `npm run dev` | 启动 Web 开发服务 |
| `npm run lint` | 执行 Web ESLint |
| `npm run typecheck` | 执行 TypeScript 检查 |
| `npm run build` | 构建生产版 Web |
| `npm run check:api` | 执行 API lint、类型检查和测试 |
| `npm run check:agent` | 执行 Agent lint、类型检查和测试 |
| `npm run security:scan` | 扫描敏感文件和危险命令接口 |
| `npm run check` | 执行 Web、API、Agent 和安全检查 |

## 安全边界

项目面向敏感基础设施，Agent 只允许明确白名单能力。不要加入通用远程 Shell、SSH Terminal、`/exec`、`/shell`、`/command`、任意镜像、任意 volume 或任意主机路径修改接口。

更多说明见 [SECURITY.md](../SECURITY.md)。
