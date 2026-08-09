from datetime import UTC, datetime

from ai_infra_agent import __version__
from ai_infra_agent.collectors.models import collect_model_inventory
from ai_infra_agent.collectors.nvidia import collect_gpu_snapshot
from ai_infra_agent.collectors.runtimes import collect_runtime_snapshot
from ai_infra_agent.collectors.system import collect_host_snapshot
from ai_infra_agent.config import AgentSettings, get_settings
from ai_infra_agent.schemas import AgentSnapshot, CollectorStatus, GPUSnapshot


def collect_snapshot(settings: AgentSettings | None = None) -> AgentSnapshot:
    resolved_settings = settings or get_settings()
    runtimes = collect_runtime_snapshot()
    runtimes.deployment_enabled = resolved_settings.enable_deployments
    if resolved_settings.deployment_runtime_fixture:
        runtimes.docker = CollectorStatus(available=True, version="fixture")
    host = collect_host_snapshot(runtimes)
    if resolved_settings.deployment_gpu_fixture:
        gpus = [
            GPUSnapshot(
                index=0,
                uuid="GPU-ai-infra-fixture-0",
                name="NVIDIA Fixture GPU",
                memory_total=24 * 1024**3,
                memory_used=1024**3,
                utilization=2,
                driver_version="fixture",
                cuda_version="fixture",
            )
        ]
        gpu_collector = CollectorStatus(available=True, version="fixture")
    else:
        gpus, gpu_collector = collect_gpu_snapshot()
    model_inventory = collect_model_inventory(
        resolved_settings,
        ollama_available=runtimes.ollama.available,
    )
    return AgentSnapshot(
        collected_at=datetime.now(UTC),
        agent_version=__version__,
        host=host,
        gpus=gpus,
        gpu_collector=gpu_collector,
        model_inventory=model_inventory,
    )
