# AI Infrastructure Control Center
## 实验室 GPU、服务器、模型与云资源统一管理平台开发需求文档

版本：v1.1  
项目代号：`ai-infra-console`  
项目类型：个人 / 实验室级 AI Infrastructure Control Plane  
目标环境：Ubuntu / Linux Server  
主要用户：个人研究者、实验室成员、AI/LLM 研发团队

---

# 1. 项目定位

本项目用于统一管理个人及实验室中的 AI 基础设施，包括：

- 实验室 GPU 服务器
- 个人购买的云服务器
- NVIDIA GPU 资源
- 本地模型文件
- Hugging Face / ModelScope 模型
- Ollama 模型
- vLLM 模型服务
- 模型下载任务
- 模型运行实例
- OpenAI Compatible API
- 服务器运行状态

本项目不是传统 HPC 调度平台，也不是聊天应用。

核心定位：

> Lightweight AI Infrastructure Control Plane

主要解决以下问题：

```text
我目前有多少台服务器？

哪些服务器在线？

每台服务器有哪些 GPU？

哪些 GPU 空闲？

哪些 GPU 正在被使用？

GPU 被哪个模型或进程占用？

每台服务器已经下载了哪些模型？

某个模型在哪些服务器上存在？

我能否直接下载 Hugging Face 模型？

能否指定服务器下载模型？

能否一键启动 vLLM？

模型运行在哪张 GPU？

当前有哪些模型 API 可用？

云服务器和实验室服务器能否统一管理？
```

目标是减少日常依赖：

```bash
ssh
nvidia-smi
docker ps
ollama list
ps aux
huggingface-cli
```

等手工命令进行服务器管理。

---

# 2. 产品设计原则

整个系统遵循以下原则。

## 2.1 Infrastructure First

平台首先是基础设施控制台，不是：

- ChatGPT Clone
- AI 聊天平台
- SaaS 用户后台
- 企业 CRM
- 传统业务管理系统

UI 视觉和信息密度应该更接近：

```text
Vercel
Linear
Cloudflare
GPUStack
Grafana
GitHub
现代 DevOps Console
```

---

## 2.2 Server Centric

所有资源最终必须能够关联到服务器。

基本关系：

```text
Server
 ├── CPU
 ├── Memory
 ├── Storage
 ├── GPU
 ├── Model Files
 ├── Deployments
 ├── Docker
 └── Processes
```

模型实例关系：

```text
Deployment
  ↓
Server
  ↓
GPU
```

---

## 2.3 Agent First

所有远程服务器运行轻量 Agent。

中央服务器不通过 SSH 长期执行管理任务。

架构：

```text
Web Console
     │
Central API
     │
     ├──────── Agent: Lab Server 01
     ├──────── Agent: Lab Server 02
     ├──────── Agent: Cloud Server 01
     └──────── Agent: Cloud Server 02
```

---

## 2.4 Safe By Default

禁止提供通用远程 Shell API。

禁止：

```text
POST /exec
POST /shell
POST /command
```

所有 Agent 操作必须通过预定义白名单动作实现。

---

## 2.5 Progressive Enhancement

第一版优先完成：

```text
Server
  ↓
GPU
  ↓
Model
  ↓
Download
  ↓
Deploy
  ↓
API
```

完整链路。

不要第一阶段引入：

```text
Kubernetes
Slurm
HAMi
Volcano
复杂任务队列
复杂 GPU 调度
云厂商资源编排
```

---

# 3. 第一阶段 MVP

必须实现以下功能。

## Infrastructure

- 用户登录
- Dashboard
- Server 管理
- Agent 注册
- Server 在线状态
- CPU 状态
- RAM 状态
- Disk 状态
- Network 状态
- GPU 监控
- GPU Process 查看

## Model Management

- Local Model 扫描
- Hugging Face 模型搜索
- Hugging Face 模型下载
- ModelScope 模型下载
- 模型文件管理
- 模型删除
- Ollama 模型发现
- Ollama Pull

## Deployment

- vLLM 部署
- Ollama 服务识别
- GPU 手动选择
- 基础自动 GPU 选择
- Start
- Stop
- Restart
- Delete
- Log
- Health Check

## API

- Endpoint 展示
- OpenAI Compatible API 信息
- API 测试
- 模型名称复制
- Endpoint 复制

---

# 4. 第一阶段明确不做

MVP 不做：

