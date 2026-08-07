# Phase 4: Model Inventory

## Status

- State: In progress; code-level plan established on 2026-08-08
- Entry gate: Phase 3 complete, including real infrastructure pages and GitHub Actions run `31207075696`
- Exit gate: every acceptance item in this document has direct automated, browser, or runtime evidence
- Scope boundary: discover and display model installations only; provider search, downloads, deletion, and deployments remain in Phases 5-6
- Host boundary: model storage and scanning may target `xiao-cpu` and `xiao-pro6000`; do not modify `asus-2024` or `asus-4090`

## Technical decisions

| Area | Decision | Reason |
| --- | --- | --- |
| Path authority | `AI_INFRA_AGENT_ALLOWED_MODEL_DIRECTORIES` is the host-local security boundary; Central may label or choose a default only from Agent-advertised roots | A compromised or mistaken control-plane request cannot make an Agent traverse an arbitrary path |
| Transport | Model inventory is included in the existing outbound registration/heartbeat payload | Preserves the no-inbound-port Agent architecture |
| Scan unit | One `ModelFile` row represents one physical model installation or standalone artifact; sharded weights are aggregated under their model directory | Keeps the inventory useful without creating thousands of low-level shard rows |
| Identity | Prefer Hugging Face cache identity or `_name_or_path`; otherwise use a normalized source plus deterministic local identity | Allows the same logical model to join across servers while preserving separate physical locations |
| Reconciliation | Successful root scans reconcile rows; failed or inaccessible roots retain the last inventory and expose an error state | A transient mount failure must not look like a deliberate model deletion |
| Filesystem safety | Resolve paths, reject roots outside the local allowlist, skip symlink traversal, bound depth/file count/metadata size, and never read weight contents | Prevents traversal, loops, resource exhaustion, and accidental model data ingestion |
| Ollama | Discover through the loopback Ollama tags API with a bounded timeout and map entries to `ollama://` locations | Avoids shell parsing and keeps discovery read-only |
| Authorization | Active Admin and Viewer users may read inventory; only Admin may change the default-directory marker | Matches the Phase 3 read/mutation boundary |
| Refresh | Inventory changes publish the existing versioned infrastructure event envelope with a model-specific kind | Reuses SSE invalidation without treating events as source of record |

## Code-level tasks

### Phase 4.1 Persistence and public contracts

- [ ] Add an Alembic migration for model-directory scan state and model-file freshness fields required for reconciliation.
- [ ] Keep `Model`, `ModelFile`, and `Deployment` as separate entities; do not encode deployment state into discovery rows.
- [ ] Add bounded Agent DTOs for advertised roots, root scan results, discovered installations, and Ollama entries.
- [ ] Add public API DTOs for model definitions, physical installations, server references, directory state, and inventory summary.
- [ ] Represent bytes, timestamps, revision, quantization, format, architecture, and nullable metadata without presentation formatting.
- [ ] Exclude filesystem samples, token values, raw config bodies, and collector tracebacks from public responses.

Evidence:

- Migration and schema tests cover upgrade/downgrade, malformed paths, payload limits, nullable metadata, and secret/raw-error exclusion.

### Phase 4.2 Agent directory policy and configuration

- [ ] Add `AI_INFRA_AGENT_ALLOWED_MODEL_DIRECTORIES` as an explicit JSON list of absolute host paths.
- [ ] Add `AI_INFRA_AGENT_DEFAULT_MODEL_DIRECTORY` and require it to resolve inside the allowed list when configured.
- [ ] Add bounded scan interval, maximum depth, maximum installations, and Ollama timeout settings with production-safe defaults.
- [ ] Normalize paths with `Path.resolve(strict=False)`, de-duplicate roots, and reject relative paths or parent/child aliases that weaken policy.
- [ ] Surface configured-but-missing and permission-denied roots as structured collector states without terminating the heartbeat loop.
- [ ] Update `.env.example`, systemd templates, installer guidance, and container examples without adding real host paths.

Evidence:

- Agent configuration tests cover valid multi-root setup, duplicate normalization, invalid relative/default paths, missing roots, and secret-free serialization.

### Phase 4.3 Bounded filesystem scanner

- [ ] Add `collectors/models.py` with pure helpers for root validation, candidate discovery, metadata extraction, and aggregate sizing.
- [ ] Recognize `config.json`, `tokenizer.json`, `generation_config.json`, `*.safetensors`, `*.bin`, and standalone `*.gguf` artifacts.
- [ ] Detect Hugging Face cache layouts and revisions while supporting ordinary local model directories.
- [ ] Parse only bounded JSON metadata and derive architecture, model type, display name, source identity, format, quantization, revision, total bytes, and file count.
- [ ] Aggregate safetensors/bin shards into one physical installation and keep each standalone GGUF path distinct.
- [ ] Skip symlinked directories/files, sockets, devices, unreadable entries, oversized metadata, and candidates outside the resolved root.
- [ ] Return deterministic ordering and collision-resistant identities independent of directory enumeration order.

Evidence:

- Fixture tests cover sharded Safetensors, PyTorch bin, GGUF quantization names, Hugging Face snapshots, nested models, malformed JSON, symlink escape/loop, limits, duplicates, and partial permission failures.

### Phase 4.4 Ollama discovery

- [ ] Add a loopback-only Ollama tags client using a fixed read-only HTTP request and bounded response size/timeout.
- [ ] Map name, digest, size, family, parameter size, quantization level, and modification time into the shared inventory DTO.
- [ ] Use stable `ollama://<name>` physical locations and deterministic source IDs.
- [ ] De-duplicate Ollama entries against repeated tags without merging them with unrelated filesystem installations.
- [ ] Degrade unavailable, malformed, or unsupported Ollama responses to collector status rather than Agent failure.

