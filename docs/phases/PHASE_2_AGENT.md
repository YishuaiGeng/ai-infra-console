# Phase 2: Agent

## Status

- State: In progress; code-level plan established on 2026-08-08
- Entry gate: Phase 1 complete, including Linux Compose and PostgreSQL runtime evidence
- Exit gate: every acceptance item in this document has direct automated or runtime evidence
- Scope boundary: no model scanning/download, deployment lifecycle, log streaming, or UI data replacement
- Host boundary: development may target `xiao-pro6000` or `xiao-cpu`; do not modify `asus-2024` or `asus-4090`

## Technical decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Runtime | Python 3.11+ package in `apps/agent` | Matches the API toolchain and remains portable across target Linux hosts |
| Communication | Agent-initiated HTTPS requests to Central API | Works across NAT and firewalls without inbound Agent ports |
| Authentication | One high-entropy bearer token per Agent, stored only as a SHA-256 digest | Tokens are random credentials, support indexed lookup/revocation, and are never stored in plaintext |
| Collection | `psutil` plus small fixed collectors | Covers host metrics without shell parsing for common data |
| NVIDIA | NVML first, fixed-argument `nvidia-smi` fallback | Uses the native API when available while retaining broad compatibility |
| Optional runtimes | Docker SDK and local Ollama HTTP/version probes | Missing software must degrade to an explicit unavailable state |
| Operations | Enum-backed allowlist and explicit handlers | Unknown actions fail closed; no arbitrary command construction or execution |
| Offline rule | Configurable 30-second threshold evaluated from `last_seen` | Keeps online state deterministic and testable without opening Phase 3 streaming work |

## Code-level tasks

### Phase 2.1 Agent package and configuration

- [ ] Create `apps/agent/pyproject.toml`, lockfile, `src/ai_infra_agent`, tests, and CLI entry point.
- [ ] Add typed settings for Central URL, token, heartbeat interval, request timeout, TLS verification, and log level.
- [ ] Validate production URLs and prevent secrets from appearing in settings representations or logs.
- [ ] Add root lint, typecheck, test, and aggregate Agent commands.
- [ ] Emit structured logs with Agent version and request IDs.

Evidence:

- Frozen dependency sync, Ruff, strict mypy, and pytest pass independently for the Agent package.

### Phase 2.2 Central registration and token lifecycle

- [ ] Add Admin-only API operations to create a server registration, rotate its token, and revoke it.
- [ ] Generate at least 256 bits of entropy and return the plaintext token only at creation/rotation time.
- [ ] Store only a deterministic digest in `server_agents`; never log or serialize the digest to public responses.
- [ ] Add Agent authentication that is separate from Web JWT authentication.
- [ ] Implement `POST /api/v1/agent/register` with hostname, Agent version, and initial inventory.
- [ ] Record registration, rotation, revocation, success, and rejection in the audit log without secrets.

Evidence:

- Tests cover valid registration, replay by the same Agent, invalid/revoked tokens, role checks, rotation, and absence of plaintext token persistence.

### Phase 2.3 Host and runtime collectors

- [ ] Collect hostname, OS, kernel, architecture, boot time, CPU model/count/load, RAM, disks, and network counters with `psutil`/standard APIs.
- [ ] Detect Python version and Agent version.
- [ ] Detect Docker daemon/version through the Docker SDK without failing the whole snapshot when unavailable.
- [ ] Detect Ollama availability/version through its local API or a fixed read-only probe.
- [ ] Define Pydantic snapshot schemas shared by collection, transport, and API validation.
- [ ] Normalize byte counts, percentages, timestamps, nullable values, and collector errors.

Evidence:

- Deterministic tests cover populated, partially available, and unavailable collector states.

### Phase 2.4 NVIDIA GPU and process collectors

- [ ] Implement NVML collection for driver/CUDA capability, GPU UUID/index/name, utilization, VRAM, temperature, power, fan, and status.
- [ ] Collect compute/graphics process PID, username, command name, and GPU memory where available.
- [ ] Implement a fixed-column, fixed-argument `nvidia-smi` CSV fallback with strict parsing.
- [ ] Deduplicate process records and normalize units across NVML and fallback results.
- [ ] Return an empty GPU collection with an explicit availability reason on CPU-only hosts.