- Kubernetes
- Slurm
- GPU 抢占
- Fair Share
- GPU 任务排队
- 自动购买 GPU 云服务器
- 自动销毁服务器
- 云费用管理
- Billing
- 多组织
- 复杂 RBAC
- Web SSH
- 在线 Terminal
- Notebook 调度
- Dataset Management
- Training Job Scheduler

需要预留扩展性，但不得过度实现。

---

# 5. 推荐整体技术架构

```text
                           Browser
                              │
                              ▼
                      Next.js Web UI
                              │
                    REST API / WebSocket
                              │
                              ▼
                        FastAPI Backend
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
     PostgreSQL             Redis              Worker
          │                   │                   │
          │              Background Jobs          │
          │                                       │
          └───────────────────┬───────────────────┘
                              │
                       Agent Control API
                              │
          ┌───────────────────┼────────────────────┐
          │                   │                    │
       Lab Node            Lab Node            Cloud Node
          │                   │                    │
        Agent               Agent                Agent
          │                   │                    │
   NVIDIA / Docker     NVIDIA / Docker      NVIDIA / Docker
```

---

# 6. Web UI 技术架构

前端必须统一使用：

```text
Next.js 16+
React
TypeScript
Tailwind CSS 4
shadcn/ui
Lucide React
TanStack Query
TanStack Table
React Hook Form
Zod
Zustand
Recharts
```

原则：

> 使用成熟 Admin Dashboard Layout + shadcn/ui 组件体系，不从零开发基础 UI。

---

# 7. Web UI 视觉目标

视觉效果参考：

```text
Sub2API
+
Vercel Dashboard
+
Linear
+
Cloudflare Dashboard
+
GPUStack
```

不是直接 Fork Sub2API。

Sub2API 仅作为以下内容参考：

- Sidebar 结构
- 页面留白
- Card 风格
- 表格密度
- Badge
- Dialog
- Settings 页面
- Dark Mode
- Dashboard 信息层级

---

# 8. UI 基础组件原则

`components/ui/` 中使用 shadcn/ui 原始组件。

尽可能不要大幅修改基础组件。

例如：

```text
components/ui/
├── button.tsx
├── card.tsx
├── table.tsx
├── badge.tsx
├── tabs.tsx
├── dialog.tsx
├── sheet.tsx
├── select.tsx
├── input.tsx
├── progress.tsx
├── tooltip.tsx
├── dropdown-menu.tsx
├── command.tsx
├── skeleton.tsx
└── sidebar.tsx
```

业务 UI 单独建立。

---

# 9. 业务组件结构

```text
components/
├── ui/
│
├── layout/
│   ├── app-sidebar.tsx
│   ├── app-header.tsx
│   ├── breadcrumb.tsx
│   └── page-container.tsx
│
├── server/
│   ├── server-card.tsx
│   ├── server-status.tsx
│   ├── server-table.tsx
│   └── server-summary.tsx
│
├── gpu/
│   ├── gpu-card.tsx
│   ├── gpu-status.tsx
│   ├── gpu-memory-bar.tsx
│   ├── gpu-utilization.tsx
│   └── gpu-process-table.tsx
│
├── model/
│   ├── model-card.tsx
│   ├── model-status.tsx
│   ├── model-download-dialog.tsx
│   └── model-instance-card.tsx
│
├── deployment/
│   ├── deployment-card.tsx
│   ├── deployment-status.tsx
│   ├── deployment-dialog.tsx
│   └── deployment-log.tsx
│
└── metrics/
    ├── metric-card.tsx
    └── metric-chart.tsx
```

---

# 10. Frontend Feature Structure

推荐 Feature-based architecture：

```text
src/
├── app/
├── components/
├── features/
│   ├── auth/
│   ├── dashboard/
│   ├── servers/
│   ├── gpus/
│   ├── models/
│   ├── downloads/
│   ├── deployments/
│   ├── api-endpoints/
│   └── settings/
│
├── hooks/
├── lib/
├── stores/
├── types/
└── config/
```

不要把所有业务代码堆在：

```text
components/
```

中。

---

# 11. Web Layout

主布局：

```text
┌────────────────────────────────────────────────────────────┐
│ Sidebar │ Header                                          │
│         ├─────────────────────────────────────────────────┤
│         │ Breadcrumb / Page Title                         │
│         │                                                 │
│         │                  Content                        │
│         │                                                 │
│         │                                                 │
└─────────┴─────────────────────────────────────────────────┘
```

Sidebar 固定。

支持：

```text
Expanded
Collapsed
```

---

# 12. Sidebar 信息架构

