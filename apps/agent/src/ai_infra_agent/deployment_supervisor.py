import asyncio
import logging
import time
from typing import Literal, Protocol, cast

from ai_infra_agent.client import CentralRequestError
from ai_infra_agent.deployment_runtime import (
    DeploymentExecutionError,
    DeploymentRuntime,
)
from ai_infra_agent.schemas import (
    DeploymentCommand,
    DeploymentRuntimeExpectation,
    DeploymentRuntimeObservation,
)

logger = logging.getLogger(__name__)


class DeploymentReporter(Protocol):
    async def claim_deployment_task(self) -> DeploymentCommand | None: ...

    async def renew_deployment_operation(self, command: DeploymentCommand) -> object: ...

    async def complete_deployment_operation(
        self,
        command: DeploymentCommand,
        *,
        outcome: Literal["completed", "failed"],
        observed_state: Literal["running", "stopped", "missing", "failed"],
        container_id: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None: ...

    async def deployment_runtime_expectations(self) -> list[DeploymentRuntimeExpectation]: ...

    async def report_deployment_runtimes(
        self,
        observations: list[DeploymentRuntimeObservation],
    ) -> None: ...


class DeploymentSupervisor:
    def __init__(
        self,
        reporter: DeploymentReporter,
        runtime: DeploymentRuntime,
        *,
        progress_seconds: float,
        reconcile_seconds: float,
    ) -> None:
        self._reporter = reporter
        self._runtime = runtime
        self._progress_seconds = progress_seconds
        self._reconcile_seconds = reconcile_seconds
        self._last_reconcile = 0.0
        self._active: asyncio.Task[None] | None = None
        self._stopping = False

    async def tick(self) -> None:
        if self._active is not None and self._active.done():
            try:
                await self._active
            except Exception:
                logger.exception(
                    "deployment supervisor failed",
                    extra={"event": "agent.deployment.supervisor_failed"},
                )
            self._active = None
        if self._stopping:
            return
        now = time.monotonic()
        if self._active is None:
            try:
                command = await self._reporter.claim_deployment_task()
            except CentralRequestError:
                logger.warning(
                    "deployment task claim failed",
                    extra={"event": "agent.deployment.claim_failed"},
                )
            else:
                if command is not None:
                    self._active = asyncio.create_task(self._run(command))
        if now - self._last_reconcile >= self._reconcile_seconds:
            await self._reconcile()
            self._last_reconcile = now

    def stop(self) -> None:
        self._stopping = True

    async def wait(self) -> None:
        if self._active is not None:
            await self._active
        await asyncio.to_thread(self._runtime.close)

    async def _run(self, command: DeploymentCommand) -> None:
        execution = asyncio.create_task(asyncio.to_thread(self._runtime.execute, command))
        while not execution.done():
            done, _ = await asyncio.wait({execution}, timeout=self._progress_seconds)
            if done:
                break
            try:
                await self._reporter.renew_deployment_operation(command)
            except CentralRequestError:
                logger.warning(
                    "deployment lease renewal failed",
                    extra={
                        "event": "agent.deployment.progress_failed",
                        "operation_id": str(command.operation_id),
                    },
                )
        try:
            result = await execution
        except DeploymentExecutionError as exc:
            await self._complete_failure(command, exc.code, exc.public_message)
        except Exception:
            logger.exception(
                "unexpected deployment execution failure",
                extra={
                    "event": "agent.deployment.execution_failed",
                    "operation_id": str(command.operation_id),
                },
            )
            await self._complete_failure(
                command,
                "deployment_executor_failure",
                "The Agent deployment executor failed unexpectedly.",
            )
        else:
            state = cast(Literal["running", "stopped", "missing", "failed"], result.state)
            try:
                await self._reporter.complete_deployment_operation(
                    command,
                    outcome="completed",
                    observed_state=state,
                    container_id=result.container_id,
                )
            except CentralRequestError:
                logger.warning(
                    "deployment completion report failed",
                    extra={
                        "event": "agent.deployment.completion_failed",
                        "operation_id": str(command.operation_id),
                    },
                )

    async def _complete_failure(
        self,
        command: DeploymentCommand,
        error_code: str,
        error_message: str,
    ) -> None:
        try:
            await self._reporter.complete_deployment_operation(
                command,
                outcome="failed",
                observed_state="failed",
                error_code=error_code,
                error_message=error_message,
            )
        except CentralRequestError:
            logger.warning(
                "deployment failure report failed",
                extra={
                    "event": "agent.deployment.completion_failed",
                    "operation_id": str(command.operation_id),
                },
            )

    async def _reconcile(self) -> None:
        try:
            expectations = await self._reporter.deployment_runtime_expectations()
            observations = await asyncio.to_thread(self._runtime.observe, expectations)
            await self._reporter.report_deployment_runtimes(observations)
        except CentralRequestError:
            logger.warning(
                "deployment reconciliation failed",
                extra={"event": "agent.deployment.reconcile_failed"},
            )
        except DeploymentExecutionError:
            logger.exception(
                "deployment runtime observation failed",
                extra={"event": "agent.deployment.observe_failed"},
            )
