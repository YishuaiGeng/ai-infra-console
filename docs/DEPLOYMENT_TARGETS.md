# Deployment Targets

This document records host roles only. Credentials, private addresses, tokens, and SSH configuration must remain outside Git.

| Host | Intended role | Allowed project actions |
| --- | --- | --- |
| `xiao-pro6000` | Primary AI Infra Console host and optional model storage/runtime node | Install and run the Central stack; register an Agent in Phase 2; store/download models; run deployments after Phase 6 |
| `xiao-cpu` | Model storage/download node | Register an Agent when approved; store/download models; no Central stack unless the deployment plan changes |
| `asus-2024` | Backup server | Inventory reference only; do not install, configure, download models, deploy workloads, or otherwise modify it |
| `asus-4090` | Backup server | Inventory reference only; do not install, configure, download models, deploy workloads, or otherwise modify it |

## Guardrails

- Production deployment targets `xiao-pro6000`.
- Model downloads may target only `xiao-pro6000` or `xiao-cpu` by default.
- The two ASUS hosts are denied mutation actions unless the maintainer explicitly changes this policy.
- Host allowlists will be enforced in backend/Agent authorization before real download or deployment actions are introduced.
- The repository must contain example host names only, never their credentials or private connection details.