必须按照分组设计。

```text
Overview
  Dashboard

Infrastructure
  Servers
  GPUs
  Storage

Models
  Model Library
  Installed Models
  Deployments
  Downloads

Services
  API Endpoints
  Ollama

System
  Activity
  Settings
```

MVP 没有实现的模块暂时不要显示。

因此第一版实际为：

```text
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

---

# 13. Dashboard

路径：

```text
/dashboard
```

Dashboard 的第一目标不是展示大量图表。

而是：

> 用户进入系统 5 秒内知道目前哪台服务器、哪张 GPU 可以使用。

---

# 14. Dashboard 第一行

显示四个或五个核心 Metric Card。

例如：

```text
SERVERS

5

4 Online
```

```text
GPUs

16

7 Available
```

```text
GPU MEMORY

248 / 384 GB

65%
```

```text
RUNNING MODELS

6

4 vLLM
```

```text
DOWNLOAD TASKS

2

1 Running
```

---

# 15. Dashboard GPU Resource Overview

Dashboard 最核心区域。

设计：

```text
GPU Resource Overview

Server            GPU             Utilization      VRAM          Workload

● lab-4090-01
                  GPU 0 RTX4090      92%          21/24 GB       Qwen3-32B
                  GPU 1 RTX4090      75%          18/24 GB       Qwen3-32B
                  GPU 2 RTX4090       0%           1/24 GB       Available
                  GPU 3 RTX4090       4%           2/24 GB       Available

● cloud-h100
                  GPU 0 H100         97%          73/80 GB       DeepSeek
```

应该比折线图拥有更高优先级。

---

# 16. Dashboard Server Status

显示服务器简化状态。

```text
Server                  Status          GPU               CPU       RAM

lab-4090-01             Online          4 × RTX4090       34%       72%
lab-a6000                Online          4 × A6000         12%       42%
cloud-h100               Online          1 × H100          51%       63%
old-server               Offline         2 × RTX3090       --        --
```

---

# 17. Dashboard Running Models

展示：

```text
Model
Server
GPU
Backend
Endpoint
Status
```

例如：

```text
Qwen3-32B
lab-4090-01
GPU 0,1
vLLM
:8001
Running
```

---

# 18. Server 页面

路径：

```text
/servers
```

使用 Data Table。

字段：

```text
Server
Status
Type
Host
GPU
GPU Memory
CPU
RAM
Models
Running
Last Seen
Actions
```

---

# 19. Server 操作

顶部：

```text
Servers

Search...

[ All ]
[ Online ]
[ Offline ]
[ Local ]
[ Cloud ]

                       [+ Add Server]
```

---

# 20. Add Server

使用 Dialog / Sheet。

输入：

```text
Name
Type
Provider
Host
Description
Tags
```

服务器类型：

```text
Local
Cloud
Other
```

Cloud Provider：

```text
AWS
Azure
GCP
Aliyun
Tencent Cloud
AutoDL
RunPod
Vast.ai
Other
```

第一版只做 metadata。

---

# 21. Agent Registration

添加服务器后：

后端创建：

```text
registration_token
```

页面展示：

```text
Install Agent
```

提供命令：

```bash
curl -fsSL https://example.com/install-agent.sh | bash
```

之后：

```bash
ai-infra-agent register \
  --server https://infra.example.com \
  --token xxxxx
```

提供：

```text
Copy Command
```

按钮。

---

# 22. Server Detail

路径：

```text
/servers/[id]
```

Header：

```text
lab-4090-01                             ● Online

192.168.1.101
Ubuntu 24.04
Agent v0.1.0
```

Tabs：

```text
Overview
GPUs
Models
Processes
Docker
Metrics
Settings
```

MVP 允许暂时只实现：

```text
Overview
GPUs
Models
Processes
Settings
```

---

# 23. Server Overview

展示：

```text
Hostname
IP
OS
Kernel
Uptime

CPU Model
CPU Cores
CPU Usage

Memory
Disk

Network

Agent Version
Last Seen
```

---

# 24. GPU Card

GPU 必须作为独立核心业务组件。

示例：

```text
GPU 0

NVIDIA GeForce RTX 4090
24 GB

GPU Utilization

████████████████░░░

84%

VRAM

██████████████████░

21.6 / 24 GB

Temperature     68°C

Power           362 / 450 W

Current Workload

