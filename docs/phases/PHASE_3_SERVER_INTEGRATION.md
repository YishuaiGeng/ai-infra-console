# Phase 3: Server Integration

## Status

- State: In progress; code-level plan established on 2026-08-08
- Entry gate: Phase 2 complete, including Linux Agent registration/heartbeat/revocation evidence
- Exit gate: every acceptance item in this document has direct automated, browser, or runtime evidence
- Scope boundary: real server/GPU visibility only; model inventory, downloads, deployment actions, and historical charts remain in later phases
- Host boundary: development may target `xiao-pro6000` or `xiao-cpu`; do not modify `asus-2024` or `asus-4090`

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

- [ ] Add `schemas/infrastructure.py` with server summary, server detail, current server metric, GPU, GPU process, and dashboard summary DTOs.
- [ ] Represent nullable collector values explicitly and preserve byte/percentage/timestamp units.
- [ ] Include server identity in each GPU response so GPU components never join against mock data.
- [ ] Define a typed infrastructure event envelope with event ID, kind, server ID, and timestamp.
- [ ] Export only public fields; Agent token hashes, audit details, private credentials, and raw collector errors must remain absent.

Evidence:

- Schema tests validate complete, partial, offline, CPU-only, and multi-GPU responses plus secret-field exclusion.

### Phase 3.2 Database read model and status derivation

- [ ] Add `services/infrastructure.py` queries for the server list, one server detail, all current GPUs, and dashboard totals.
- [ ] Select only the latest `gpu_metrics` row per GPU and avoid per-row database queries.
- [ ] Join current `server_metrics` and `gpu_processes` into bounded response objects.
- [ ] Apply the 30-second stale-server transition before infrastructure reads.
- [ ] Derive GPU status consistently: offline server, active process, high utilization, VRAM pressure, then available.
- [ ] Return deterministic ordering by server name and GPU index.

Evidence:

- Database tests cover three servers, four GPUs, stale/offline behavior, process replacement, latest-metric selection, CPU-only servers, and query result ordering.

### Phase 3.3 Authenticated infrastructure endpoints

- [ ] Expand `GET /api/v1/servers` to return real server summaries for authenticated Admin and Viewer users.
- [ ] Add `GET /api/v1/servers/{server_id}` for Overview, GPUs, and Processes data.
- [ ] Add `GET /api/v1/gpus` for the cross-server inventory.
- [ ] Add `GET /api/v1/infrastructure/summary` for Dashboard server/GPU capacity totals.
- [ ] Preserve Admin-only registration, token rotation, and token revocation routes.
- [ ] Return the standard error envelope for unauthorized, missing, and malformed requests.

Evidence:

- API tests cover Admin/Viewer reads, anonymous rejection, 404 handling, multi-server aggregation, and unchanged Admin-only mutations.

### Phase 3.4 Redis-backed SSE updates

- [ ] Add a small event publisher using the existing Redis connection and a versioned channel name.
- [ ] Publish a server update only after a registration or heartbeat transaction commits.
- [ ] Add authenticated `GET /api/v1/infrastructure/events` as `text/event-stream` with event IDs and keepalive comments.
- [ ] Handle Redis disconnects, client cancellation, and stream cleanup without leaking tasks or connections.
- [ ] Emit or reconcile offline transitions so stale nodes leave the online view promptly.
- [ ] Document that SSE is an invalidation signal, not the source of record.

Evidence:

- Async tests cover publish-after-commit, authenticated stream shape, keepalive/reconnect behavior, cancellation cleanup, and Redis failure degradation.

### Phase 3.5 Web session and same-origin API boundary

- [ ] Add a server-only Central API client configured by `AI_INFRA_API_INTERNAL_URL`.
- [ ] Add login, current-session, and logout route handlers that set/delete a Secure HttpOnly SameSite cookie.
- [ ] Add authenticated proxy handlers for infrastructure reads and the SSE stream; never serialize the API bearer token to client code.
- [ ] Add a focused login screen and redirect unauthenticated console requests to it.
- [ ] Map Central error envelopes into stable Web errors and clear expired sessions on HTTP 401.
- [ ] Add Compose/environment configuration for the internal API URL without exposing host credentials.

