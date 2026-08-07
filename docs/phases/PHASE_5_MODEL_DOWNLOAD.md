# Phase 5: Model Download

## Status

- State: Implementation complete; final interaction evidence and Linux CI gate in progress on 2026-08-08
- Entry gate: Phase 4 complete, including model inventory and GitHub Actions run `31210327473`
- Exit gate: every acceptance item in this document has direct automated, browser, or runtime evidence
- Scope boundary: provider discovery, download, retry, cancel, and safe deletion only; runtime deployment remains Phase 6
- Host boundary: mutation may be enabled only for `xiao-cpu` and `xiao-pro6000`; do not modify `asus-2024` or `asus-4090`

## Technical decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Remote execution | Define explicit download and delete task DTOs; never expose a generic command, argv, shell, or script field | Keeps the outbound Agent useful without creating remote-code-execution surface |
| Host policy | Central requires an explicit mutable-server allowlist and Agent requires `AI_INFRA_AGENT_ENABLE_MODEL_MUTATIONS=true` | Both control-plane and host owner must opt in; backup hosts remain read-only |
| Path authority | The UI submits a directory ID. Central resolves an Agent-advertised available root, and Agent independently recomputes and contains the final path under its exact local allowlist | User input and Central state cannot make Agent write outside approved roots |
| Providers | Use official `huggingface_hub` and `modelscope-hub` clients behind small provider adapters | Reuses maintained search, retry, range/resume, locking, and integrity behavior |
| Credentials | Read `HF_TOKEN`, `HF_ENDPOINT`, `MODELSCOPE_TOKEN`, `MODELSCOPE_ENDPOINT`, `HTTP_PROXY`, and `HTTPS_PROXY` only from local service environments; never persist or return them | Supports private mirrors and proxies without turning credentials into task data |
| Download layout | Stage into a task-specific partial directory, then atomically publish to `<root>/<provider>/<owner>/<repo>` after success | Failed and cancelled tasks never look like installed models |
| State machine | `queued -> downloading -> completed`; cancellation uses `queued -> cancelled` or `downloading -> cancelling -> cancelled`; retry creates a new attempt from `failed/cancelled` | Explicit transitions make retries, leases, and UI behavior deterministic |
| Leasing | Agent claims one task at a time with a random lease token, bounded expiry, heartbeat extension, and compare-on-update | Agent restart can recover work while an old claimant cannot overwrite a newer attempt |
| Progress | Provider callbacks update bounded byte counters; Agent coalesces reports and Central computes validated progress/speed | Avoids per-chunk request floods and does not trust impossible counters |
| Deletion | Admin confirms the exact source ID; Central rejects deployed files and Agent validates root containment, target type, and symlink policy again before removal | Destructive action has two confirmations and cannot cross the filesystem boundary |
| Refresh | Download/delete state publishes versioned SSE events; completed mutations trigger an immediate inventory refresh request and polling remains fallback | Downloads and Installed Models converge without a page reload |
| Tests | Unit tests use fake provider adapters; Compose uses a tiny read-only fixture source enabled only in the test environment | Proves the full protocol without downloading a public multi-gigabyte model in CI |

## Code-level tasks

### Phase 5.1 Persistence and task state machine

- [x] Add an Alembic migration for download revision, directory reference, requester, attempt, lease, cancellation, progress freshness, safe error code, and timestamps.
- [x] Add a dedicated model-delete task table rather than overloading download rows or creating a generic command table.
- [x] Add database constraints/indexes for server/status ordering, non-negative byte counters, bounded attempts, and one active destination.
- [x] Implement pure transition helpers for claim, progress, cancel, complete, fail, retry, lease expiry, and stale claimant rejection.
- [x] Store lease token digests only and compare submitted lease credentials without logging them.
- [x] Keep provider errors sanitized into bounded code/message fields and retain request/audit IDs separately.

Evidence:

- Migration and service tests cover upgrade/downgrade, every legal transition, illegal transitions, lease expiry/reclaim, stale updates, duplicate destination, and rollback.

### Phase 5.2 Provider catalog adapters

- [x] Add a normalized catalog DTO for provider, source ID, display name, task/type, tags, downloads, likes, license, gated/private flags, revision, size, architecture, and last modified time.
- [x] Add a Hugging Face adapter using `HfApi.list_models()` and `model_info()` with bounded result count, timeout, endpoint, and token configuration.
- [x] Add a ModelScope adapter using the official `modelscope-hub` client with equivalent normalized output.
- [x] Validate provider names and repository IDs; reject URLs, traversal segments, control characters, and unbounded query strings.
- [x] Execute synchronous provider clients off the async event loop and map timeout/auth/rate-limit/upstream failures to stable API errors.
- [x] Add a short bounded cache that varies by provider/query and never stores tokens or raw upstream responses.