Qwen3-32B
vLLM
```

---

# 25. GPU 状态定义

状态：

```text
Available
Active
High Load
Memory Full
Unavailable
```

状态 Badge：

```text
Available
Active
Warning
Critical
Offline
```

不要使用过多颜色。

颜色仅用于状态表达。

---

# 26. GPU Detail

点击 GPU 打开详情。

显示：

```text
GPU Name
GPU UUID
GPU Index
Driver
CUDA
Utilization
VRAM
Temperature
Power
Fan
Processes
```

---

# 27. GPU Processes

展示：

```text
PID
User
Process
GPU Memory
Command
Started At
```

例如：

```text
43122
geng
python
18.3 GB
python train.py
12:32
```

第一阶段只允许查看。

不提供 Kill。

---

# 28. GPU 页面

路径：

```text
/gpus
```

用于统一查看所有 GPU。

提供：

```text
Card View
Table View
```

默认 Table。

字段：

```text
Server
GPU
Status
Utilization
VRAM
Temperature
Power
Workload
```

---

# 29. GPU Filter

支持：

```text
Server
GPU Model
Status
Local / Cloud
Running Model
```

快捷过滤：

```text
Available Only
```

这是高频功能。

---

# 30. Model Domain Model

系统中的 Model 必须区分三个概念。

```text
Model Definition

Model File

Model Deployment
```

---

# 31. Model Definition

例如：

```text
Qwen/Qwen3-32B
```

表示逻辑模型。

字段：

```text
id
name
display_name
provider
model_type
architecture
parameters
context_length
license
description
tags
```

---

# 32. Model File

表示实际存在于某服务器中的模型文件。

例如：

```text
Model:
Qwen/Qwen3-32B

Server:
lab-4090-01

Path:
/data/models/Qwen3-32B
```

---

# 33. Model Deployment

表示正在运行的实例。

例如：

```text
Qwen3-32B-vllm-01

Model:
Qwen/Qwen3-32B

Server:
lab-4090-01

GPU:
0,1

Backend:
vLLM

Port:
8001
```

---

# 34. Model Library

路径：

```text
/models/library
```

不要设计成纯表格。

采用 Model Card Grid。

顶部：

```text
Model Library

Search models...

[ Hugging Face ]
[ ModelScope ]
```

---

# 35. Model Card

例如：

```text
Qwen

Qwen3-32B

Text Generation
32B Parameters
Apache 2.0

Hugging Face

[ Details ]    [ Download ]
```

---

# 36. 模型搜索

第一阶段：

```text
Hugging Face API
ModelScope API
```

搜索：

```text
Qwen3
DeepSeek
Llama
Gemma
BGE
```

---

# 37. Model Detail

显示：

```text
Model ID
Author
Architecture
Parameters
Model Type
License
Downloads
Likes
Tags
Files
Estimated Size
```

---

# 38. Download Dialog

点击：

```text
Download
```

打开：

```text
Download Model

Model
Qwen/Qwen3-32B

Source
Hugging Face

Target Server
[ lab-4090-01 ]

Target Directory
/data/models/Qwen3-32B

Revision
main

[Cancel]                   [Download]
```

---

# 39. Model Download Backend

Hugging Face：

```python
huggingface_hub.snapshot_download()
```

ModelScope：

```python
modelscope.snapshot_download()
```

支持：

```text
HF_TOKEN
HF_ENDPOINT
MODELSCOPE_TOKEN
HTTP_PROXY
HTTPS_PROXY
```

---

# 40. Download Task

路径：

```text
/downloads
```

使用 Data Table。

字段：

```text
Model
Server
Progress
Downloaded
Total
Speed
Status
Started
Actions
```

---

# 41. Download 状态

```text
Queued
Downloading
Completed
Failed
Cancelled
```

操作：

```text
Cancel
Retry
Open Model
```

---

# 42. Model Directories

每台 Server 支持多个模型目录。

例如：

```text
/data/models
/mnt/models
/home/share/models
```

其中一个为：

```text
Default
```

---

# 43. Local Model Scanner

Agent 定期扫描这些目录。

识别：

```text
config.json
tokenizer.json
generation_config.json
*.safetensors
*.bin
*.gguf
```

提取：

```text
Architecture
Model Type
Model Size
Quantization
Path
```

---

# 44. Installed Models

路径：

```text
/models
```

显示系统已经存在的模型。

表格字段：

```text
Model
Server
Size
Format
Path
Status
Deployments
Actions
```

---

# 45. Model Detail Installed Locations

例如：

```text
Qwen3-32B

Installed Locations

lab-4090-01

