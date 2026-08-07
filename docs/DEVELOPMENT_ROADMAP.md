# AI Infra Console Development Roadmap

> 基于 `AI Infrastructure Control Center.md` 与 `一、开发原则.md` 整理。本文用于后续开发排期、任务拆分和阶段验收，不替代原始 PRD。

## 1. 当前仓库状态

- Phase 0 UI Foundation 已于 2026-08-07 完成，前端位于 `apps/web`。
- 当前目录已初始化为 git 仓库，默认分支为 `main`，并同步到 `git@github.com:YishuaiGeng/ai-infra-console.git`。
- 根目录使用 npm workspaces，统一提供 `dev`、`lint`、`typecheck`、`build` 和 `check` 命令。
- `docs/` 已包含开发 Roadmap、阶段代码任务、后端开发和部署目标文档；原始 PRD 仍保留在仓库根目录。
- 根目录已有两份核心文档：
  - `AI Infrastructure Control Center.md`：完整 PRD 与分阶段规划。
  - `一、开发原则.md`：当前开发约束，重点要求先做 Phase 0 UI Foundation。
- `服务器资料/` 下包含服务器与账号相关信息，已加入根目录 `.gitignore`，不得进入前端 mock、日志、README 或公开提交。

### 当前执行状态

| Phase | 状态 | 说明 |
| --- | --- | --- |
| Phase 0 | 已完成 | 所有必需路由、统一 Mock Data、主题、交互、响应式与开源文档已完成 |
| Phase 1 | 已完成 | Web、API 与五服务 Compose 门禁通过，PostgreSQL Migration、认证和 Worker 已有运行时证据 |
| Phase 2 | 已完成 | Agent 注册、采集、心跳、白名单操作及 Linux Compose 运行时门禁全部通过 |
| Phase 3 | 已完成 | 真实 Server/GPU API、SSE、Web Session 与多服务器页面已通过 Run 31207075696 |
| Phase 4 | 已完成 | 模型目录策略、Agent 扫描、Ollama Discovery、真实 Installed Models 与 Compose 门禁通过 |
| Phase 5 | 进行中 | 正在执行 Provider 搜索、受限 Agent 下载任务、进度控制和安全删除 |

Phase 0 分步结果：

- [x] Phase 0.1 项目初始化
- [x] Phase 0.2 基础目录与类型
- [x] Phase 0.3 统一 Mock Data
- [x] Phase 0.4 App Layout
- [x] Phase 0.5 基础 UI 与业务组件
- [x] Phase 0.6 全部必需页面
- [x] Phase 0.7 Loading / Empty / Error / Form / Responsive
- [x] Phase 0.8 lint / typecheck / build / 浏览器视觉验收

## 2. 产品主线

项目定位是一个面向个人研究者、AI 开发者和科研实验室的轻量级 AI Infrastructure Control Plane。

第一版必须优先打通这一条主链路：

```text
Open Console
  -> View Servers
  -> View GPUs
  -> Find Available GPU
  -> View Installed Models
  -> Search Hugging Face / ModelScope
  -> Download Model
  -> Select Server
  -> Select GPU
  -> Deploy with vLLM
  -> View Logs
  -> Get Endpoint
  -> Test API
  -> Stop Deployment
  -> GPU Becomes Available
```

开发过程中始终遵守三条边界：

- 先 UI 骨架，后真实后端，最后再接 Agent 与运行时能力。
- 所有真实操作必须通过白名单动作，不提供通用 Shell / SSH Terminal。
- 不提前引入 Kubernetes、Slurm、复杂调度、Billing、多组织、Notebook 或训练任务调度。

## 3. 推荐开发节奏

建议按 Phase 逐个完成，每个 Phase 独立验收，不跨阶段偷跑。

```text
Phase 0  UI Foundation
Phase 1  Backend Foundation
Phase 2  Agent
Phase 3  Server Integration
Phase 4  Model Inventory
Phase 5  Model Download
Phase 6  Deployment
Phase 7  API
Phase 8  Monitoring Polish
Phase 9  UI Polish
```

每个 Phase 的固定收尾动作：

- 运行项目。
- 执行 lint。
- 执行 typecheck。
- 执行 build。
- 如有测试则执行测试。
- 更新 README / API 文档 / Migration 说明。
- 记录未完成项与下一阶段建议。
- 确认没有引入上一阶段 regression。

