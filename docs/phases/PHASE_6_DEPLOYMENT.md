# Phase 6: Deployment

## Status

- State: Code-level plan established on 2026-08-08; implementation not started
- Entry gate: Phase 5 complete, including GitHub Actions run [`31221477457`](https://github.com/YishuaiGeng/ai-infra-console/actions/runs/31221477457)
- Exit gate: every acceptance item in this document has direct automated, browser, runtime, or clean Linux CI evidence
- Scope boundary: managed vLLM Docker deployment, placement, lifecycle, health, and logs only; OpenAI-compatible request testing remains Phase 7
- Host boundary: deployment mutation may be enabled only for `xiao-pro6000`; model storage may remain on `xiao-cpu` or `xiao-pro6000`, but a runtime uses a model file local to its selected server. Do not modify `asus-2024` or `asus-4090`

## Technical decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Remote execution | Add typed deployment-operation DTOs for create, start, stop, restart, and delete; never add a generic command, shell, script, executable, or arbitrary container API | Keeps the Agent outbound-only without creating a remote-code-execution surface |
| Host opt-in | Central reuses the mutable-server allowlist and Agent adds a separate deployment opt-in | Model writes and container control are distinct privileges; backup hosts remain read-only |
| Runtime scope | Phase 6 manages vLLM only. Existing Ollama discovery stays read-only and is not presented as a deployable backend | Matches the roadmap and avoids pretending an unmanaged Ollama process has lifecycle ownership |
| Container ownership | Agent manages only containers with exact project/deployment/generation labels and a deterministic name; it never mutates unlabeled or foreign containers | Prevents accidental control of host workloads |
| Image policy | Agent uses an operator-configured allowlist with an immutable image digest in production; users cannot submit an image or entrypoint | Prevents image substitution and tag drift |
| Arguments | Central stores typed vLLM fields. Extra arguments are tokenized without a shell, bounded, checked against an allowlist, and cannot override model, host, port, GPU, image, volume, or security settings | Preserves advanced vLLM tuning without arbitrary process execution |
| Model mount | Agent revalidates the selected inventory path under one exact local model allowlist root and mounts it read-only at a fixed container path | Central state cannot mount arbitrary host files |
| Placement | Manual placement validates exact same-server GPU IDs. Automatic placement ranks fresh same-server GPUs by free VRAM descending, utilization ascending, then index; it never crosses servers | Implements deterministic basic scheduling while keeping model locality explicit |
| GPU conflicts | `DeploymentGPU` records placement; only starting/started states consume capacity. Start rechecks active allocations and Agent rechecks actual device/runtime state | Stop releases runtime memory while stale plans cannot silently overcommit a GPU |
| Port policy | A configured deployment reserves one server port until deletion. Central checks database conflicts and Agent checks Docker/socket conflicts immediately before start | Gives deterministic URLs and catches host-local conflicts Central cannot see |
| State and leasing | A deployment stores desired/observed state while a separate durable operation row stores action, attempt, lease digest, generation, timestamps, and safe error fields | Lifecycle retries and Agent restarts remain auditable and stale reporters cannot overwrite new work |
| Reconciliation | Agent periodically reports only project-labeled containers, health, and bounded log cursors; Central reconciles missing/restarted containers after Agent restart | Runtime state remains accurate without inbound access to the host |
| Logs and health | Agent probes loopback vLLM endpoints and reads bounded Docker logs, sanitizes control sequences, then posts outbound. Central exposes authenticated read APIs and SSE invalidation | Central never needs direct network or Docker access to managed servers |
| Container hardening | Use no privileged mode, no Docker socket mount, dropped capabilities, bounded tmpfs/shm, read-only model mount, explicit published port, and no host PID namespace | Narrows the impact of model/runtime code, including explicit trust-remote-code use |
| Tests | Unit tests inject a fake Docker client; Compose uses a tiny test-only runtime adapter that is rejected in production | Proves the full protocol without GPU hardware, a Docker socket, or a multi-gigabyte vLLM image in CI |

## Code-level tasks

### Phase 6.1 Persistence and lifecycle state machine

- [ ] Add an Alembic migration that extends deployments with requester, desired state, generation, health, last reconciliation, safe error, and lifecycle timestamps.
- [ ] Add a dedicated deployment-operation table for create/start/stop/restart/delete action, status, attempt, lease digest/expiry, generation, request/audit IDs, and terminal outcome.
- [ ] Add constraints and indexes for valid ports, bounded generations/attempts, deterministic server/status ordering, one active operation per deployment, and one reserved server/port pair.
- [ ] Migrate existing rows conservatively by deriving desired state from status and preserving existing configuration JSON.
- [ ] Implement pure transition helpers for queue, claim, lease renew/expiry, start, success, failure, no-op, retry, reconciliation, and stale-generation rejection.
- [ ] Keep lease tokens hashed and lifecycle errors sanitized into bounded code/message fields.

Evidence:

- Migration and service tests cover upgrade/downgrade/upgrade, every legal action/state pair, illegal transitions, idempotency, stale leases/generations, retry, and rollback.

### Phase 6.2 Placement and configuration planning

- [ ] Define strict typed create/config schemas for deployment name, model-file ID, placement mode, GPU IDs, port, tensor parallel size, GPU memory utilization, max model length, dtype, trust remote code, and bounded extra arguments.
- [ ] Require a discovered local model file on an online mutable server with an active Agent, available model root, Docker capability, and deployment opt-in.
- [ ] Reject missing/stale/error model files, active deletion tasks, remote-only model locations, CPU-only servers, stale GPUs, and unsupported formats/backends.
- [ ] Implement deterministic manual placement validation for same-server GPU IDs and tensor-parallel cardinality.
- [ ] Implement deterministic automatic placement using fresh free VRAM, utilization, active deployment allocation, and GPU index without cross-server scheduling.
- [ ] Reserve the port and chosen placement transactionally; reject name, port, active-operation, and active-GPU conflicts with stable API errors.
- [ ] Tokenize and validate extra arguments as a bounded argv list with an explicit vLLM allowlist and managed-flag denial.

Evidence:

- Planner tests cover ranking ties, stale/missing telemetry, manual ordering, tensor parallel mismatch, GPU conflict, port conflict, model locality, active deletion, unsupported format, extra-argument injection, and backup-host denial.

### Phase 6.3 Authenticated deployment APIs

- [ ] Add authenticated deployment target/options, list, detail, and operation-status APIs with deterministic filters and ordering for Admin and Viewer.
- [ ] Add Admin-only create, start, stop, restart, retry, and exact-confirm delete APIs.
- [ ] Make repeated lifecycle requests idempotent: return the active operation, treat already desired terminal state as a no-op, and never enqueue conflicting actions.
- [ ] Expose configuration, selected GPUs, desired/observed state, health, endpoint, uptime, safe errors, and current operation without leaking Agent credentials or Docker internals.
- [ ] Add bounded authenticated log reads with `after`, `limit`, and search filters.
- [ ] Record audit rows and publish versioned deployment/log/health SSE events only after commit.

Evidence:

- API tests cover anonymous/Admin/Viewer roles, every lifecycle action, idempotency, conflicts, exact deletion confirmation, filtering, error mapping, logs, SSE, and secret-free responses.

### Phase 6.4 Outbound Agent deployment protocol

- [ ] Add a server-scoped deployment-operation claim endpoint returning a discriminated typed command and no free-form executable/image/volume field.
- [ ] Add lease-authenticated progress/terminal endpoints scoped to the authenticated Agent server and current deployment generation.
- [ ] Extend `CentralClient` with typed deployment claim/report, runtime reconciliation, health, and bounded log-batch methods.
- [ ] Add a deployment supervisor that executes at most one lifecycle operation while heartbeats and model-task supervision continue.
- [ ] Recover expired operations after Agent restart and reject reports from a previous lease or generation.
- [ ] Add periodic project-container reconciliation even when no lifecycle operation is queued.

Evidence:

- API/Agent protocol tests cover cross-server denial, lease mismatch, one-at-a-time claim, restart reclaim, stale generation, report retry, heartbeat continuity, and foreign-container omission.

### Phase 6.5 Safe Agent Docker execution

- [ ] Add Agent settings for deployment opt-in, image allowlist/digest, operation/reconciliation intervals, startup/stop timeouts, health path, log bounds, and test-only runtime adapter.
- [ ] Reject deployment enablement without model roots, verified production HTTPS, Docker availability, and an immutable production image reference.
- [ ] Revalidate model root/path containment, symlink policy, expected model identity, selected GPU indices/UUIDs, and port range locally before container creation.
- [ ] Build the vLLM argv only from typed fields and validated extra tokens; never invoke a shell.
- [ ] Create a deterministic project-labeled container with read-only model mount, `CUDA_VISIBLE_DEVICES`, Docker GPU device requests, published port, bounded resources, and hardened defaults.
- [ ] Refuse name/port conflicts, foreign containers, label mismatches, stale generations, missing GPUs, unavailable Docker, and model-path replacement.
- [ ] Implement typed start, graceful stop with bounded kill fallback, restart, and delete only for the exactly owned container.
- [ ] Make missing owned containers idempotent for stop/delete and never prune images, volumes, networks, or unrelated containers.

Evidence:

- Agent tests use fake Docker/socket/filesystem adapters for argv, labels, mounts, GPU requests, hardening, conflicts, timeouts, missing containers, foreign labels, traversal, symlinks, disabled mode, and error redaction.

### Phase 6.6 Reconciliation, health, and logs

- [ ] Discover only exact project-labeled containers and report deployment ID, generation, container identity digest, Docker state, exit code, and bounded timestamps.
- [ ] Map Docker states to stable deployment states and reconcile running, stopped, exited, missing, and replaced containers without trusting arbitrary labels.
- [ ] Probe the local vLLM health endpoint with a short timeout and report healthy/degraded/unhealthy/unknown state and latency.
- [ ] Read logs only from the owned container using bounded line/byte/time cursors; strip ANSI/control characters and never return Docker environment or inspect payloads.
- [ ] Persist a capped per-deployment log window with monotonic sequence IDs and bounded retention cleanup.
- [ ] Publish deployment, GPU allocation, health, and log SSE events so Dashboard, GPUs, list, and detail views converge without reload.

Evidence:

- Reconciliation tests cover Agent/container restart, missing and replaced containers, nonzero exit, health transitions, duplicate/out-of-order logs, retention, ANSI/control stripping, and SSE ordering.

### Phase 6.7 Web data layer and workflows

- [ ] Add same-origin HttpOnly-session BFF handlers for deployment targets, list/detail, create, lifecycle actions, delete, and logs.
- [ ] Add Zod-validated deployment/operation/log DTO mappers, query keys/hooks, SSE invalidation, and bounded polling fallback.
- [ ] Replace deployment list/detail/action/log mock imports with real Central data and role-aware mutation controls.
- [ ] Replace Deploy Model Dialog mock options with installed same-server model files, real online mutable targets, automatic/manual GPU placement, and inline capability/conflict errors.
- [ ] Submit typed vLLM fields, use a structured extra-argument editor/allowlist, and clearly gate the trust-remote-code risk.
- [ ] Implement state-correct Start, Stop, Restart, Retry, and exact-confirm Delete controls with disabled/pending states and no duplicate mutation.
- [ ] Show endpoint, desired/observed state, health, selected GPUs, configuration, operation timeline, safe failure details, and real bounded/following logs.
- [ ] Refresh Dashboard, GPU, model deployment counts, list, and detail data through SSE/polling; hide all lifecycle controls from Viewer.

Evidence:

- Web tests cover DTO mapping, planner/form payloads, role/action visibility, status/action matrix, pending deduplication, log cursors/search, SSE invalidation, and tracked deployment mock-import removal.

### Phase 6.8 Browser and interaction verification

- [ ] Create a fixture deployment for a discovered `Qwen/Qwen3-8B` location on `xiao-pro6000` using automatic placement and verify the selected GPU/port/configuration.
- [ ] Exercise manual GPU placement and surface port, stale GPU, unsupported format, and unauthorized Viewer errors.
- [ ] Observe queued/starting/running and healthy state, endpoint publication, logs, Dashboard count, and GPU allocation without reload.
- [ ] Exercise Stop and verify stopped state, released runtime GPU state, and preserved configuration.
- [ ] Exercise Start and Restart, including idempotent repeated actions and operation-progress feedback.
- [ ] Exercise exact-confirm Delete and verify only the owned fixture runtime disappears while the installed model remains.
- [ ] Verify keyboard operation, dialog focus return, status announcements, long names/logs/errors, and no page-level overflow at available viewports.

Evidence:

- Browser checks capture the complete tiny-runtime lifecycle and note fixed viewport or GPU capability honestly.

### Phase 6.9 Phase gate

- [ ] Run Web, API, Agent lint/typecheck/tests, Python package builds, production Web build, and migration cycle.
- [ ] Validate base and Agent Compose configurations and extend the clean Linux smoke through create/claim/start/reconcile/health/logs/stop/restart/delete and Viewer denial.
- [ ] Verify Docker SDK/runtime dependencies install in clean Linux containers and the fixture runtime adapter is impossible in production.
- [ ] Run tracked secret, generic-command, shell, arbitrary-image/volume, unsafe-model-path, foreign-container, Docker-socket, backup-host mutation, and deployment mock-dependency scans.
- [ ] Verify Phase 0-5 routes, authentication, heartbeats, inventory, downloads/deletion, SSE, polling, and Compose behavior remain healthy.
- [ ] Record exact local/browser/Linux CI evidence and host-specific deployment prerequisites before opening Phase 7.

## Exit acceptance

- [ ] An Admin can choose an installed model on `xiao-pro6000`, use automatic or manual same-server GPU placement, and create a typed vLLM deployment.
- [ ] Central and Agent both reject stale/unavailable GPUs, conflicting ports, unsafe model paths, unsupported backends/images, foreign containers, and backup-host mutation.
- [ ] The Agent creates only an exactly labeled, hardened container with a read-only model mount, managed argv, selected GPU devices, and no shell execution.
- [ ] Deployment state converges through queued/starting/running/healthy, and the console exposes the expected `http://server:port/v1` base URL.
- [ ] Start, Stop, Restart, Retry, and Delete are idempotent, lease/generation-safe, role-protected, and auditable.
- [ ] Stop releases runtime GPU memory/state; Delete removes only the owned container/configuration and never removes the model file.
- [ ] Deployment Detail exposes real configuration, health, safe errors, and bounded Agent-forwarded logs.
- [ ] Agent/container restart and missing-container reconciliation cannot leave a false running state or let stale reporters overwrite a new generation.
- [ ] Viewer can read deployment state/logs but cannot see or invoke lifecycle mutation controls.
- [ ] No generic command execution, inbound Agent listener, arbitrary Docker control, or backup-host modification was introduced.
- [ ] Phase 0-5 Web/API/Agent/Compose checks still pass.
- [ ] No modification was made to `asus-2024` or `asus-4090`.

Phase 7 must not start until every item above is checked and backed by current command, browser, runtime, or Linux CI output.