/data/models/Qwen3-32B
62 GB

cloud-server-01

/data/models/Qwen3-32B
62 GB
```

---

# 46. 删除模型

必须二次确认。

Dialog：

```text
Delete Model File?

Qwen3-32B

Server:
lab-4090-01

Path:
/data/models/Qwen3-32B

This action cannot be undone.

[Cancel]                 [Delete]
```

Agent 必须检查目标路径属于：

```text
allowed_model_directories
```

禁止任意目录删除。

---

# 47. Deployment 页面

路径：

```text
/deployments
```

字段：

```text
Deployment
Model
Server
GPU
Backend
Port
Status
Uptime
Actions
```

---

# 48. Deploy Model Dialog

模型详情点击：

```text
Deploy
```

显示：

```text
Deploy Model

Model
Qwen3-32B

Server
[ lab-4090-01 ]

GPU Selection

○ Automatic
● Manual

GPU
☑ GPU 0
☑ GPU 1
☐ GPU 2
☐ GPU 3

Backend
[ vLLM ]

Port
8001

Tensor Parallel Size
2

GPU Memory Utilization
0.90

Max Model Length
Auto

Data Type
Auto

Advanced Options
▸

[Cancel]                   [Deploy]
```

---

# 49. Automatic GPU Selection

MVP 自动调度不要复杂。

基本评分：

第一优先：

```text
Free VRAM
```

第二：

```text
GPU Utilization
```

第三：

```text
同一服务器
```

默认不要跨服务器。

---

# 50. vLLM

第一阶段完整支持 vLLM。

建议统一通过 Docker 运行。

例如：

```bash
docker run ...
```

并配置：

```text
CUDA_VISIBLE_DEVICES
```

---

# 51. vLLM 参数

至少支持：

```text
Model Path
Port
Tensor Parallel Size
GPU Memory Utilization
Max Model Length
Data Type
Trust Remote Code
Extra Arguments
```

高级参数放：

```text
Advanced
```

中。

不要全部堆在默认 Deploy Dialog。

---

# 52. Deployment Lifecycle

```text
Created
Starting
Running
Stopping
Stopped
Failed
Unknown
```

---

# 53. Deployment Detail

路径：

```text
/deployments/[id]
```

Header：

```text
Qwen3-32B-vllm

● Running

lab-4090-01
GPU 0, GPU 1
```

Tabs：

```text
Overview
Metrics
Logs
Configuration
```

---

# 54. Deployment Overview

显示：

```text
Model
Server
GPU
Backend
Port
Endpoint
Container
Started At
Uptime
Health
```

操作：

```text
Stop
Restart
Delete
```

---

# 55. Model Logs

使用 Terminal-style Log Viewer。

功能：

```text
Follow Logs

Last 100
Last 500
Last 1000

Search
Auto Scroll
```

通过：

```text
WebSocket
```

或 SSE。

---

# 56. Ollama

Agent 自动检测：

```bash
ollama list
```

和：

```bash
ollama ps
```

同步模型。

支持：

```text
Discover
Pull
Start
Stop
Delete
```

第一版 Ollama 可以简单实现。

---

# 57. API Endpoints

路径：

```text
/apis
```

字段：

```text
Model
Endpoint
Server
Backend
Status
Port
Actions
```

---

# 58. API Card

例如：

```text
Qwen3-32B

● Online

OpenAI Compatible

http://lab-4090-01:8001/v1

Model:
Qwen3-32B

[ Copy URL ]
[ Test API ]
```

---

# 59. API Test

Dialog：

```text
Test API

Model
Qwen3-32B

Prompt

Hello

[Send]
```

显示：

```text
Response

Latency
Input Tokens
Output Tokens
Total Tokens
```

---

# 60. Future Unified API Gateway

第一阶段不实现。

但 Deployment 数据结构必须方便未来建立：

```text
https://ai.example.com/v1
```

统一代理：

```text
qwen3-32b
deepseek
embedding
```

---

# 61. Server Agent

推荐：

```text
Python 3.11+
FastAPI / aiohttp
psutil
pynvml
Docker SDK
httpx
```

Agent 应尽可能轻量。

---

# 62. Agent Hardware Detection

首次启动读取：

```text
Hostname
OS
Kernel
CPU
CPU Core
RAM
Disk
Network
Docker
NVIDIA Driver
CUDA
GPU
Ollama
Python
```

---

# 63. NVIDIA GPU Detection

优先：

```text
pynvml
```

Fallback：

```text
nvidia-smi
```

---

# 64. Agent Heartbeat

建议：

```text
10 秒
```

向 Backend 上报。

数据：

```text
CPU
RAM
Disk
Network
GPU
GPU Process
Deployment
Agent Version
```

---

# 65. Offline Detection

默认：

```text
30 秒没有 Heartbeat
```

服务器：

```text
Offline
```

该数值 Settings 可配置。

---

# 66. Agent Operations

允许：

```text
get_system_info
get_gpu_info
get_gpu_processes