## 4. Phase 0：UI Foundation

### 目标

在无真实后端、无 Agent 的情况下，完成一个使用统一 Mock Data 的完整 Web UI Prototype，固定产品的信息架构、视觉语言和核心交互。

### 约束

- 不实现真实 Agent。
- 不实现 pynvml / nvidia-smi。
- 不实现真实 Hugging Face / ModelScope 下载。
- 不启动真实 Docker / vLLM / Ollama。
- 不实现复杂认证和复杂后端。
- 不用 Mock API 假装后端已经完成，只使用本地统一 mock 数据。

### 任务拆分

#### Phase 0.1 项目初始化

- 建立 `apps/web` 前端应用。
- 使用 Next.js、React、TypeScript、Tailwind CSS、shadcn/ui、Lucide React。
- 安装 TanStack Query、TanStack Table、React Hook Form、Zod、Zustand、Recharts。
- 建立基础 lint、typecheck、build 命令。
- 确定包管理器，并写入 README。

#### Phase 0.2 基础目录与类型

- 建立推荐目录：

```text
apps/web/src/app
apps/web/src/components/ui
apps/web/src/components/layout
apps/web/src/components/server
apps/web/src/components/gpu
apps/web/src/components/model
apps/web/src/components/deployment
apps/web/src/components/metrics
apps/web/src/features
apps/web/src/hooks
apps/web/src/lib
apps/web/src/mocks
apps/web/src/stores
apps/web/src/types
apps/web/src/config
```

- 定义核心类型：
  - `Server`
  - `GPU`
  - `GPUProcess`
  - `ModelDefinition`
  - `ModelFile`
  - `Deployment`
  - `DownloadTask`
  - `ApiEndpoint`
  - `ActivityLog`
  - `SystemSettings`

#### Phase 0.3 统一 Mock Data

- 在 `src/mocks` 或 `src/lib/mock-data` 下集中维护数据。
- 至少包含服务器：
  - `lab-4090-01`：Local，RTX 4090 x 4，Online。
  - `lab-a6000-01`：Local，RTX A6000 x 4，Online。
  - `cloud-h100-01`：Cloud，H100 x 1，Online。
  - `lab-old-01`：Local，RTX 3090 x 2，Offline。
- 至少包含模型：
  - `Qwen3-8B`
  - `Qwen3-32B`
  - `DeepSeek-R1-Distill-Qwen-32B`
  - `BGE-M3`
- 至少包含 Deployment 状态：
  - Running
  - Stopped
  - Failed
- Mock 数据之间必须能互相关联，避免页面之间数字矛盾。

#### Phase 0.4 App Layout

- 建立固定 Sidebar。
- Sidebar 支持 Expanded / Collapsed。
- 建立 Header。
- Header 包含 Breadcrumb、Theme Toggle、Notification 入口、User Menu。
- 支持 Light / Dark / System。
- 页面统一使用 `PageContainer`。

Sidebar 信息架构：

```text
Overview
  Dashboard

Infrastructure
  Servers
  GPUs

Models
  Model Library
  Installed Models
  Deployments
  Downloads

Services
  API Endpoints

System
  Activity
  Settings
```

#### Phase 0.5 基础 UI 与业务组件

- shadcn/ui 基础组件只放在 `components/ui`。
- 业务组件单独放置，避免污染基础组件层。
- 建立状态色语义：
  - Green：Online / Healthy / Available。
  - Blue：Running / Active。
  - Yellow：Warning。
  - Red：Failed / Offline / Critical。
  - Gray：Stopped / Unknown。
- 建立可复用组件：
  - `MetricCard`
  - `StatusBadge`
  - `DataTable`
  - `EmptyState`
  - `ErrorState`
  - `LoadingSkeleton`
  - `GPUCard`
  - `GPUStatusBadge`
  - `GPUMemoryBar`
  - `GPUUtilization`
  - `GPUProcessTable`
  - `ServerTable`
  - `ModelCard`
  - `ModelDownloadDialog`
  - `DeployModelDialog`
  - `DeploymentLogViewer`

#### Phase 0.6 页面实现

必须完成以下路由：

```text
/dashboard
/servers
/servers/[id]
/gpus
/models/library
/models
/deployments
/deployments/[id]
/downloads
/apis
/activity
/settings
```

页面重点：