Evidence:

- Mock-transport tests cover multiple tags, empty inventory, timeout, refused connection, malformed payload, payload limit, and metadata mapping.

### Phase 4.5 Heartbeat persistence and reconciliation

- [ ] Extend `collect_snapshot()` and Agent heartbeat schemas with directory and model inventory results.
- [ ] Keep collection off the async event loop and cache full scans for the configured interval while host/GPU heartbeat frequency remains unchanged.
- [ ] Upsert `ServerModelDirectory`, `Model`, and `ModelFile` rows in one bounded transaction per accepted report.
- [ ] Reconcile absent installations only for roots that completed successfully; preserve last-known rows for failed roots and mark their status stale/error.
- [ ] Update model-file freshness and aggregate the same logical model across multiple servers without losing physical paths.
- [ ] Update server model counts from current physical installations and publish a model inventory event only after commit when inventory changed.

Evidence:

- Persistence tests cover two servers sharing a model, rescans, path moves, failed-root retention, successful removal, Ollama rows, transaction rollback, event-on-change, and no-event-on-identical heartbeat.

### Phase 4.6 Authenticated inventory and directory APIs

- [ ] Add `GET /api/v1/models` with deterministic filters for server, source, format, status, model type, and text search.
- [ ] Add `GET /api/v1/models/{model_id}` with logical definition and all physical locations.
- [ ] Add `GET /api/v1/model-inventory/summary` for logical-model, installation, server, format, and total-byte counts.
- [ ] Add `GET /api/v1/servers/{server_id}/model-directories` for Agent-advertised roots and scan health.
- [ ] Add an Admin-only mutation that selects one default from existing allowed roots; reject arbitrary or unadvertised paths.
- [ ] Extend server detail responses with real model installations while preserving bounded query counts and standard errors.

Evidence:

- API tests cover Admin/Viewer reads, anonymous rejection, Admin-only default changes, invalid/unadvertised paths, filters, 404s, multi-location aggregation, and query ordering.

### Phase 4.7 Web data layer and real inventory views

- [ ] Add same-origin BFF handlers for model inventory, model detail, directory reads, and default-directory mutation.
- [ ] Add Zod-validated DTO mappers, model query keys/hooks, SSE invalidation, and bounded polling fallback.
- [ ] Replace Installed Models mock imports with real API data and server identity embedded in each installation response.
- [ ] Show logical model, physical server/path, aggregate size, format, quantization, revision, freshness, and status in the inventory table.
- [ ] Replace the Server Detail Models tab with that server's real installations and directory scan health.
- [ ] Add an Admin-only default-directory control that offers only Agent-advertised allowed roots.
- [ ] Keep Model Library search/download fixtures isolated until Phase 5 and remove their dependency on mock server records.

Evidence:

- Web tests cover mapping, byte formatting, filter keys, event invalidation, partial/error states, Viewer mutation hiding, and tracked-source scans for Installed Models/Server Detail mock imports.

### Phase 4.8 User-visible states and browser verification

- [ ] Add stable loading, no-configured-directory, no-model, inaccessible-root, stale-inventory, offline-server, and Ollama-unavailable states.
- [ ] Preserve search, filters, sorting, and column choices across background refreshes.
- [ ] Make long repository IDs and filesystem paths wrap or truncate with an accessible full-value affordance.
- [ ] Verify the same logical model appears as separate physical locations on `xiao-cpu` and `xiao-pro6000` fixtures.
- [ ] Verify directory/default controls, model detail, server Model tab, and read-only Viewer behavior by keyboard.
- [ ] Verify no text overflow, overlap, blank state, or hydration error at desktop and mobile viewports.

Evidence:

- Browser checks cover desktop and mobile with multi-location Safetensors, standalone GGUF, Ollama, empty, stale, offline, and scan-error fixtures.

### Phase 4.9 Phase gate

- [ ] Run Web, API, Agent lint/typecheck/tests, package build, and production Web build.
- [ ] Run PostgreSQL migration upgrade/downgrade/upgrade and both Compose configurations.
- [ ] Extend Compose smoke with read-only model fixtures mounted into the Agent container.
- [ ] Verify a real Agent scan reaches Central and appears through API, Web BFF, Installed Models, and Server Detail.
- [ ] Verify successful rescan/removal and failed-root retention behavior.
- [ ] Verify SSE refreshes affected model queries without a full reload and polling recovers after interruption.
- [ ] Run tracked secret, arbitrary-command, unsafe-path, and model mock-dependency scans.
- [ ] Record exact evidence and host-specific items before opening Phase 5.

## Exit acceptance

- [ ] The same logical model can be displayed at distinct physical locations on multiple servers.
- [ ] Each installation exposes server, path, aggregate size, format, quantization, revision, freshness, and status.
- [ ] Safetensors/bin directories, standalone GGUF files, and Ollama tags are discovered correctly.
- [ ] Failed or inaccessible roots remain visible without deleting last-known inventory.
- [ ] Central cannot cause the Agent to inspect any path outside its local allowlist.
- [ ] Installed Models and Server Detail Models no longer depend on model/server mock data.
- [ ] Admin and Viewer authorization boundaries are enforced and inventory events refresh real queries.
- [ ] Phase 0-3 Web/API/Agent/Compose checks still pass.
- [ ] No download, deletion, deployment action, or arbitrary command interface was introduced early.
- [ ] No modification was made to `asus-2024` or `asus-4090`.

Phase 5 must not start until every item above is checked and backed by current command, browser, or runtime output.