Evidence:

- Tests cover mocked NVML, mocked `nvidia-smi`, malformed output, no driver, no GPU, and a synthetic four-GPU snapshot.

### Phase 2.5 Heartbeat persistence and offline detection

- [ ] Add an Alembic migration for current server metrics and current GPU process snapshots.
- [ ] Implement `POST /api/v1/agent/heartbeat` with Agent bearer authentication.
- [ ] Transactionally update server inventory, Agent version/last_seen, GPU inventory, GPU metrics, server metrics, and process snapshots.
- [ ] Mark the reporting server online only after a valid heartbeat commits.
- [ ] Implement configurable stale-server evaluation with a 30-second default.
- [ ] Make repeated heartbeats idempotent for server/GPU identity and bounded for current process data.

Evidence:

- API/database tests cover initial heartbeat, repeated heartbeat, GPU changes, process replacement, rollback on invalid payload, and offline transition.

### Phase 2.6 Agent client and resilient loop

- [ ] Implement registration and heartbeat HTTP clients with explicit connect/read timeouts.
- [ ] Send the token only in the Authorization header and redact it from exceptions/logs.
- [ ] Add the default 10-second loop, bounded exponential backoff, jitter, and graceful shutdown.
- [ ] Distinguish authentication rejection from temporary network/server failure.
- [ ] Reuse one HTTP client and avoid overlapping collection or heartbeat cycles.

Evidence:

- Tests use a local fake Central API to verify request shape, retry/backoff, redaction, shutdown, and recovery.

### Phase 2.7 Allowlisted operation framework

- [ ] Define typed operation names and payload/result contracts.
- [ ] Register only Phase 2 read operations: `get_system_info`, `get_gpu_info`, and `get_gpu_processes`.
- [ ] Reject unknown, malformed, and not-yet-enabled operations before dispatch.
- [ ] Confirm no `/exec`, `/shell`, `/command`, raw subprocess, or arbitrary argument endpoint exists.
- [ ] Keep all subprocess use inside fixed collector adapters with constant executable arguments.

Evidence:

- Tests prove all three handlers work and unknown/arbitrary command-shaped requests fail closed.

### Phase 2.8 Packaging and Linux service operation

- [ ] Add a non-root Agent Dockerfile and an opt-in Compose smoke profile or equivalent isolated fixture.
- [ ] Add a systemd unit template with restart policy, environment-file loading, and hardened defaults.
- [ ] Add an installation/configuration script that does not embed real hostnames, addresses, or tokens.
- [ ] Document token provisioning, registration, startup, upgrade, revocation, troubleshooting, and CPU-only behavior.

Evidence:

- Package build succeeds; container runs as non-root; systemd unit passes static verification where available.

### Phase 2.9 Phase gate

- [ ] Run Web, API, Agent lint/typecheck/tests and production builds.
- [ ] Run API migration tests against PostgreSQL.
- [ ] Run an end-to-end registration and heartbeat against the Compose Central stack.
- [ ] Verify online state, persisted host metrics, GPU inventory/process shape, Agent version, and token revocation.
- [ ] Run the Agent collector on a CPU-only environment and retain evidence of graceful degradation.
- [ ] Scan tracked routes/code for prohibited generic command interfaces and tracked files for credentials.
- [ ] Record exact evidence and unresolved hardware-specific items before opening Phase 3.

## Exit acceptance

- [ ] A newly issued registration token connects exactly one Agent and is never stored in plaintext.
- [ ] Revocation blocks subsequent registration and heartbeat requests.
- [ ] Default heartbeat cadence is 10 seconds and the default offline threshold is 30 seconds.
- [ ] Host, runtime, GPU, GPU process, and Agent version payloads are validated and persisted.
- [ ] NVML is preferred and `nvidia-smi` is used only as the fixed fallback.
- [ ] CPU-only and missing-runtime hosts remain operational with explicit unavailable states.
- [ ] No arbitrary command or inbound remote-shell capability exists.
- [ ] Phase 1 Web/API/Compose checks still pass.
- [ ] No modification was made to `asus-2024` or `asus-4090`.

Phase 3 must not start until every item above is checked and backed by current command or runtime output.
