# Phase 3: Server Integration

## Status

- State: Complete; accepted on 2026-08-08
- Entry gate: Phase 2 complete, including Linux Agent registration/heartbeat/revocation evidence
- Exit gate: every acceptance item in this document has direct automated, browser, or runtime evidence
- Scope boundary: real server/GPU visibility only; model inventory, downloads, deployment actions, and historical charts remain in later phases
- Host boundary: development may target `gpu-node-01` or `storage-node-01`; do not modify `backup-node-01` or `backup-node-02`

## Technical decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Read API | Purpose-built infrastructure summary, server detail, and GPU read models | Keeps database joins and status derivation out of the browser |
| Read authorization | Any authenticated active user may read infrastructure; registration and token changes remain Admin-only | Matches the existing Admin/Viewer role boundary |
| Browser session | Same-origin Next.js route handlers hold the API JWT in an HttpOnly cookie | Prevents bearer tokens from being persisted in browser JavaScript storage |
| Refresh | Redis Pub/Sub to FastAPI SSE, proxied through the same-origin Web application | Supports outbound HTTP infrastructure and browser-native streaming without adding a second protocol stack |
| Reconciliation | SSE invalidates TanStack Query caches; bounded polling remains the recovery path | Event loss or reconnects cannot leave the UI permanently stale |
| GPU status | Server offline wins; otherwise process presence, utilization, and VRAM pressure derive the UI status | Produces one deterministic status model across all pages |
| Units | API returns bytes, seconds, timestamps, and percentages; Web formats presentation units | Avoids precision loss and presentation-specific API contracts |

## Code-level tasks

### Phase 3.1 Infrastructure response contracts

- [x] Add `schemas/infrastructure.py` with server summary, server detail, current server metric, GPU, GPU process, and dashboard summary DTOs.
- [x] Represent nullable collector values explicitly and preserve byte/percentage/timestamp units.
- [x] Include server identity in each GPU response so GPU components never join against mock data.
- [x] Define a typed infrastructure event envelope with event ID, kind, server ID, and timestamp.
- [x] Export only public fields; Agent token hashes, audit details, private credentials, and raw collector errors must remain absent.

Evidence:

- Schema tests validate complete, partial, offline, CPU-only, and multi-GPU responses plus secret-field exclusion.

### Phase 3.2 Database read model and status derivation

- [x] Add `services/infrastructure.py` queries for the server list, one server detail, all current GPUs, and dashboard totals.
- [x] Select only the latest `gpu_metrics` row per GPU and avoid per-row database queries.
- [x] Join current `server_metrics` and `gpu_processes` into bounded response objects.
- [x] Apply the 30-second stale-server transition before infrastructure reads.
- [x] Derive GPU status consistently: offline server, active process, high utilization, VRAM pressure, then available.
- [x] Return deterministic ordering by server name and GPU index.

Evidence:

- Database tests cover three servers, four GPUs, stale/offline behavior, process replacement, latest-metric selection, CPU-only servers, and query result ordering.

### Phase 3.3 Authenticated infrastructure endpoints

- [x] Expand `GET /api/v1/servers` to return real server summaries for authenticated Admin and Viewer users.
- [x] Add `GET /api/v1/servers/{server_id}` for Overview, GPUs, and Processes data.
- [x] Add `GET /api/v1/gpus` for the cross-server inventory.
- [x] Add `GET /api/v1/infrastructure/summary` for Dashboard server/GPU capacity totals.
- [x] Preserve Admin-only registration, token rotation, and token revocation routes.
- [x] Return the standard error envelope for unauthorized, missing, and malformed requests.

Evidence:

- API tests cover Admin/Viewer reads, anonymous rejection, 404 handling, multi-server aggregation, and unchanged Admin-only mutations.

### Phase 3.4 Redis-backed SSE updates

- [x] Add a small event publisher using the existing Redis connection and a versioned channel name.
- [x] Publish a server update only after a registration or heartbeat transaction commits.
- [x] Add authenticated `GET /api/v1/infrastructure/events` as `text/event-stream` with event IDs and keepalive comments.
- [x] Handle Redis disconnects, client cancellation, and stream cleanup without leaking tasks or connections.
- [x] Emit or reconcile offline transitions so stale nodes leave the online view promptly.
- [x] Document that SSE is an invalidation signal, not the source of record.

Evidence:

- Async tests cover publish-after-commit, authenticated stream shape, keepalive/reconnect behavior, cancellation cleanup, and Redis failure degradation.

### Phase 3.5 Web session and same-origin API boundary

- [x] Add a server-only Central API client configured by `AI_INFRA_API_INTERNAL_URL`.
- [x] Add login, current-session, and logout route handlers that set/delete a Secure HttpOnly SameSite cookie.
- [x] Add authenticated proxy handlers for infrastructure reads and the SSE stream; never serialize the API bearer token to client code.
- [x] Add a focused login screen and redirect unauthenticated console requests to it.
- [x] Map Central error envelopes into stable Web errors and clear expired sessions on HTTP 401.
- [x] Add Compose/environment configuration for the internal API URL without exposing host credentials.

