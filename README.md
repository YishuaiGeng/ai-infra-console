# AI Infra Console

<p align="center">
  <img src="apps/web/public/brand/logo.png" alt="AI Infra Console" width="560" />
</p>

<p align="center">
  <a href="./docs/DEVELOPMENT_ROADMAP.md"><img alt="Phase" src="https://img.shields.io/badge/phase-9%20complete-16a34a" /></a>
  <a href="https://nextjs.org/"><img alt="Next.js" src="https://img.shields.io/badge/Next.js-16-black" /></a>
  <a href="./LICENSE"><img alt="License" src="https://img.shields.io/badge/license-Apache--2.0-0f766e" /></a>
</p>

AI Infra Console is a lightweight control plane for personal and lab AI infrastructure. It helps operators monitor GPU servers, inspect NVIDIA GPU utilization, manage local model files, run model downloads, control vLLM deployments, test OpenAI-compatible endpoints, and review audit activity from a single web console.

This project is designed for individual researchers, AI developers, and small labs that need a focused infrastructure console without adopting Kubernetes, Slurm, or a full cluster platform.

![AI Infra Console dashboard](./docs/assets/dashboard-dark.png)

> Private server credentials, host notes, API tokens, provider tokens, registration tokens, and the local `服务器资料/` directory must not be committed. Keep production secrets in environment files or a dedicated secret manager.

## Highlights

- GPU-first dashboard for server health, available GPU capacity, model counts, deployment health, and recent resource trends.
- Authenticated Central API with stable error envelopes, request IDs, JWT sessions, Admin/Viewer roles, and audit logs.
- Outbound-only Agent for host metrics, NVIDIA GPU telemetry, GPU processes, Docker/Ollama capability, model inventory, model tasks, and deployment runtime reporting.
- Model inventory for Safetensors, PyTorch bin, GGUF, Hugging Face cache layouts, and local Ollama discovery.
- Hugging Face and ModelScope catalog search plus Agent-executed download/cancel/retry/delete workflows.
- Safe vLLM deployment lifecycle with typed create/start/stop/restart/retry/delete actions, deterministic ports, exact GPU placement, health, and bounded logs.
- OpenAI-compatible endpoint listing with copy actions, Agent health metadata, and Central-mediated `/v1/chat/completions` testing.
- Monitoring history for CPU, RAM, disk, network, GPU utilization, VRAM, temperature, and power samples with retention cleanup.
- Derived notifications for offline servers, low disk, high GPU temperature, near-full VRAM, failed downloads, and failed deployments.
- Web BFF routes that keep API bearer tokens out of browser storage by using Secure HttpOnly session cookies.
- Security guardrails against generic remote shell, arbitrary Docker control, unsafe model paths, and backup-host mutation.

## Current Status

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | UI foundation | Complete |
| 1 | Central API, database, Redis, authentication | Complete |
| 2 | Outbound Agent registration, heartbeat, hardware collection | Complete |
| 3 | Real server and GPU integration | Complete |
| 4 | Model inventory and directory scanning | Complete |
| 5 | Hugging Face and ModelScope downloads | Complete |
| 6 | Docker and vLLM deployment lifecycle | Complete |
| 7 | OpenAI-compatible endpoint listing, health, and test dialog | Complete |
| 8 | Activity, metrics history, and notifications | Complete |
| 9 | Accessibility and UI polish | Complete |

## Architecture

```text
Browser
  -> Next.js Web Console and BFF
  -> FastAPI Central API
  -> PostgreSQL, Redis, RQ
  <- Outbound Python Agent heartbeats and task polling
  <- Server metrics, GPU telemetry, inventory, downloads, deployments, logs
```

The Agent is outbound-only. Central never opens an inbound shell or SSH tunnel to managed servers. Mutating operations are typed, allowlisted, audited, and role-protected.

## Pages

| Area | Routes |
| --- | --- |
| Overview | `/dashboard` |
| Infrastructure | `/servers`, `/servers/[id]`, `/gpus` |
| Models | `/models/library`, `/models`, `/deployments`, `/deployments/[id]`, `/downloads` |
| Services | `/apis` |
| System | `/activity`, `/settings` |

