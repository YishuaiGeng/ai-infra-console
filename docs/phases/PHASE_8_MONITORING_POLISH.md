# Phase 8: Monitoring Polish

## Status

- State: Complete in code as of 2026-08-10.
- Entry gate: Phase 3 infrastructure telemetry and Phase 6 deployment/runtime status are available in Central.
- Exit gate: Activity, metric history, notifications, and retention cleanup are backed by real Central data.
- Scope boundary: this phase adds monitoring persistence and console notifications. It does not introduce direct host polling from the browser or inbound Agent access.

## Implementation Evidence

- Agent heartbeats persist server metric samples and GPU metric samples in Central.
- Alembic migration `f2c91b5e8a44_monitoring_history.py` adds historical server metric storage.
- Central exposes `GET /api/v1/metrics/history` for server CPU/RAM/disk and GPU utilization/VRAM/temperature/power history.
- Central exposes `GET /api/v1/notifications` for derived and stored notifications.
- Notifications cover offline servers, low disk, high GPU temperature, near-full VRAM, failed downloads, failed deployments, and stored notification records.
- Dashboard includes a compact 24-hour resource trend panel backed by Agent metric samples.
- Header notification menu reads real monitoring notifications.
- `/activity` reads real audit rows and filters sensitive detail keys before returning data.
- Retention cleanup removes stale metric samples using `metrics_retention_days`.

## Acceptance

- [x] GPU historical metrics are persisted and exposed through Central.
- [x] Server historical metrics are persisted and exposed through Central.
- [x] Notifications are generated from real infrastructure/deployment/task state.
- [x] Activity logs use real audited Central events.
- [x] Dashboard and header monitoring surfaces use real API hooks.
- [x] Production monitoring/activity UI has no dependency on monitoring or activity mock fixtures.
- [x] Metric retention is configurable and enforced during telemetry persistence.

## Verification

- `npm run check` passes Web lint, typecheck, tests, production build, API lint/typecheck/tests, Agent lint/typecheck/tests, and the security scan.
- API tests cover telemetry persistence and migration coverage for the monitoring history table.
- Web tests cover monitoring DTO mapping for metric history and notifications.
