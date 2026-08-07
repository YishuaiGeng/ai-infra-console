# AI Infra Console

[![Phase](https://img.shields.io/badge/phase-0%20UI%20Foundation-2563eb)](./docs/DEVELOPMENT_ROADMAP.md)
[![Next.js](https://img.shields.io/badge/Next.js-16-black)](https://nextjs.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-0f766e)](./LICENSE)

English | [简体中文](./docs/README.zh-CN.md)

AI Infra Console is a lightweight control plane for AI servers, NVIDIA GPUs, model files, inference deployments, downloads, and OpenAI-compatible endpoints. It is designed for individual researchers, AI developers, and small labs that need a focused infrastructure view without adopting a full cluster platform.

![AI Infra Console dashboard](./docs/assets/dashboard-dark.png)

> [!IMPORTANT]
> The Phase 0 web UI still uses one local mock dataset and is not yet connected to the backend. Phase 1 Central API work is in progress, including authentication, schema migrations, Redis, and a worker. There is no server Agent, real hardware integration, model download, Docker lifecycle action, or vLLM deployment yet.

## Phase 0 UI coverage (mock-backed)

- GPU-first dashboard that surfaces available devices before secondary metrics.
- Server inventory and server details with host, GPU, model, and process views.
- GPU table/card views with server, model, status, and availability filters.
- Hugging Face and ModelScope model library with client-side validated download forms.
- Installed model locations across multiple servers.
- Deployment inventory, configuration, lifecycle controls, metrics, and terminal-style logs.
- Simulated download progress, a mock API test dialog with a synthetic response, activity logs, and system settings.
- Light, dark, and system themes with responsive desktop, tablet, and basic mobile layouts.
- Shared mock data across every page so totals and relationships remain consistent.

## Phase 1 backend (in progress)

- FastAPI application with `/api/v1`, liveness, readiness, and OpenAPI documentation.
- PostgreSQL-oriented SQLAlchemy schema with 15 tables and an Alembic migration.
- Username/password login, Argon2 hashes, short-lived JWT bearer tokens, and Admin/Viewer roles.
- Stable API error envelope, structured logs, propagated request IDs, and authentication audit records.
- Redis-backed RQ worker with a fixed task registry and no arbitrary command execution path.
- Five-service Compose definition for web, API, PostgreSQL, Redis, and worker.
- Automated backend lint, type checking, migration, authentication, error, health, and worker tests.

## Product workflow

This is the target product workflow. Phase 0 only simulates its interactions in the browser.

```text
View servers and GPUs
  -> Find available GPU capacity
  -> Inspect or download a model
  -> Choose server and GPU placement
  -> Deploy with vLLM or Ollama
  -> Inspect logs and health
  -> Copy or test the OpenAI-compatible endpoint
  -> Stop the deployment and release GPU capacity
```

## Pages

| Area | Routes |
| --- | --- |
| Overview | `/dashboard` |
| Infrastructure | `/servers`, `/servers/[id]`, `/gpus` |
| Models | `/models/library`, `/models`, `/deployments`, `/deployments/[id]`, `/downloads` |
| Services | `/apis` |
| System | `/activity`, `/settings` |

The root route `/` redirects to `/dashboard`. Mock-backed examples for dynamic routes are `/servers/srv-lab-4090-01` and `/deployments/dep-qwen32`.

## Tech stack

- Next.js 16, React 19, and TypeScript
- Tailwind CSS 4 and shadcn/ui with Base UI primitives
- TanStack Query and TanStack Table 9
- React Hook Form and Zod
- Zustand, Recharts, Lucide React, next-themes, and Sonner
- FastAPI, SQLAlchemy, Pydantic, Alembic, PostgreSQL, Redis, and RQ
- uv, Ruff, mypy, and pytest

## Quick start

Requirements:

- Node.js 20.9 or newer
- npm 10 or newer
- Python 3.11 or newer and uv 0.9 or newer for backend development
- Docker Engine with Compose v2 for the complete stack

From the repository root:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). If that port is already occupied, Next.js will report the selected local URL.

For the complete Compose stack, configure `.env` from `.env.example`, then run `docker compose up -d --build`. See [Backend Development](./docs/BACKEND_DEVELOPMENT.md).

## Commands

| Command | Purpose |
| --- | --- |
| `npm run dev` | Start the web console in development mode |
| `npm run lint` | Run ESLint across the web workspace |
| `npm run typecheck` | Run TypeScript without emitting files |
| `npm run build` | Create the production Next.js build |
| `npm run start` | Serve a completed production build |
| `npm run check:api` | Run API lint, type checking, and tests |
| `npm run api:smoke` | Run a temporary API, Redis, auth, and worker smoke test |
| `npm run check` | Run all web and API checks |
| `docker compose up -d --build` | Start the five-service local stack |

## Repository layout

```text
ai-infra-console/
├── apps/
│   ├── api/                 # FastAPI, migrations, worker, and tests
│   └── web/                 # Next.js application
│       └── src/
│           ├── app/         # App Router pages and layouts
│           ├── components/  # UI primitives and domain components
│           ├── config/      # Navigation and product configuration
│           ├── features/    # Page-level feature composition
│           ├── mocks/       # Single mock data source
│           ├── stores/      # Client UI state
│           └── types/       # Shared domain types
├── compose.yaml
├── docs/                    # Roadmap, phase plans, and operations docs
├── CONTRIBUTING.md
├── SECURITY.md
└── package.json             # npm workspace entry point
```

The monorepo will add `apps/agent` during Phase 2 after the Phase 1 gate passes.

## Roadmap

| Phase | Scope | Status |
| --- | --- | --- |
| 0 | UI Foundation | Complete |
| 1 | Central API, database, Redis, authentication | In progress |
| 2 | Agent registration, heartbeat, hardware collection | Planned |
| 3 | Real server and GPU integration | Planned |
| 4 | Model inventory and directory scanning | Planned |
| 5 | Hugging Face and ModelScope downloads | Planned |
| 6 | Docker and vLLM deployment lifecycle | Planned |
| 7 | OpenAI-compatible API testing | Planned |
| 8 | Historical metrics and notifications | Planned |
| 9 | Accessibility and UI polish | Planned |

Development intentionally stops at the end of each phase for review. See the [detailed development roadmap](./docs/DEVELOPMENT_ROADMAP.md) and the [product requirements](./AI%20Infrastructure%20Control%20Center.md).

## Security model

AI Infra Console is intended to control sensitive infrastructure. Future Agent capabilities must expose explicit allowlisted operations only. Arbitrary remote shell, SSH terminal, `/exec`, `/shell`, and `/command` APIs are outside the project boundary.

Never commit real host records, credentials, registration tokens, model provider tokens, or private addresses. The local `服务器资料/` directory is explicitly ignored for this reason. Review [SECURITY.md](./SECURITY.md) before implementing backend or Agent features.

## Contributing

Issues and focused pull requests are welcome. Read [CONTRIBUTING.md](./CONTRIBUTING.md), keep changes within the active roadmap phase, and include screenshots for visible UI changes.

## License

Licensed under the [Apache License 2.0](./LICENSE).
