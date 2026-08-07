# AI Infra Console Agent

The Agent collects host, NVIDIA GPU, and locally allowed model inventory, then sends outbound registration and heartbeat requests to the Central API. It does not open an inbound management port or expose arbitrary command execution.

Model scanning is disabled until `AI_INFRA_AGENT_ALLOWED_MODEL_DIRECTORIES` is set to a JSON array of absolute paths. The scanner reads only bounded metadata and file sizes, does not read model weight contents, does not traverse directory symlinks, and rejects file symlinks that resolve outside an allowed root. Ollama discovery uses the read-only loopback tags API.

The packaged systemd unit exposes `/data`, `/mnt`, and `/home/share` as read-only locations. Use a host-specific systemd drop-in when an allowed model root lives elsewhere; do not weaken the service to grant write access for inventory scanning.

Phase 2 operating instructions are tracked in [`../../docs/phases/PHASE_2_AGENT.md`](../../docs/phases/PHASE_2_AGENT.md), and model inventory work is tracked in [`../../docs/phases/PHASE_4_MODEL_INVENTORY.md`](../../docs/phases/PHASE_4_MODEL_INVENTORY.md).