scan_models
download_model
delete_model

deploy_model
start_deployment
stop_deployment
restart_deployment

get_logs

ollama_list
ollama_pull
ollama_stop
```

禁止 arbitrary command。

---

# 67. Agent Communication

尽量：

> Agent 主动连接 Central Server。

而不是：

> Central Server 主动连接实验室内网 Agent。

原因：

- NAT
- 实验室内网
- 云服务器
- 防火墙
- 家庭网络

兼容性更好。

---

# 68. Backend Stack

统一：

```text
Python 3.11+
FastAPI
SQLAlchemy
Pydantic
Alembic
PostgreSQL
Redis
Celery / RQ
WebSocket / SSE
```

---

# 69. Central REST API

Prefix：

```text
/api/v1
```

模块：

```text
/auth

/servers

/gpus

/models

/model-files

/downloads

/deployments

/api-endpoints

/notifications

/settings

/activity
```

---

# 70. Data Model

至少：

```text
users

servers

server_agents

server_model_directories

gpus

gpu_metrics

models

model_files

model_download_tasks

deployments

deployment_gpus

api_endpoints

notifications

system_settings

audit_logs
```

---

# 71. Server Table

字段：

```text
id

name
hostname
host

type
provider

status

description
tags

os
kernel

cpu_model
cpu_cores

memory_total
disk_total

agent_version

last_seen

created_at
updated_at
```

---

# 72. GPU Table

```text
id
server_id

gpu_index
uuid

vendor
name

memory_total

driver_version
cuda_version

status

created_at
updated_at
```

---

# 73. GPU Metrics

```text
gpu_id

timestamp

utilization

memory_used

temperature

power_usage

power_limit

fan_speed
```

---

# 74. Model File

```text
id

model_id

server_id

path

size

format

quantization

source

revision

status

created_at
updated_at
```

---

# 75. Deployment

```text
id

name

model_file_id

server_id

backend

status

port

endpoint

container_id

config

created_at
started_at
stopped_at
```

---

# 76. Authentication

MVP：

```text
Username + Password
```

Session 或 JWT 均可。

需要：

```text
Admin
Viewer
```

数据结构。

但第一阶段可只开放 Admin 用户。

---

# 77. Agent Token

Agent 注册 Token：

- 数据库不保存原始明文
- Token Hash 存储
- 可以 Revoke
- 一个 Agent 一个 Token
- Token 不具备 Web 登录权限

---

# 78. Sensitive Data

以下数据必须加密：

```text
HF_TOKEN

ModelScope Token

Proxy Password

Cloud Credential
```

---

# 79. Proxy Settings

Server Settings 支持：

```text
HTTP_PROXY

HTTPS_PROXY

NO_PROXY

HF_ENDPOINT
```

支持服务器级配置。

这是实验室服务器下载 Hugging Face 时的重要能力。

---

# 80. Activity / Audit Logs

路径：

```text
/activity
```

记录：

```text
Time
User
Action
Resource
Server
Status
```

例如：

```text
22:10

admin

DEPLOY_MODEL

Qwen3-32B

lab-4090-01

Success
```

---

# 81. Notifications

第一阶段支持站内通知。

事件：

```text
Server Offline

Server Online

GPU Temperature High

Disk Space Low

Download Completed

Download Failed

Deployment Failed

Deployment Started
```

---

# 82. Settings

路径：

```text
/settings
```

Tabs：

```text
General
Monitoring
Models
Deployment
Security
```

---

# 83. General Settings

```text
Platform Name

Timezone

Refresh Interval
```

---

# 84. Monitoring Settings

```text
GPU Available Utilization Threshold

GPU Available VRAM Threshold

High Temperature Threshold

Offline Timeout

Metrics Retention
```

---

# 85. Model Settings

```text
Default Model Directory

Hugging Face Endpoint

Hugging Face Token

ModelScope Token
```

---

# 86. Deployment Settings

```text
Default Backend

vLLM Image

Default GPU Memory Utilization