Evidence:

- Adapter tests use injected fake clients for result mapping, empty results, malformed entries, private/gated records, timeout, auth, rate limit, and response bounds.

### Phase 5.3 Authenticated download and deletion APIs

- [x] Add authenticated catalog search/detail APIs for Admin and Viewer; keep all mutations Admin-only.
- [x] Add `POST /api/v1/downloads`, `GET /api/v1/downloads`, and `GET /api/v1/downloads/{id}` with deterministic filtering and ordering.
- [x] Add Admin-only cancel and retry endpoints with idempotent terminal-state behavior.
- [x] Add Admin-only installation deletion request/status endpoints with exact source-ID confirmation.
- [x] Require server online state, Central mutable-server allowlist membership, an active Agent, and an available Agent-advertised target directory before queueing.
- [x] Reject downloads to arbitrary text paths, backup hosts, stale/unavailable roots, duplicate active destinations, and already installed identical revisions unless force behavior is explicitly added later.
- [x] Reject deletion while a `Deployment` references the model file and never cascade a deployment through deletion.
- [x] Record audit entries and publish `model.download.updated` or `model.inventory.updated` only after commit.

Evidence:

- API tests cover anonymous/Admin/Viewer roles, host policy, directory IDs, duplicate jobs, filters, cancel/retry, confirmation mismatch, deployed-file rejection, and secret-free responses.

### Phase 5.4 Outbound Agent task protocol

- [x] Add a server-scoped Agent claim endpoint returning a discriminated download/delete union with no free-form executable field.
- [x] Add lease-authenticated progress and terminal-report endpoints that only accept tasks owned by the authenticated Agent server.
- [x] Return cancellation state from progress reports so a downloading Agent can stop cooperatively.
- [x] Extend `CentralClient` with typed claim/report methods and stable handling for empty queues, auth failure, lease conflict, and transient Central failure.
- [x] Extend `AgentRunner` to keep heartbeats flowing while supervising at most one mutation task.
- [x] Recover expired tasks after Agent restart and refuse late progress from the previous lease holder.

Evidence:

- API/Agent protocol tests cover cross-server denial, digest mismatch, one-at-a-time claim, lease renewal, cancellation, retry, restart reclaim, and heartbeat continuity.

### Phase 5.5 Safe Agent download execution

- [x] Add Agent settings for the mutation opt-in, task polling/report intervals, lease behavior, provider tokens/endpoints, proxy support, worker limits, and test-only fixture provider.
- [x] Reject mutation enablement in production when no allowed model directories exist or transport is not verified HTTPS.
- [x] Implement repository-ID normalization and a deterministic provider/owner/repository relative layout.
- [x] Resolve the advertised root against the Agent allowlist, refuse root replacement, symlink parents, non-directory roots, existing unrelated targets, and containment escapes.
- [x] Implement Hugging Face snapshot downloads and ModelScope repository downloads through official clients with local credentials and bounded workers.
- [x] Stage each attempt under the selected root, emit coalesced progress, support cooperative cancel, preserve resumable provider metadata, and atomically publish only after success.
- [x] Clean task-owned incomplete paths after cancellation/fatal failure without touching provider caches or unrelated files.
- [x] Invalidate the model-scan cache after publish so the next heartbeat reports the new installation immediately.

Evidence:

- Agent tests cover both provider adapters, progress, retryable/fatal errors, cancellation, partial cleanup, resume metadata, target collisions, symlinks, traversal, disabled mutations, and token redaction.

### Phase 5.6 Safe Agent deletion

- [x] Accept only a typed deletion task containing the inventory row identity, advertised root, expected source identity, and physical path.
- [x] Re-resolve the root and target locally; require the target to be strictly below one exact allowed directory.
- [x] Refuse allowlist roots themselves, symlinks, special files, missing identity evidence, paths outside the root, and targets not owned by the selected inventory row.
- [x] Remove only the selected file or directory tree without crossing filesystem boundaries.
- [x] Make already-absent targets idempotent, report a bounded outcome, and invalidate the scan cache after success.

Evidence:

- Deletion tests cover file/directory success, absent idempotency, root refusal, symlink escape, special file, identity mismatch, sibling preservation, and mutation-disabled mode.

### Phase 5.7 Web data layer and workflows

