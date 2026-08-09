# Phase 7: API Endpoints

## Status

- State: Complete in code as of 2026-08-10.
- Entry gate: Phase 6 deployment lifecycle exposes running vLLM deployments with endpoint, health, and model metadata.
- Exit gate: `/apis` uses real Central deployment data, exposes OpenAI-compatible endpoint information, and tests only an existing deployment endpoint through Central.
- Scope boundary: this phase exposes and tests managed deployment endpoints. It does not add an arbitrary HTTP client, generic proxy, or user-submitted endpoint URL.

## Implementation Evidence

- Central exposes `POST /api/v1/deployments/{deployment_id}/test-api` for authenticated endpoint testing.
- The test API service rejects non-running deployments, builds a bounded `/v1/chat/completions` request, applies a timeout, parses OpenAI-compatible response fields, and returns safe error messages.
- Web BFF route `apps/web/src/app/api/deployments/[id]/test-api/route.ts` forwards only deployment-scoped test requests under the existing HttpOnly session.
- `/apis` lists running deployment endpoints from `useDeployments()` rather than `mocks/data.ts`.
- Endpoint cards show base URL, `/models`, `/chat/completions`, model source ID, server, backend, port, deployment status, Agent health, latency, last health check, and generation.
- Copy actions are limited to the deployment endpoint and model name. Test requests cannot target arbitrary URLs from the browser.

## Acceptance

- [x] Model, endpoint, server, backend, status, port, and actions are visible on `/apis`.
- [x] OpenAI-compatible information includes the `/v1` base URL and common request paths.
- [x] Endpoint health comes from Agent runtime reports stored on the deployment row.
- [x] API Test dialog uses form validation for prompt, max tokens, and temperature.
- [x] API Test dialog resets stale mutation state when closed.
- [x] Long model names and URLs wrap or truncate without page-level overflow.
- [x] Production endpoint UI has no dependency on endpoint mock fixtures.
- [x] The implementation preserves the no-generic-proxy and no-arbitrary-command security boundaries.

## Verification

- `npm run check` passes Web lint, typecheck, tests, production build, API lint/typecheck/tests, Agent lint/typecheck/tests, and the security scan.
- `rg -n 'from\s+["'']@/mocks|mocks/data' apps\web\src` returns no production mock imports.