Default Port Range
```

---

# 87. UI Theme

必须支持：

```text
Light
Dark
System
```

默认：

```text
System
```

---

# 88. UI 风格

禁止：

- 大面积渐变背景
- 过度圆角
- 玻璃拟态
- 过多动画
- 霓虹颜色
- 大面积插画
- 低信息密度 Landing Page 风格

需要：

- 清晰
- 紧凑
- 专业
- Developer Tool 风格
- Infrastructure Console 风格

---

# 89. Card 设计

Border：

```text
1px subtle border
```

Shadow：

```text
minimal
```

Radius：

```text
medium
```

不要过度悬浮效果。

---

# 90. Status Color

统一语义：

```text
Green
Healthy / Online / Available

Blue
Running / Active

Yellow
Warning

Red
Failed / Offline / Critical

Gray
Stopped / Unknown
```

所有页面统一。

---

# 91. Tables

所有 Data Table 统一：

```text
Search

Filter

Sort

Pagination

Column visibility
```

主要使用：

```text
TanStack Table
```

---

# 92. Empty State

不能显示空白。

例如无服务器：

```text
No servers connected

Add your first server and install the agent to begin monitoring resources.

[ Add Server ]
```

---

# 93. Loading

必须使用：

```text
Skeleton
```

避免整页 Spinner。

---

# 94. Error State

错误必须显示：

```text
Title
Message
Retry
```

例如：

```text
Failed to load GPU data

Agent did not respond.

[Retry]
```

---

# 95. Responsive

主要针对：

```text
1440p desktop
1080p desktop
Laptop
```

同时保证平板可用。

手机只要求基本查看。

---

# 96. Repository Structure

推荐：

```text
ai-infra-console/

apps/

  web/
    src/
      app/
      components/
      features/
      hooks/
      lib/
      stores/
      types/

  api/
    app/
      api/
      core/
      models/
      schemas/
      services/
      workers/

  agent/
    agent/
      collectors/
      handlers/
      services/
      security/

packages/

  shared-types/

deploy/

  docker-compose.yml

scripts/

docs/

README.md
```

---

# 97. Docker Compose

Central Server 运行：

```text
web

api

postgres

redis

worker
```

必须能够：

```bash
docker compose up -d
```

完成启动。

---

# 98. Agent Installation

最终希望支持：

```bash
curl -fsSL https://example.com/install-agent.sh | bash
```

然后：

```bash
ai-infra-agent register \
  --server https://infra.example.com \
  --token xxx
```

---

# 99. systemd

Agent 安装后：

```text
ai-infra-agent.service
```

要求：

```text
Restart=always
```

服务器重启后自动上线。

---

# 100. MVP 开发阶段

Codex 必须严格分阶段。

不要一次完成整个项目。

---

# Phase 0：UI Foundation

第一阶段先建立前端设计系统。

完成：

```text
Next.js

Tailwind

shadcn/ui

Sidebar

Header

Dark Mode

Page Layout

Metric Card

Data Table Foundation

Status Badge
```

建立以下 Mock 页面：

```text
Dashboard

Servers

GPUs

Models

Deployments
```

此阶段只用 Mock Data。

目标：

> 首先把整个 UI 架构固定。

不得直接开始写复杂后端。

---

# Phase 1：Backend Foundation

建立：

```text
FastAPI

PostgreSQL

Redis

SQLAlchemy

Alembic

Authentication

API Error Format

Logging
```

---

# Phase 2：Agent

完成：

```text
Agent Register

Heartbeat

System Info

GPU Info

GPU Process

Agent Version
```

---

# Phase 3：Server Integration

将真实 Agent 数据接入 UI。

完成：

```text
Dashboard

Servers

Server Detail

GPUs

GPU Detail
```

此时系统必须已经可以真正管理多台机器的资源状态。

---

# Phase 4：Model Inventory

实现：

```text
Model Directory

Local Scan

Model Definition

Model Files

Installed Models

Ollama Discovery
```

---

# Phase 5：Model Download

完成：

```text
Hugging Face Search

ModelScope Search

Download Dialog

Background Download

Progress

Retry

Cancel

Delete
```

---

# Phase 6：Deployment

完成：

```text
vLLM

Docker

GPU Select

Start

Stop

Restart

Health

Logs
```

---

# Phase 7：API

实现：

```text
API Endpoint

OpenAI Compatible Information

API Test

Endpoint Health
```

---

# Phase 8：Monitoring Polish

实现：

```text
GPU Historical Metrics