Evidence:

- Route-handler tests cover successful login, bad credentials, cookie flags, logout, authenticated proxying, token non-exposure, and expired-session behavior.

### Phase 3.6 Typed Web data layer

- [ ] Add API DTO types, validated mappers, and UI domain types for real infrastructure data.
- [ ] Add stable TanStack Query keys and hooks for dashboard summary, servers, server detail, and GPUs.
- [ ] Add one SSE subscription that invalidates only affected infrastructure queries.
- [ ] Add bounded polling as a reconnect/fallback path and pause unnecessary refresh work in hidden tabs.
- [ ] Convert bytes and uptime to display units only in shared formatters.
- [ ] Remove all server/GPU lookup imports from `mocks/data.ts` in the Phase 3 data path.

Evidence:

- Unit tests cover DTO mapping, query invalidation, offline/null handling, byte conversion, and status mapping.

### Phase 3.7 Replace infrastructure mock usage

- [ ] Wire Dashboard server totals, GPU capacity, GPU resource table, and server status table to real queries.
- [ ] Wire Servers search/filter/sort and Add Server registration to real APIs; show the one-time token only after creation.
- [ ] Replace static server detail params/metadata and wire Overview, GPUs, Processes, refresh, and Agent token controls to real data.
- [ ] Wire GPU table/card views and all filters to real cross-server data.
- [ ] Refactor `GPUCard`, `GPUResourceTable`, `GPUProcessTable`, and breadcrumbs to receive server/GPU data rather than importing mocks.
- [ ] Keep model/deployment/download fixtures clearly isolated until their roadmap phases while removing their dependency on mock server/GPU records.

Evidence:

- A tracked-source scan finds no server/GPU mock import in Dashboard, Servers, Server Detail, GPUs, or their shared infrastructure components.

### Phase 3.8 User-visible states and browser verification

- [ ] Add stable loading skeletons for all four real-data pages without layout shift.
- [ ] Add actionable authentication, network, empty-inventory, CPU-only, and offline states.
- [ ] Preserve filters and tabs across background refreshes without replacing the whole page.
- [ ] Confirm table/card controls, dialogs, token copy, logout, and manual refresh remain keyboard accessible.
- [ ] Verify no text overflow, overlap, blank state, or hydration error at desktop and mobile viewports.

Evidence:

- Browser checks cover 1440x900 and 390x844 with online, offline, CPU-only, empty, loading, and API-error fixtures.

### Phase 3.9 Phase gate

- [ ] Run Web, API, Agent lint/typecheck/tests and production builds.
- [ ] Run PostgreSQL migrations and the five-service Compose smoke test.
- [ ] Extend Compose smoke with three registered servers, including online, offline, and CPU-only cases.
- [ ] Verify Agent heartbeat triggers SSE and refreshes Dashboard, Servers, Server Detail, and GPUs without a full reload.
- [ ] Verify Viewer reads work while registration/token lifecycle remains Admin-only.
- [ ] Run tracked secret and server/GPU mock-dependency scans.
- [ ] Record exact evidence and unresolved host-specific items before opening Phase 4.

## Exit acceptance

- [ ] Three simultaneous server records are aggregated consistently across Dashboard and inventory views.
- [ ] Users can identify each server and GPU status, capacity, and freshness without inspecting raw payloads.
- [ ] Offline and CPU-only servers degrade correctly and remain inspectable.
- [ ] Dashboard, Servers, Server Detail, GPUs, and their shared components do not depend on server/GPU mock data.
- [ ] SSE updates invalidate real queries, and polling recovers after an interrupted stream.
- [ ] API tokens remain in HttpOnly server-side session handling and are absent from browser storage/client payloads.
- [ ] Admin and Viewer authorization boundaries are enforced.
- [ ] Phase 0-2 Web/API/Agent/Compose checks still pass.
- [ ] No modification was made to `asus-2024` or `asus-4090`.

Phase 4 must not start until every item above is checked and backed by current command, browser, or runtime output.