- [x] Add same-origin BFF handlers for catalog, downloads, cancel/retry, and deletion with existing HttpOnly session behavior.
- [x] Add Zod-validated catalog/task DTO mappers, query keys/hooks, SSE invalidation, and bounded polling fallback.
- [x] Replace Model Library mock definitions with debounced provider search, provider/type filters, loading, empty, upstream-error, gated, and private states.
- [x] Replace Download Dialog's free-text path with real online mutable servers and their available advertised directories.
- [x] Submit real download tasks and surface validation, authorization, duplicate, offline, and provider errors inline.
- [x] Replace Downloads mock rows/actions with real task progress, bytes, speed, attempts, timestamps, errors, Cancel, and Retry.
- [x] Add Admin-only two-step deletion from Installed Models with exact model identity confirmation and deployed-model refusal feedback.
- [x] Keep Viewer catalog/download reads visible while hiding every mutation control.

Evidence:

- Web tests cover DTO mapping, debounce/query keys, form payloads, progress calculation, state/action visibility, SSE invalidation, and tracked-source mock-import removal.

### Phase 5.8 Browser and interaction verification

- [x] Search `Qwen/Qwen3-8B` through Hugging Face and ModelScope fixtures and verify provider metadata/error states.
- [x] Create a download for `xiao-cpu` or `xiao-pro6000` fixture using a selected advertised directory, never a typed path.
- [x] Observe queued/downloading/completed progress and verify Installed Models refreshes with the published path.
- [x] Exercise cancel and retry without duplicate rows or stale progress overwrites.
- [ ] Exercise deletion confirmation, successful removal, deployed-model refusal, and inventory refresh.
- [x] Verify Viewer cannot see download/delete mutation controls.
- [ ] Verify keyboard operation, focus return, status announcements, long IDs/paths, no overlap, and no horizontal overflow at available desktop/mobile viewports.

Evidence:

- Browser checks capture the complete tiny-fixture lifecycle and note any viewport capability honestly.

### Phase 5.9 Phase gate

- [x] Run Web, API, Agent lint/typecheck/tests, package builds, and production Web build.
- [x] Run PostgreSQL migration upgrade/downgrade/upgrade and both Compose configurations.
- [ ] Extend Compose smoke through Admin create, Agent claim, progress, completion, scan convergence, cancel/retry, delete, and Viewer denial.
- [x] Verify official provider dependencies install in clean Linux containers and test-only fixture mode is impossible in production.
- [x] Run tracked secret, arbitrary-command, unsafe-path, backup-host mutation, and remaining model/download mock-dependency scans.
- [x] Verify Phase 0-4 routes, auth, Agent heartbeat, model inventory, SSE, and polling remain healthy.
- [ ] Record exact evidence and host-specific deployment items before opening Phase 6.

## Exit acceptance

- [x] Searching `Qwen/Qwen3-8B` returns normalized Hugging Face and ModelScope results or a clear provider-specific state.
- [x] An Admin can select an allowed directory on `xiao-cpu` or `xiao-pro6000` and create a real outbound Agent download task.
- [x] Downloads exposes queued/downloading/cancelling/completed/failed/cancelled state, bytes, total, speed, attempt, and safe error details.
- [x] Cancel and retry are idempotent, lease-safe, and do not publish partial models.
- [x] Completed downloads appear in Installed Models after an immediate inventory refresh.
- [x] Admin can delete an undeployed installation only after exact confirmation; Agent cannot delete outside its local allowlist.
- [x] Provider credentials and proxy configuration remain local secrets and never enter database rows, API responses, logs, or Git.
- [x] No generic command execution, deployment action, or inbound Agent listener was introduced.
- [ ] Phase 0-4 Web/API/Agent/Compose checks still pass.
- [x] No modification was made to `asus-2024` or `asus-4090`.

## Current evidence

- API: 44 tests passed; Ruff and mypy passed. The migration cycle test passes upgrade/downgrade/upgrade and verifies the Phase 5 task schema.
- Agent: 44 tests passed with one Windows symlink test skipped; Ruff, mypy, wheel, and source distribution builds passed.
- Web: ESLint and TypeScript passed; 15 Vitest tests passed with 84.72% statement coverage; the production Next.js build passed.
- Browser: real Hugging Face and ModelScope search, allowlisted `xiao-pro6000` selection, completed download and inventory convergence, cancel/retry, exact-confirm deletion, and Viewer mutation hiding were observed against the isolated Phase 5 stack.
- Compose: both configurations validate. The local smoke reached download, scan, retry, delete, Viewer denial, Web BFF, and token-revocation stages; Docker Desktop locked while checking the final stopped-Agent assertion, so the Linux GitHub Actions run remains the authoritative full gate.
- Security: the tracked secret, generic command, unsafe path, backup-host mutation, and Phase 5 mock-dependency scan passes. No mutation request was sent to either backup host.

Phase 6 must not start until every item above is checked and backed by current command, browser, or runtime output.