- Dashboard：Metric Cards、GPU Resource Overview、Server Status、Running Models。
- Servers：TanStack Table、搜索、状态过滤、类型过滤、Add Server Dialog。
- Server Detail：Header、Overview、GPUs、Models、Processes、Settings Tabs。
- GPUs：默认 Table View，支持 Card View 与 Available Only。
- Model Library：Model Card Grid、Details、Download Dialog。
- Installed Models：表达同一模型在多个服务器的安装位置。
- Deployments：列表操作、Deploy Model Dialog、Mock Start / Stop / Restart。
- Deployment Detail：Overview、Metrics、Logs、Configuration，包含 Terminal-style Mock Log Viewer。
- Downloads：下载进度表，包含 Progress UI。
- API Endpoints：Copy URL、Copy Model Name、Test API Dialog。
- Activity：Audit Log 表。
- Settings：General、Monitoring、Models、Deployment、Security Tabs。

#### Phase 0.7 基础体验

- 所有页面都要有 Loading Skeleton。
- 空数据必须显示 Empty State。
- 错误必须显示 Error State 与 Retry。
- 表单统一使用 React Hook Form + Zod。
- 操作反馈使用 Toast / Dialog / Alert。
- 响应式优先保障 2560x1440、1920x1080、常规 Laptop，Tablet 可用，Mobile 可基本浏览。

#### Phase 0.8 验收标准

- 能启动前端。
- 所有必需路由可访问，无死路由。
- Dashboard 能在 5 秒内让用户识别可用 GPU。
- Sidebar、Header、Breadcrumb、Theme Toggle 工作正常。
- 状态颜色全局一致。
- Mock 数据统一，不同页面之间数字与关联关系一致。
- 关键页面不呈现普通 SaaS Admin Template 气质，而是 AI Infrastructure Console 气质。
- `npm run lint` 通过。
- `npm run typecheck` 通过。
- `npm run build` 通过。

## 5. Phase 1：Backend Foundation

代码级任务、技术决策、证据要求和阶段门详见 [`docs/phases/PHASE_1_BACKEND_FOUNDATION.md`](./phases/PHASE_1_BACKEND_FOUNDATION.md)。Phase 1 必须先完成该清单，再进入 Phase 2。

### 目标

建立 Central API 与基础数据层，为后续 Agent 接入做准备。

### 任务

- 建立 `apps/api`。
- 使用 FastAPI、SQLAlchemy、Pydantic、Alembic。
- 建立 PostgreSQL 与 Redis。
- 建立基础 Docker Compose：
  - web
  - api
  - postgres
  - redis
  - worker
- 建立统一 API 前缀：`/api/v1`。
- 建立统一错误格式。
- 建立日志格式与 request id。
- 建立基础 Authentication：
  - Username + Password。
  - Admin / Viewer 数据结构。
  - 第一版只开放 Admin 也可以。
- 建立数据库表初版：
  - users
  - servers
  - server_agents
  - server_model_directories
  - gpus
  - gpu_metrics
  - models
  - model_files
  - model_download_tasks
  - deployments
  - deployment_gpus
  - api_endpoints
  - notifications
  - system_settings
  - audit_logs

### 验收

- `docker compose up -d` 可启动基础服务。
- API health check 可访问。
- Alembic migration 可执行。
- 登录接口与当前用户接口可用。
- API 返回统一错误格式。

## 6. Phase 2：Agent

代码级任务、技术决策、证据要求和阶段门详见 [`docs/phases/PHASE_2_AGENT.md`](./phases/PHASE_2_AGENT.md)。Phase 2 必须先完成该清单，再进入 Phase 3。

### 目标

完成轻量 Agent 的注册、心跳和硬件采集能力。

### 任务

- 建立 `apps/agent`。
- 实现 Agent 注册：
  - 使用 registration token。
  - 数据库存 token hash，不保存明文。
  - token 可 revoke。
- 实现心跳：
  - 默认 10 秒上报。
  - 30 秒无心跳标记 Offline，后续可配置。
- 实现硬件采集：
  - Hostname
  - OS / Kernel
  - CPU / RAM / Disk / Network
  - Docker
  - NVIDIA Driver / CUDA
  - GPU
  - Ollama
  - Python
- GPU 信息优先使用 pynvml，fallback 到 nvidia-smi。
- 实现 GPU Process 查看。
- 实现 Agent Version 上报。
- 实现 Agent 白名单动作框架，不提供任意命令执行。