The root route `/` redirects to `/dashboard`.

## Tech Stack

- Next.js 16, React 19, TypeScript, Tailwind CSS 4, shadcn-style components, Base UI, Lucide React
- TanStack Query, TanStack Table, React Hook Form, Zod, Zustand, Recharts, Sonner
- FastAPI, SQLAlchemy, Pydantic, Alembic, PostgreSQL, Redis, RQ
- Python Agent with psutil, NVIDIA Management Library, Docker SDK, HTTPX
- uv, Ruff, mypy, pytest, Vitest, ESLint

## Quick Start

Requirements:

- Node.js 20.9 or newer
- npm 10 or newer
- Python 3.11 or newer
- uv 0.9 or newer for API/Agent development
- Docker Engine with Compose v2 for the complete local stack

Install dependencies and start the web console:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). If port 3000 is occupied, Next.js prints the selected URL.

Run the full local stack:

```bash
cp .env.example .env
docker compose up -d --build
```

Review and adjust `.env` before using real servers.

## Configuration

Important configuration areas:

- `AI_INFRA_DATABASE_URL`, `AI_INFRA_REDIS_URL`: Central persistence and queue backends.
- `AI_INFRA_JWT_SECRET`: Central session signing secret.
- `AI_INFRA_MUTABLE_SERVER_NAMES`: explicit allowlist for servers that may receive model/deployment mutations.
- Agent model roots and deployment opt-in settings: required before an Agent can download models or run managed vLLM containers.

Do not put real credentials, private host records, provider tokens, registration tokens, or local server notes into Git.

## Commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the Web console in development mode |
| `npm run build` | Build the production Web app |
| `npm run lint` | Run Web ESLint |
| `npm run typecheck` | Run TypeScript checks |
| `npm run test:web` | Run Web tests |
| `npm run check:api` | Run API lint, type checking, and tests |
| `npm run check:agent` | Run Agent lint, type checking, and tests |
| `npm run security:scan` | Scan for tracked secrets and unsafe command interfaces |
| `npm run check` | Run Web, API, Agent, and security gates |
| `docker compose up -d --build` | Start the local Compose stack |

## Repository Layout

```text
ai-infra-console/
|-- apps/
|   |-- api/       # FastAPI, migrations, worker, tests
|   |-- agent/     # Outbound Agent, collectors, runtime supervisors, tests
|   `-- web/       # Next.js console and BFF routes
|-- deploy/        # systemd and deployment templates
|-- docs/          # roadmap, phase records, operations docs
|-- scripts/       # security and smoke scripts
|-- compose.yaml
|-- CONTRIBUTING.md
|-- SECURITY.md
`-- package.json
```

## Security Model

AI Infra Console controls sensitive infrastructure. The project intentionally does not provide generic remote shell, SSH terminal, `/exec`, `/shell`, `/command`, arbitrary image, arbitrary volume, or arbitrary host-path mutation APIs.

Agent capabilities are explicit and allowlisted. Deployment control is limited to exactly owned, labeled containers and configured mutable hosts. Backup or read-only hosts must stay outside mutation allowlists.

Read [SECURITY.md](./SECURITY.md) before changing backend, Agent, deployment, or filesystem mutation code.

## Documentation

- [Chinese README](./docs/README.zh-CN.md)
- [Development roadmap](./docs/DEVELOPMENT_ROADMAP.md)
- [Product requirements](./AI%20Infrastructure%20Control%20Center.md)
- [Backend development](./docs/BACKEND_DEVELOPMENT.md)
- [Agent operations](./docs/AGENT_OPERATIONS.md)
- [Deployment targets](./docs/DEPLOYMENT_TARGETS.md)
- [Phase 7 API endpoints](./docs/phases/PHASE_7_API_ENDPOINTS.md)
- [Phase 8 monitoring polish](./docs/phases/PHASE_8_MONITORING_POLISH.md)
- [Phase 9 UI polish](./docs/phases/PHASE_9_UI_POLISH.md)

## License

Licensed under the [Apache License 2.0](./LICENSE).
