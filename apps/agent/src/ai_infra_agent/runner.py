import asyncio
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Protocol

import httpx

from ai_infra_agent.client import AgentAuthenticationError, CentralRequestError
from ai_infra_agent.schemas import AgentReportResponse, AgentSnapshot

logger = logging.getLogger(__name__)


class Reporter(Protocol):
    async def register(self, snapshot: AgentSnapshot) -> AgentReportResponse: ...

    async def heartbeat(self, snapshot: AgentSnapshot) -> AgentReportResponse: ...


class TaskSupervisor(Protocol):
    async def tick(self) -> None: ...

    def stop(self) -> None: ...

    async def wait(self) -> None: ...


class TaskSupervisorGroup:
    def __init__(self, *supervisors: TaskSupervisor) -> None:
        self._supervisors = supervisors

    async def tick(self) -> None:
        for supervisor in self._supervisors:
            await supervisor.tick()

    def stop(self) -> None:
        for supervisor in self._supervisors:
            supervisor.stop()

    async def wait(self) -> None:
        await asyncio.gather(*(supervisor.wait() for supervisor in self._supervisors))


async def wait_for_stop(delay: float, stop_event: asyncio.Event) -> None:
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=delay)
    except TimeoutError:
        pass


class AgentRunner:
    def __init__(
        self,
        reporter: Reporter,
        collector: Callable[[], AgentSnapshot],
        *,
        heartbeat_seconds: float,
        stop_event: asyncio.Event | None = None,
        waiter: Callable[[float, asyncio.Event], Awaitable[None]] = wait_for_stop,
        random_value: Callable[[], float] = random.random,
        task_supervisor: TaskSupervisor | None = None,
    ) -> None:
        self._reporter = reporter
        self._collector = collector
        self._heartbeat_seconds = heartbeat_seconds
        self._stop_event = stop_event or asyncio.Event()
        self._waiter = waiter
        self._random_value = random_value
        self._task_supervisor = task_supervisor

    def stop(self) -> None:
        self._stop_event.set()
        if self._task_supervisor is not None:
            self._task_supervisor.stop()

    async def run(self) -> None:
        registered = False
        failures = 0
        while not self._stop_event.is_set():
            snapshot = await asyncio.to_thread(self._collector)
            try:
                if registered:
                    await self._reporter.heartbeat(snapshot)
                else:
                    await self._reporter.register(snapshot)
                    registered = True
                if self._task_supervisor is not None:
                    await self._task_supervisor.tick()
                failures = 0
                delay = self._heartbeat_seconds
            except AgentAuthenticationError:
                logger.error(
                    "Agent authentication rejected; stopping",
                    extra={"event": "agent.authentication.rejected"},
                )
                raise
            except (httpx.HTTPError, CentralRequestError) as exc:
                failures += 1
                base_delay = min(60.0, float(2 ** min(failures, 5)))
                delay = base_delay + self._random_value() * min(1.0, base_delay * 0.2)
                logger.warning(
                    "Central API unavailable; retrying",
                    extra={
                        "event": "agent.report.retry",
                        "attempt": failures,
                        "retry_seconds": round(delay, 2),
                    },
                    exc_info=exc,
                )
            await self._waiter(delay, self._stop_event)
        if self._task_supervisor is not None:
            self._task_supervisor.stop()
            await self._task_supervisor.wait()