### 验收

- 能连接一台测试服务器，例如 `lab-server-01`。
- 平台显示 Online。
- 能显示 4 张 RTX 4090 GPU。
- 能显示 utilization、VRAM、temperature、power。
- 禁止存在 `/exec`、`/shell`、`/command` 之类通用远程命令接口。

## 7. Phase 3：Server Integration

代码级任务、技术决策、证据要求和阶段门详见 [`docs/phases/PHASE_3_SERVER_INTEGRATION.md`](./phases/PHASE_3_SERVER_INTEGRATION.md)。Phase 3 必须先完成该清单，再进入 Phase 4。

### 目标

把 Phase 0 的 Mock UI 接入真实后端与 Agent 数据，形成可用的服务器与 GPU 资源管理视图。

### 任务

- 替换 Dashboard、Servers、Server Detail、GPUs 的 Mock 数据。
- 建立前端 API client 与 TanStack Query。
- 建立 Server 在线 / 离线状态刷新。
- 建立 GPU 实时状态刷新。
- 实现 Server Detail 中 Overview、GPUs、Processes 的真实数据。
- 引入 WebSocket 或 SSE，用于心跳和指标更新。
- 建立多服务器视图。

### 验收

- 同时存在 `lab-server-01`、`lab-server-02`、`cloud-server-01` 时 Dashboard 能统一展示。
- 用户能快速识别每台服务器、每张 GPU 的状态。
- Offline Server 正确降级显示。
- UI 不再依赖服务器 / GPU mock 数据。

## 8. Phase 4：Model Inventory

代码级任务、技术决策、证据要求和阶段门详见 [`docs/phases/PHASE_4_MODEL_INVENTORY.md`](./phases/PHASE_4_MODEL_INVENTORY.md)。Phase 4 必须先完成该清单，再进入 Phase 5。

### 目标

实现模型目录管理、模型文件扫描和已安装模型视图。

### 任务

- 建立服务器级模型目录配置：
  - `/data/models`
  - `/mnt/models`
  - `/home/share/models`
  - Default 标记。
- Agent 扫描模型目录。
- 识别模型文件：
  - `config.json`
  - `tokenizer.json`
  - `generation_config.json`
  - `*.safetensors`
  - `*.bin`
  - `*.gguf`
- 提取模型元信息：
  - architecture
  - model type
  - size
  - quantization
  - path
- 实现 Model Definition、Model File、Model Deployment 的区分。
- 实现 Installed Models 页面真实数据。
- 实现 Ollama Discovery 基础能力。

### 验收

- 同一个模型可以显示在多个服务器位置。
- 能看到每个模型文件的 server、path、size、format、status。
- Ollama 已存在模型可被发现。

## 9. Phase 5：Model Download

代码级任务、技术决策、证据要求和阶段门详见 [`docs/phases/PHASE_5_MODEL_DOWNLOAD.md`](./phases/PHASE_5_MODEL_DOWNLOAD.md)。Phase 5 必须先完成该清单，再进入 Phase 6。

### 目标

实现 Hugging Face / ModelScope 搜索与指定服务器下载模型。

### 任务

- 实现 Hugging Face Search。
- 实现 ModelScope Search。
- 实现 Download Dialog 的真实提交。
- 后端创建 Download Task。
- Worker / Agent 执行下载。
- 支持进度、已下载大小、总大小、速度、状态。
- 支持 Retry、Cancel。
- 支持 HF_TOKEN、HF_ENDPOINT、MODELSCOPE_TOKEN、HTTP_PROXY、HTTPS_PROXY。
- 实现模型删除，必须二次确认。
- Agent 删除前检查目标路径属于 `allowed_model_directories`。

### 验收

- 搜索 `Qwen/Qwen3-8B` 能返回结果。
- 选择 `lab-server-01` 后能开始下载。
- Downloads 页面显示 Downloading、Progress、Speed。
- 完成后 Installed Models 显示 Installed。
- Cancel / Retry 行为正确。
- 删除不能越过允许的模型目录。

## 10. Phase 6：Deployment

### 目标

实现 vLLM Docker 部署与 Deployment 生命周期管理。

### 任务

- 实现 Deploy Model Dialog 的真实提交。
- 支持 Manual GPU 选择。
- 支持基础 Automatic GPU 选择：
  - 优先 Free VRAM。
  - 其次 GPU Utilization。
  - 最后同一服务器。
  - 默认不跨服务器。
