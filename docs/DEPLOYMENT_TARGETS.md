# Deployment Targets

This document describes the recommended host-role model for a self-hosted AI Infra Console deployment. It must contain example host names only. Credentials, private addresses, provider tokens, registration tokens, and SSH configuration belong in local secret storage, never in Git.

| Example host | Intended role | Allowed actions |
| --- | --- | --- |
| `gpu-node-01` | Central host and optional GPU runtime node | Run the Central stack, register an Agent, store/download models, and run deployments when explicitly allowlisted |
| `storage-node-01` | Model storage or download node | Register an Agent and store/download models when explicitly allowlisted |
| `backup-node-01` | Backup or inventory-only server | Read-only inventory reference unless the operator intentionally changes policy |
| `backup-node-02` | Backup or inventory-only server | Read-only inventory reference unless the operator intentionally changes policy |

## Guardrails

- Put only servers that may receive model or deployment mutations in `AI_INFRA_MUTABLE_SERVER_NAMES`.
- Keep backup, read-only, and inventory-only servers out of mutation allowlists.
- Enable Agent model mutations and deployment control independently on each managed server.
- Pin reviewed runtime images before enabling deployment control.
- Never commit real hostnames if they reveal private infrastructure.
