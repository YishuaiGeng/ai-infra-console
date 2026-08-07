# Agent Operations

The Phase 2 Agent makes outbound requests to the Central API. It does not listen on an inbound port and does not provide a shell or arbitrary command endpoint.

## Provision a token

Sign in as an Admin and create a server registration with `POST /api/v1/servers/registrations`. The response shows the registration token once. Central stores only its SHA-256 digest.

Set these values on the Agent host without committing them:

```bash
AI_INFRA_AGENT_ENVIRONMENT=production
AI_INFRA_AGENT_CENTRAL_URL=https://infra.example.com
AI_INFRA_AGENT_TOKEN=replace-with-issued-token
AI_INFRA_AGENT_HEARTBEAT_SECONDS=10
AI_INFRA_AGENT_TLS_VERIFY=true
```

Production mode requires HTTPS and TLS certificate verification. Keep `/etc/ai-infra-console/agent.env` readable only by root and the `ai-infra-agent` group.

## Inspect before service installation

```bash
ai-infra-agent validate-config
ai-infra-agent collect
ai-infra-agent register
ai-infra-agent heartbeat
```

`collect` is safe on CPU-only hosts. Missing NVML, `nvidia-smi`, Docker, or Ollama is represented as an unavailable collector instead of terminating the Agent.

## Install with systemd

Build the wheel from a reviewed checkout, transfer it to the target host, and run:

```bash
sudo ./scripts/install-agent.sh ./dist/ai_infra_console_agent-0.1.0-py3-none-any.whl
sudoedit /etc/ai-infra-console/agent.env
sudo systemctl enable --now ai-infra-agent
systemctl status ai-infra-agent
journalctl -u ai-infra-agent -n 100 --no-pager
```

The included unit runs as the dedicated `ai-infra-agent` user with filesystem and privilege hardening. GPU device access remains a host-level deployment responsibility.

## Rotate or revoke

- Rotate: `POST /api/v1/servers/{server_id}/agent-token`, update the Agent environment file, then restart the service.
- Revoke: `POST /api/v1/servers/{server_id}/agent-token/revoke`. Subsequent reports receive HTTP 401 and the Agent stops retrying.

Tokens and private host records must never be added to `.env.example`, logs, screenshots, issue reports, or Git.
