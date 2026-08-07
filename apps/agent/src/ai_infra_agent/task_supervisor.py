import asyncio
import logging
import threading
from typing import Literal, Protocol

from ai_infra_agent.client import CentralRequestError
from ai_infra_agent.model_tasks import (
    DownloadProgress,
    ModelTaskCancelled,
    ModelTaskExecutionError,
    ModelTaskExecutor,
)
from ai_infra_agent.schemas import (
    DeleteTaskCommand,
    DownloadProgressResponse,
    DownloadTaskCommand,
    ModelTaskCommand,
)

logger = logging.getLogger(__name__)


class ModelTaskReporter(Protocol):
    async def claim_model_task(self) -> ModelTaskCommand | None: ...

    async def report_download_progress(
        self,
        command: DownloadTaskCommand,
        *,
        downloaded_size: int,
        total_size: int | None,
        speed_bytes_per_second: int | None,
    ) -> DownloadProgressResponse: ...

    async def complete_download_task(
        self,
        command: DownloadTaskCommand,
        *,
        outcome: Literal["completed", "failed", "cancelled"],
        downloaded_size: int,
        total_size: int | None,
        final_path: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None: ...

    async def complete_delete_task(
        self,
        command: DeleteTaskCommand,
        *,
        outcome: Literal["completed", "failed"],
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None: ...


class ModelTaskSupervisor:
    def __init__(
        self,
        reporter: ModelTaskReporter,
        executor: ModelTaskExecutor,
        *,
        progress_seconds: float,
    ) -> None:
        self._reporter = reporter
        self._executor = executor
        self._progress_seconds = progress_seconds
        self._active: asyncio.Task[None] | None = None
        self._cancel_event: threading.Event | None = None
        self._stopping = False

    async def tick(self) -> None:
        if self._active is not None and self._active.done():
            try:
                await self._active
            except Exception:
                logger.exception(
                    "model task supervisor failed",
                    extra={"event": "agent.model_task.supervisor_failed"},
                )
            self._active = None
            self._cancel_event = None
        if self._stopping or self._active is not None:
            return
        try:
            command = await self._reporter.claim_model_task()
        except CentralRequestError:
            logger.warning(
                "model task claim failed",
                extra={"event": "agent.model_task.claim_failed"},
            )
            return
        if command is None:
            return
        self._cancel_event = threading.Event()
        if command.kind == "download":
            self._active = asyncio.create_task(self._run_download(command, self._cancel_event))
        else:
            self._active = asyncio.create_task(self._run_delete(command))

    def stop(self) -> None:
        self._stopping = True
        if self._cancel_event is not None:
            self._cancel_event.set()

    async def wait(self) -> None:
        if self._active is not None:
            await self._active

    async def _run_download(
        self,
        command: DownloadTaskCommand,
        cancel_event: threading.Event,
    ) -> None:
        progress = DownloadProgress()
        execution = asyncio.create_task(
            asyncio.to_thread(
                self._executor.execute_download,
                command,
                progress,
                cancel_event,
            )
        )
        report_failures = 0
        while not execution.done():
            done, _ = await asyncio.wait({execution}, timeout=self._progress_seconds)
            if done:
                break
            snapshot = progress.snapshot()
            try:
                response = await self._reporter.report_download_progress(
                    command,
                    downloaded_size=snapshot.downloaded_size,
                    total_size=snapshot.total_size,
                    speed_bytes_per_second=snapshot.speed_bytes_per_second,
                )
                report_failures = 0
                if response.cancel_requested:
                    cancel_event.set()
            except CentralRequestError:
                report_failures += 1
                logger.warning(
                    "download progress report failed",
                    extra={
                        "event": "agent.model_task.progress_failed",
                        "task_id": str(command.task_id),
                        "attempt": report_failures,
                    },
                )
                if report_failures >= 3:
                    cancel_event.set()
        snapshot = progress.snapshot()
        try:
            result = await execution
        except ModelTaskCancelled:
            await self._complete_download(
                command,
                outcome="cancelled",
                downloaded_size=snapshot.downloaded_size,
                total_size=snapshot.total_size,
                error_code="cancelled",
            )
        except ModelTaskExecutionError as exc:
            await self._complete_download(
                command,
                outcome="failed",
                downloaded_size=snapshot.downloaded_size,
                total_size=snapshot.total_size,
                error_code=exc.code,
                error_message=exc.public_message,
            )
        except Exception:
            logger.exception(
                "unexpected model download failure",
                extra={
                    "event": "agent.model_task.download_failed",
                    "task_id": str(command.task_id),
                },
            )
            await self._complete_download(
                command,
                outcome="failed",
                downloaded_size=snapshot.downloaded_size,
                total_size=snapshot.total_size,
                error_code="executor_failure",
                error_message="The Agent model executor failed unexpectedly.",
            )
        else:
            await self._complete_download(
                command,
                outcome="completed",
                downloaded_size=result.downloaded_size,
                total_size=result.total_size,
                final_path=result.path,
            )

    async def _complete_download(
        self,
        command: DownloadTaskCommand,
        *,
        outcome: Literal["completed", "failed", "cancelled"],
        downloaded_size: int,
        total_size: int | None,
        final_path: str | None = None,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        try:
            await self._reporter.complete_download_task(
                command,
                outcome=outcome,
                downloaded_size=downloaded_size,
                total_size=total_size,
                final_path=final_path,
                error_code=error_code,
                error_message=error_message,
            )
        except CentralRequestError:
            logger.warning(
                "download terminal report failed",
                extra={
                    "event": "agent.model_task.completion_failed",
                    "task_id": str(command.task_id),
                },
            )

    async def _run_delete(self, command: DeleteTaskCommand) -> None:
        try:
            await asyncio.to_thread(self._executor.execute_delete, command)
        except ModelTaskExecutionError as exc:
            await self._complete_delete(
                command,
                outcome="failed",
                error_code=exc.code,
                error_message=exc.public_message,
            )
        except Exception:
            logger.exception(
                "unexpected model deletion failure",
                extra={"event": "agent.model_task.delete_failed", "task_id": str(command.task_id)},
            )
            await self._complete_delete(
                command,
                outcome="failed",
                error_code="executor_failure",
                error_message="The Agent model deletion executor failed unexpectedly.",
            )
        else:
            await self._complete_delete(command, outcome="completed")

    async def _complete_delete(
        self,
        command: DeleteTaskCommand,
        *,
        outcome: Literal["completed", "failed"],
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        try:
            await self._reporter.complete_delete_task(
                command,
                outcome=outcome,
                error_code=error_code,
                error_message=error_message,
            )
        except CentralRequestError:
            logger.warning(
                "deletion terminal report failed",
                extra={
                    "event": "agent.model_task.completion_failed",
                    "task_id": str(command.task_id),
                },
            )