- 使用 Docker 运行 vLLM。
- 配置 `CUDA_VISIBLE_DEVICES`。
- 支持参数：
  - Model Path
  - Port
  - Tensor Parallel Size
  - GPU Memory Utilization
  - Max Model Length
  - Data Type
  - Trust Remote Code
  - Extra Arguments
- 实现 Start、Stop、Restart、Delete。
- 实现 Health Check。
- 实现 Logs，优先 WebSocket 或 SSE。
- 实现端口冲突检测。

### 验收

- 选择 `Qwen3-8B`、`lab-server-01`、`GPU 2`、`vLLM`、`Port 8001` 后能部署。
- 状态进入 Running。
- 返回 `http://server:8001/v1`。
- Deployment Detail 能查看配置和日志。
- Stop 后 container 停止，GPU 显存释放，GPU 页面更新为 Available。

## 11. Phase 7：API

### 目标

完成 OpenAI Compatible API 信息展示与测试。

### 任务

- 建立 API Endpoints 数据。
- 展示模型、Endpoint、Server、Backend、Status、Port。
- 支持 Copy URL。
- 支持 Copy Model Name。
- 支持 Test API Dialog。
- 调用 `/v1/chat/completions`。
- 展示 response、latency、input tokens、output tokens、total tokens。
- 为未来 Unified API Gateway 预留数据结构。

### 验收

- 点击 Test API，发送 `Hello`，能获得成功返回。
- Endpoint Health 正确显示。
- 用户能直接复制 URL 与 model name 用于外部客户端。

## 12. Phase 8：Monitoring Polish

### 目标

补齐基础观测能力，让系统从资源查看工具变成可持续使用的控制台。

### 任务

- GPU Historical Metrics。
- Server Historical Metrics。
- Notifications。
- Activity Logs。
- 指标保留策略。
- GPU 温度高、磁盘空间低、服务器上下线、下载失败、部署失败等事件。
- Dashboard 和 Detail 页面加入必要历史趋势，但不堆叠无意义图表。

### 验收

- Activity 能追踪关键操作。
- Notifications 能提示关键异常。
- 历史指标能辅助判断资源趋势。
- 不影响 Dashboard 快速识别可用 GPU 的核心目标。

## 13. Phase 9：UI Polish

### 目标

做全局体验、视觉一致性和可访问性收尾。

### 任务

- 统一 Light / Dark / System。
- 检查 Empty State、Loading、Error、Toast、Dialog。
- 检查表单校验和错误提示。
- 检查响应式布局。
- 检查键盘可用性与基础 accessibility。
- 检查状态颜色、表格密度、卡片半径、边框和阴影。
- 删除重复组件。
- 整理 README、开发文档和部署说明。

### 验收

- 所有核心页面视觉一致。
- 关键流程无明显布局跳动、文字溢出或重叠。
- 桌面信息密度足够，移动端能基本查看。
- lint、typecheck、build、测试通过。

## 14. 建议优先级

### P0 必须优先

- Dashboard GPU Resource Overview。
- Servers。
- Server Detail。
- GPUs。
- Model Library。
- Deploy Model Dialog。
- 统一 Mock Data。
- 状态色和基础布局。

### P1 随 Phase 推进

- Downloads。
- API Endpoints。
- Activity。
- Settings。
- Deployment Detail Logs。

### 延后到后续阶段

- 真实 Agent。
- 真实下载。
- 真实 Docker / vLLM。
- 真实 API 测试。
- 历史指标。
- 通知。
- 复杂认证。

## 15. 开发前建议先确认的决策

- 包管理器：npm、pnpm 或 yarn。
- 前端是否放在 `apps/web`，后端是否放在 `apps/api`，Agent 是否放在 `apps/agent`。
- Session 或 JWT 作为 MVP 登录方案。
- 后台任务使用 Celery 还是 RQ。
- Agent 到 Central API 的通信方式：长轮询、WebSocket、SSE 或反向连接模型。
- 日志推送使用 WebSocket 还是 SSE。
- 敏感配置的加密方式。
- 指标保留周期默认值。
- 第一台真实验收服务器是哪一台。

## 16. 第一周建议安排

如果马上开始开发，建议第一周只围绕 Phase 0，不写后端。

### Day 1：项目骨架