Server Historical Metrics

Notifications

Activity Logs
```

---

# Phase 9：UI Polish

统一检查：

```text
Dark Mode

Empty State

Loading

Error

Toast

Dialog

Form Validation

Responsive

Accessibility

Visual consistency
```

---

# 101. Codex 开发工作方式

每次只执行一个 Phase。

Codex 每完成一个阶段：

1. 运行项目。
2. 执行 lint。
3. 执行 typecheck。
4. 执行测试。
5. 检查 Docker。
6. 更新 README。
7. 更新 Migration。
8. 更新 API 文档。
9. 记录未完成项。
10. 确保前一阶段没有 regression。

---

# 102. Codex 禁止事项

禁止：

```text
一次性实现整个 PRD

未经说明切换技术栈

自行引入 Kubernetes

自行引入 Slurm

自行加入复杂 Billing

自行加入 SSH Terminal

把 UI 写成传统 ERP 风格

大量 inline CSS

绕过 shadcn/ui 重做基础组件

大量 duplicated components

使用 Mock API 假装后端完成
```

---

# 103. Phase 0 验收

启动前端后必须已经存在完整骨架：

```text
Dashboard

Servers

GPUs

Model Library

Installed Models

Deployments

Downloads

API Endpoints

Activity

Settings
```

允许使用 Mock Data。

视觉必须统一。

---

# 104. Phase 2 验收

连接：

```text
lab-server-01

RTX4090 × 4
```

平台能够显示：

```text
Online

GPU 0
GPU 1
GPU 2
GPU 3

Utilization

VRAM

Temperature

Power
```

---

# 105. 多 Server 验收

同时存在：

```text
lab-server-01

lab-server-02

cloud-server-01
```

Dashboard 能统一看到。

无需关心服务器实际位于：

```text
实验室内网

公网

云厂商
```

---

# 106. Model Download 验收

搜索：

```text
Qwen/Qwen3-8B
```

选择：

```text
lab-server-01
```

点击：

```text
Download
```

看到：

```text
Downloading

Progress

Speed
```

完成后：

```text
Installed
```

---

# 107. Deployment 验收

选择：

```text
Qwen3-8B

lab-server-01

GPU 2

vLLM

Port 8001
```

点击：

```text
Deploy
```

系统启动服务。

状态变成：

```text
Running
```

返回：

```text
http://server:8001/v1
```

---

# 108. Stop 验收

点击：

```text
Stop
```

模型 Container 停止。

GPU 显存释放。

GPU 页面更新：

```text
Available
```

---

# 109. API 验收

点击：

```text
Test API
```

发送：

```text
Hello
```

调用：

```text
/v1/chat/completions
```

成功获得返回。

---

# 110. 第一版成功标准

完整流程：

```text
Open Console
      ↓
View Servers
      ↓
View GPUs
      ↓
Find Available GPU
      ↓
View Installed Models
      ↓
Search Hugging Face
      ↓
Download Model
      ↓
Select Server
      ↓
Select GPU
      ↓
Deploy with vLLM
      ↓
View Logs
      ↓
Get Endpoint
      ↓
Test API
      ↓
Stop Deployment
      ↓
GPU Becomes Available
```

如果以上流程稳定工作，则 MVP 成功。

---

# 111. 第二阶段扩展方向

未来可以增加：

```text
SGLang

Unified API Gateway

Model Load Balancing

Automatic Model Deployment

Shared Model Storage

Object Storage

Tailscale / Headscale

Prometheus

Grafana

MLflow

Weights & Biases

Training Jobs

JupyterLab

VS Code Server
```

---

# 112. 第三阶段扩展方向

规模扩大后再考虑：

```text
Slurm

Kubernetes

HAMi

Volcano

Kueue

GPU Quota

Fair Share

Priority

Job Queue

Multi-user Scheduling
```

---

# 113. 长期产品形态

最终希望成为：

```text
AI Infrastructure Control Center

Infrastructure
├── Server
├── GPU
├── Storage
└── Cloud

Models
├── Model Library
├── Local Models
├── Download
└── Registry

Runtime
├── vLLM
├── SGLang
├── Ollama
└── Custom Runtime

Service
├── Endpoint
├── API Gateway
└── Routing

Observability
├── Metrics
├── Logs
├── Alert
└── Activity
```

最终定位：

> 一个面向个人研究者、AI 开发者和科研实验室的轻量级 GPU、服务器、模型及推理服务统一控制平台。