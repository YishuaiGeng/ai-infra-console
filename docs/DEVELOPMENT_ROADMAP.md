# AI Infra Console Development Roadmap

This roadmap summarizes the staged implementation plan. The source product requirement is [`AI Infrastructure Control Center.md`](../AI%20Infrastructure%20Control%20Center.md).

## Current Phase Status

| Phase | Scope | Status | Notes |
| --- | --- | --- | --- |
| 0 | UI Foundation | Complete | Mock-backed console, layout, routes, shared components, loading/empty/error states |
| 1 | Backend Foundation | Complete | FastAPI, SQLAlchemy, Alembic, PostgreSQL/Redis/RQ, auth, audit basics |
| 2 | Agent | Complete | Outbound Agent registration, heartbeat, host/GPU/process collection |
| 3 | Server Integration | Complete | Real server/GPU APIs, Web BFF, SSE invalidation, dashboard integration |
| 4 | Model Inventory | Complete | Read-only model directory scanning and installed-model views |
| 5 | Model Download | Complete | Provider search, download/cancel/retry/delete workflows through Agent tasks |
| 6 | Deployment | Complete | vLLM Docker placement, lifecycle, health, bounded logs, reconciliation |
| 7 | API Endpoints | In progress | Real endpoint listing and Central-mediated chat-completions test are implemented |
| 8 | Monitoring Polish | In progress | Real Activity audit view is implemented; historical metrics and notifications remain |
| 9 | UI Polish | Planned | Accessibility, responsive polish, visual consistency, final docs cleanup |

## Product Workflow

```text
Open Console
  -> View Servers
  -> View GPUs
  -> Find Available GPU
  -> View Installed Models
  -> Search Hugging Face / ModelScope
  -> Download Model
  -> Select Server and GPU
  -> Deploy with vLLM
  -> View Logs and Health
  -> Copy or Test OpenAI-compatible Endpoint
  -> Stop/Delete Deployment
  -> GPU Becomes Available
```

## Fixed Engineering Boundaries

- The Agent remains outbound-only; do not add inbound Agent listeners.
- Do not add generic remote shell, SSH terminal, `/exec`, `/shell`, `/command`, arbitrary script, or arbitrary container APIs.
- Mutating actions must stay allowlisted, typed, audited, and role-protected.
- Real credentials, private addresses, server notes, provider tokens, and registration tokens must not enter Git.
- Backup hosts listed in [`DEPLOYMENT_TARGETS.md`](./DEPLOYMENT_TARGETS.md) must remain read-only unless the maintainer explicitly changes the policy.

## Phase Details

Detailed phase records:

- [Phase 1: Backend Foundation](./phases/PHASE_1_BACKEND_FOUNDATION.md)
- [Phase 2: Agent](./phases/PHASE_2_AGENT.md)
- [Phase 3: Server Integration](./phases/PHASE_3_SERVER_INTEGRATION.md)
- [Phase 4: Model Inventory](./phases/PHASE_4_MODEL_INVENTORY.md)
- [Phase 5: Model Download](./phases/PHASE_5_MODEL_DOWNLOAD.md)
- [Phase 6: Deployment](./phases/PHASE_6_DEPLOYMENT.md)

Phase 7 through Phase 9 should use the same pattern: write code-level acceptance criteria, implement the smallest real workflow that satisfies them, run Web/API/Agent/security gates, then update README and phase evidence.

## Remaining Work

Phase 7:

- Add more endpoint-level health and model metadata if needed by external clients.
- Expand browser verification for live endpoint test failures, long responses, and unavailable runtimes.

Phase 8:

- Add historical GPU/server metrics persistence and chart views without making Dashboard chart-heavy.
- Add notifications for critical events such as offline servers, high GPU temperature, low disk space, download failure, and deployment failure.
- Define metrics retention settings and cleanup jobs.

Phase 9:

- Finish keyboard/focus checks across dialogs, menus, tables, and logs.
- Sweep desktop/tablet/mobile overflow and long text behavior.
- Remove remaining mock dependencies from production-facing pages where real APIs exist.
- Run full Web/API/Agent/security gates and update documentation with final evidence.
