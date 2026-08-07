from datetime import UTC, datetime

from ai_infra_agent import __version__
from ai_infra_agent.collectors.nvidia import collect_gpu_snapshot
from ai_infra_agent.collectors.runtimes import collect_runtime_snapshot
from ai_infra_agent.collectors.system import collect_host_snapshot
from ai_infra_agent.schemas import AgentSnapshot


def collect_snapshot() -> AgentSnapshot:
    runtimes = collect_runtime_snapshot()
    host = collect_host_snapshot(runtimes)
    gpus, gpu_collector = collect_gpu_snapshot()
    return AgentSnapshot(
        collected_at=datetime.now(UTC),
        agent_version=__version__,
        host=host,
        gpus=gpus,
        gpu_collector=gpu_collector,
    )
