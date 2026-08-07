import sys
from datetime import UTC, datetime
from typing import Any

from redis import Redis
from rq import Queue, SimpleWorker, Worker

from ai_infra_api.core.config import Settings, get_settings
from ai_infra_api.core.logging import configure_logging


def health_probe(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a serializable result used to verify the worker path."""
    return {
        "status": "ok",
        "processed_at": datetime.now(UTC).isoformat(),
        "payload": payload or {},
    }


def redis_connection(settings: Settings) -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=False)


def enqueue_health_probe(payload: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    queue = Queue(settings.redis_queue_name, connection=redis_connection(settings))
    job = queue.enqueue(health_probe, payload or {}, job_timeout=30, result_ttl=300)
    return job.id


def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    connection = redis_connection(settings)
    worker_class = SimpleWorker if sys.platform == "win32" else Worker
    worker = worker_class([settings.redis_queue_name], connection=connection)
    worker.work(with_scheduler=False)


if __name__ == "__main__":
    run()
