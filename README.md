# AI Infra Console

<p align="center">
  <img src="apps/web/public/brand/logo.png" alt="AI Infra Console" width="560" />
</p>

<p align="center">
  <a href="https://nextjs.org/"><img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-black" /></a>
  <a href="https://fastapi.tiangolo.com/"><img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-0.115-009688" /></a>
  <a href="./LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-0f766e" /></a>
</p>

AI Infra Console is a self-hosted control plane for AI infrastructure. It gives individuals and small labs a focused console for monitoring GPU servers, tracking resource usage, managing local model files, downloading models, running vLLM deployments, testing OpenAI-compatible endpoints, and reviewing audit activity.

The project is intentionally smaller than a cluster platform. It is built for operators who manage their own servers and need a practical, security-conscious view of GPU capacity, model storage, and inference runtimes.

![AI Infra Console dashboard](./docs/assets/dashboard-dark.png)

## Features

- GPU-first dashboard with server health, GPU allocation, model counts, deployment health, and 24-hour resource trends.
- Authenticated Central API with JWT sessions, Admin/Viewer roles, request IDs, stable error envelopes, and audit logs.
- Outbound-only Python Agent for host metrics, NVIDIA GPU telemetry, GPU processes, Docker/Ollama capability, model inventory, downloads, deployment runtime state, health, and logs.
- Model inventory for Safetensors, PyTorch bin, GGUF, Hugging Face cache layouts, and local Ollama discovery.
- Hugging Face and ModelScope catalog search with Agent-executed download, cancel, retry, and delete workflows.
- Safe vLLM lifecycle management: create, start, stop, restart, retry, delete, deterministic ports, exact GPU placement, health checks, and bounded logs.
- OpenAI-compatible endpoint listing with copy actions, health metadata, and Central-mediated `/v1/chat/completions` testing.
- Monitoring history for CPU, RAM, disk, network, GPU utilization, VRAM, temperature, and power samples.
- Derived notifications for offline servers, low disk, high GPU temperature, near-full VRAM, failed downloads, and failed deployments.
- Same-origin Web BFF routes using Secure HttpOnly cookies so API bearer tokens are not stored in browser storage.

## Architecture

```text
Browser
  -> Next.js Web Console and BFF
  -> FastAPI Central API
  -> PostgreSQL, Redis, RQ
  <- Outbound Python Agent polling and heartbeats
  <- Server metrics, GPU telemetry, inventory, downloads, deployments, logs
```

The Agent is outbound-only. Central does not open inbound SSH, shell, or Docker sockets on managed servers. Mutating operations are typed, allowlisted, audited, and role-protected.

## Requirements

- Linux server recommended for deployment
- Docker Engine with Compose v2
- Node.js 20.9+ and npm 10+ for Web development
- Python 3.11+ and uv 0.9+ for API/Agent development
- NVIDIA drivers and Docker GPU runtime on servers that will run vLLM workloads

## Quick Start

```bash
git clone https://github.com/YishuaiGeng/ai-infra-console.git
cd ai-infra-console
cp .env.example .env
```

Edit `.env` before first start:

- Set `AI_INFRA_JWT_SECRET` to a unique value with at least 32 characters.
- Set `AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD` to the first administrator password.
- Set `AI_INFRA_POSTGRES_PASSWORD` to a strong database password.
- Set `AI_INFRA_MUTABLE_SERVER_NAMES` to the exact registered server names that Central may mutate.
- Keep backup or inventory-only servers out of `AI_INFRA_MUTABLE_SERVER_NAMES`.

Start the stack:

```bash
docker compose up -d --build
```

Open the Web console:

```text
http://<server-host>:3000
```

The first administrator account is created from:

```text
AI_INFRA_BOOTSTRAP_ADMIN_USERNAME
AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD
```

## Server Deployment

For a persistent server installation:

1. Clone the repository on the Central host.
2. Copy `.env.example` to `.env` and replace every placeholder.
3. Set DNS and TLS in front of the Web/API service using your reverse proxy.
4. Start Central with `docker compose up -d --build`.
5. Create or retrieve an Agent registration token from the console.
6. Install the Agent on each managed server using the templates in `deploy/systemd/`.
7. Configure each Agent with its Central URL, registration token, model directories, and deployment opt-in settings.
8. Enable model mutations or deployments only on servers that are intentionally allowlisted.

The Compose stack starts PostgreSQL, Redis, the Central API, the worker, and the Web console. The Agent can run separately on each managed server.

## Agent Configuration

The Agent reads an environment file like `deploy/systemd/agent.env.example`.

Important settings:

- `AI_INFRA_AGENT_CENTRAL_URL`: public Central URL reachable from the managed server.
- `AI_INFRA_AGENT_TOKEN`: one-time registration token.
- `AI_INFRA_AGENT_ALLOWED_MODEL_DIRECTORIES`: local model roots the Agent may scan.
- `AI_INFRA_AGENT_DEFAULT_MODEL_DIRECTORY`: default target for model downloads.
- `AI_INFRA_AGENT_ENABLE_MODEL_MUTATIONS`: enables download/delete tasks on this server.
- `AI_INFRA_AGENT_ENABLE_DEPLOYMENTS`: enables managed vLLM container lifecycle on this server.
- `AI_INFRA_AGENT_VLLM_IMAGE`: reviewed and pinned vLLM image reference for deployment mode.

Agent deployment and hardening details are in [Agent operations](./docs/AGENT_OPERATIONS.md).

## Security Model

AI Infra Console controls sensitive infrastructure and intentionally avoids generic remote execution features.

The project must not add:

- Generic remote shell or SSH terminal
- `/exec`, `/shell`, `/command`, or arbitrary script APIs
- Arbitrary Docker image, volume, or host-path mutation APIs
- Inbound Agent listeners
- Backup-host mutation by default

Never commit private host records, server credentials, registration tokens, provider tokens, API tokens, `.env`, or the local `服务器资料/` directory.

Read [SECURITY.md](./SECURITY.md) before changing backend, Agent, deployment, or filesystem mutation code.

## Development

Install dependencies:

```bash
npm install
```

Run the Web console in development mode:

```bash
npm run dev
```

Run the full verification gate:

```bash
npm run check
```

Common commands:

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Web console in development mode |
| `npm run build` | Build the production Web app |
| `npm run check:web` | Run Web lint, type checking, tests, and build |
| `npm run check:api` | Run API lint, type checking, and tests |
| `npm run check:agent` | Run Agent lint, type checking, and tests |
| `npm run security:scan` | Scan tracked files for secrets and unsafe command surfaces |
| `npm run check` | Run all Web, API, Agent, and security checks |
| `docker compose up -d --build` | Start the complete local stack |

## Repository Layout

```text
ai-infra-console/
|-- apps/
|   |-- api/       # FastAPI Central API, migrations, worker, tests
|   |-- agent/     # Outbound Agent, collectors, runtime supervisors, tests
|   `-- web/       # Next.js console and same-origin BFF routes
|-- deploy/        # systemd and deployment templates
|-- docs/          # architecture, roadmap, operations, and phase records
|-- scripts/       # security and smoke scripts
|-- compose.yaml
|-- CONTRIBUTING.md
|-- SECURITY.md
`-- package.json
```

## Documentation

- [Chinese README](./docs/README.zh-CN.md)
- [Backend development](./docs/BACKEND_DEVELOPMENT.md)
- [Agent operations](./docs/AGENT_OPERATIONS.md)
- [Deployment targets](./docs/DEPLOYMENT_TARGETS.md)
- [Development roadmap](./docs/DEVELOPMENT_ROADMAP.md)
- [Product requirements](./AI%20Infrastructure%20Control%20Center.md)

## License

Licensed under the [Apache License 2.0](./LICENSE).
