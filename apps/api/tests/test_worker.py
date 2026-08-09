from collections.abc import Callable
from typing import cast

from fakeredis import FakeRedis
from rq import Queue, SimpleWorker
from rq.job import JobStatus

from ai_infra_api.worker import health_probe


def test_worker_processes_health_probe() -> None:
    connection = FakeRedis()
    queue = Queue("test", connection=connection)
    job = queue.enqueue(health_probe, {"source": "phase-1-test"})
    worker = SimpleWorker([queue], connection=connection)

    assert worker.work(burst=True) is True
    cast(Callable[[], None], job.refresh)()
    assert job.get_status() == JobStatus.FINISHED
    result = job.return_value()
    assert isinstance(result, dict)
    assert result["status"] == "ok"
    assert result["payload"] == {"source": "phase-1-test"}