Evidence:

- Route-handler tests cover successful login, bad credentials, cookie flags, logout, authenticated proxying, token non-exposure, and expired-session behavior.

### Phase 3.6 Typed Web data layer

- [x] Add API DTO types, validated mappers, and UI domain types for real infrastructure data.
- [x] Add stable TanStack Query keys and hooks for dashboard summary, servers, server detail, and GPUs.
- [x] Add one SSE subscription that invalidates only affected infrastructure queries.
- [x] Add bounded polling as a reconnect/fallback path and pause unnecessary refresh work in hidden tabs.
- [x] Convert bytes and uptime to display units only in shared formatters.
- [x] Remove all server/GPU lookup imports from `mocks/data.ts` in the Phase 3 data path.

Evidence:

- Unit tests cover DTO mapping, query invalidation, offline/null handling, byte conversion, and status mapping.

### Phase 3.7 Replace infrastructure mock usage

- [x] Wire Dashboard server totals, GPU capacity, GPU resource table, and server status table to real queries.
- [x] Wire Servers search/filter/sort and Add Server registration to real APIs; show the one-time token only after creation.
- [x] Replace static server detail params/metadata and wire Overview, GPUs, Processes, refresh, and Agent token controls to real data.
- [x] Wire GPU table/card views and all filters to real cross-server data.
- [x] Refactor `GPUCard`, `GPUResourceTable`, `GPUProcessTable`, and breadcrumbs to receive server/GPU data rather than importing mocks.
- [x] Keep model/deployment/download fixtures clearly isolated until their roadmap phases while removing their dependency on mock server/GPU records.

Evidence:

- A tracked-source scan finds no server/GPU mock import in Dashboard, Servers, Server Detail, GPUs, or their shared infrastructure components.

### Phase 3.8 User-visible states and browser verification

- [x] Add stable loading skeletons for all four real-data pages without layout shift.
- [x] Add actionable authentication, network, empty-inventory, CPU-only, and offline states.
- [x] Preserve filters and tabs across background refreshes without replacing the whole page.
- [x] Confirm table/card controls, dialogs, token copy, logout, and manual refresh remain keyboard accessible.
- [x] Verify no text overflow, overlap, blank state, or hydration error at desktop and mobile viewports.

Evidence:

- Browser checks cover 1440x900 and 390x844 with online, offline, CPU-only, empty, loading, and API-error fixtures.

### Phase 3.9 Phase gate

- [x] Run Web, API, Agent lint/typecheck/tests and production builds.
- [x] Run PostgreSQL migrations and the five-service Compose smoke test.
- [x] Extend Compose smoke with three registered servers, including online, offline, and CPU-only cases.
- [x] Verify Agent heartbeat triggers SSE and refreshes Dashboard, Servers, Server Detail, and GPUs without a full reload.
- [x] Verify Viewer reads work while registration/token lifecycle remains Admin-only.
- [x] Run tracked secret and server/GPU mock-dependency scans.
- [x] Record exact evidence and unresolved host-specific items before opening Phase 4.

## Exit acceptance

- [x] Three simultaneous server records are aggregated consistently across Dashboard and inventory views.
- [x] Users can identify each server and GPU status, capacity, and freshness without inspecting raw payloads.
- [x] Offline and CPU-only servers degrade correctly and remain inspectable.
- [x] Dashboard, Servers, Server Detail, GPUs, and their shared components do not depend on server/GPU mock data.
- [x] SSE updates invalidate real queries, and polling recovers after an interrupted stream.
- [x] API tokens remain in HttpOnly server-side session handling and are absent from browser storage/client payloads.
- [x] Admin and Viewer authorization boundaries are enforced.
- [x] Phase 0-2 Web/API/Agent/Compose checks still pass.
- [x] No modification was made to `backup-node-01` or `backup-node-02`.

## Final evidence

```text
npm run check                                      PASS
Web tests / coverage                               8 passed / 80.1%
API tests / coverage                               31 passed / 82%
Agent tests / coverage                             28 passed / 82%
npm run api:smoke                                  PASS
docker compose config --quiet                      PASS
docker compose --profile agent config --quiet      PASS
GitHub Actions web/api/agent/compose               PASS (run 31207075696)
Compose three-server/API/SSE/Web BFF smoke          PASS
Tracked secret and infrastructure mock scans       PASS
Browser login/live refresh/list/detail/logout       PASS
```

Runtime fixtures covered online four-GPU, offline one-GPU, CPU-only, and pending-registration servers. The browser check also covered available-only filtering, table/card views, one active GPU process, Agent token controls, and CPU-only/empty states without horizontal overflow. No host deployment was attempted in this phase, and neither backup server was modified.

Phase 4 may start because every item above is checked and backed by current command, browser, or runtime output.