- 初始化 `apps/web`。
- 配置 TypeScript、Tailwind、shadcn/ui。
- 建立目录结构。
- 建立基础 layout。

### Day 2：Mock 与基础组件

- 定义类型。
- 建立统一 mock data。
- 完成 MetricCard、StatusBadge、DataTable、EmptyState、ErrorState、Skeleton。

### Day 3：基础设施核心页

- 完成 Dashboard。
- 完成 Servers。
- 完成 Server Detail。
- 完成 GPUs。

### Day 4：模型与部署核心页

- 完成 Model Library。
- 完成 Installed Models。
- 完成 Deployments。
- 完成 Deploy Model Dialog。
- 完成 Deployment Detail 和 Log Viewer。

### Day 5：补齐体验与验收页

- 完成 Downloads。
- 完成 API Endpoints。
- 完成 Activity。
- 完成 Settings。
- 补齐 Loading / Empty / Error。
- 完成 responsive 检查。
- 运行 lint、typecheck、build。

## 17. 风险与注意事项

- Phase 0 页面较多，不能把所有页面做成薄薄的表格壳，应优先把 GPU、Server、Model Runtime 的业务感做出来。
- Mock 数据必须集中管理，否则 Dashboard、Servers、GPUs 很容易出现统计不一致。
- 后端和 Agent 一旦提前混入 Phase 0，会拖慢 UI 定型，并增加调试成本。
- 真实删除模型文件必须延后到 Agent 白名单动作和路径校验具备之后。
- 服务器资料中可能包含敏感信息，开发中不要直接复制到 mock、截图、日志或文档示例。
- 部署能力涉及端口、容器、GPU 显存和日志，Phase 6 前只做 UI，不做真实动作。

## 18. 下一步

Phase 0 已按以下顺序执行完成：

```text
Phase 0.1 -> Phase 0.2 -> Phase 0.3 -> Phase 0.4 -> Phase 0.5 -> Phase 0.6 -> Phase 0.7 -> Phase 0.8
```

维护者已于 2026-08-07 指示继续后续阶段。Phase 1 至 Phase 4 已于 2026-08-08 通过本地自动化、浏览器与 GitHub Actions Compose 门禁；当前正在执行 Phase 5，并采用固定循环：细化代码级任务、实现、自动化校验、运行时验收、更新文档、通过阶段门，然后才细化下一个 Phase。

部署目标与主机修改边界记录在 [`docs/DEPLOYMENT_TARGETS.md`](./DEPLOYMENT_TARGETS.md)：Central stack 最终部署到 `xiao-pro6000`，模型可下载到 `xiao-pro6000` 或 `xiao-cpu`，`asus-2024` 与 `asus-4090` 保持备用且不执行修改操作。

Phase 0 最终验证：

```text
npm run lint       PASS
npm run typecheck  PASS
npm run build      PASS (23 static pages)
```

浏览器检查已覆盖 1440x900 和 390x844 视口、全部 12 条必需路由，以及 Add Server、Download Model、Deploy Model、API Test、Theme、Sidebar、Filter 和 Tabs 等关键交互。

Phase 1 最终验证：

```text
npm run check                         PASS
npm run api:smoke                     PASS
GitHub Actions web/api/compose        PASS (run 31200348566)
PostgreSQL upgrade/downgrade/upgrade  PASS
Container auth + RQ Worker smoke      PASS
```

Phase 2 最终验证：

```text
npm run check                              PASS
API tests                                  PASS (26 tests, 82% coverage)
Agent tests and package build              PASS (28 tests, 82% coverage)
GitHub Actions web/api/agent/compose       PASS (run 31203551373)
Compose Agent register/heartbeat/revoke    PASS
```

Phase 3 最终验证：

```text
npm run check                                      PASS
Web / API / Agent tests                            PASS (8 / 31 / 28)
GitHub Actions web/api/agent/compose               PASS (run 31207075696)
Compose three-server/API/SSE/Web BFF smoke          PASS
Browser live refresh/list/detail/logout             PASS
```

Phase 4 最终验证：

```text
npm run check                                      PASS
Web / API / Agent tests                            PASS (11 / 36 / 38; Windows 1 skip)
GitHub Actions web/api/agent/compose               PASS (run 31210327473)
Compose model scan/API/BFF/SSE smoke                PASS
Browser inventory/search/detail/server-directory   PASS (1280x720 available viewport)
```
