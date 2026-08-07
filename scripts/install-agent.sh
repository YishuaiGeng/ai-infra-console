#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer as root." >&2
  exit 1
fi

if [[ "$#" -ne 1 ]]; then
  echo "Usage: $0 /path/to/ai_infra_console_agent.whl" >&2
  exit 1
fi

wheel_path="$1"
if [[ ! -f "$wheel_path" ]]; then
  echo "Agent wheel not found: $wheel_path" >&2
  exit 1
fi

id -u ai-infra-agent >/dev/null 2>&1 || useradd --system --home /nonexistent --shell /usr/sbin/nologin ai-infra-agent
install -d -m 0755 /opt/ai-infra-agent
python3 -m venv /opt/ai-infra-agent
/opt/ai-infra-agent/bin/pip install --disable-pip-version-check "$wheel_path"

install -d -m 0750 -o root -g ai-infra-agent /etc/ai-infra-console
if [[ ! -f /etc/ai-infra-console/agent.env ]]; then
  install -m 0640 -o root -g ai-infra-agent deploy/systemd/agent.env.example /etc/ai-infra-console/agent.env
fi
install -m 0644 deploy/systemd/ai-infra-agent.service /etc/systemd/system/ai-infra-agent.service
systemctl daemon-reload

echo "Edit /etc/ai-infra-console/agent.env, then run: systemctl enable --now ai-infra-agent"
