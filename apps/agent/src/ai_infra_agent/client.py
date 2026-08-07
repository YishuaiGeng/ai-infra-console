import logging
from typing import Literal
from uuid import uuid4

import httpx
from pydantic import SecretStr

from ai_infra_agent.config import AgentSettings
from ai_infra_agent.schemas import (
    AgentReportResponse,
    AgentSnapshot,
    DeleteTaskCommand,
    DownloadProgressResponse,
    DownloadTaskCommand,
    ModelTaskClaimResponse,
    ModelTaskCommand,
)

logger = logging.getLogger(__name__)


class AgentAuthenticationError(RuntimeError):
    pass


class CentralRequestError(RuntimeError):
    pass


class CentralClient:
    def __init__(
        self,
        settings: AgentSettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if settings.token is None:
            raise ValueError("AI_INFRA_AGENT_TOKEN is required")
        self._token: SecretStr = settings.token
        self._client = httpx.AsyncClient(
            base_url=settings.central_api_url,
            timeout=httpx.Timeout(settings.request_timeout_seconds),
            verify=settings.tls_verify,
            transport=transport,
            headers={"user-agent": "ai-infra-console-agent"},
        )

    async def __aenter__(self) -> "CentralClient":
        return self

    async def __aexit__(self, *_args: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def register(self, snapshot: AgentSnapshot) -> AgentReportResponse:
        return await self._report("/api/v1/agent/register", snapshot)

    async def heartbeat(self, snapshot: AgentSnapshot) -> AgentReportResponse:
        return await self._report("/api/v1/agent/heartbeat", snapshot)

    async def claim_model_task(self) -> ModelTaskCommand | None:
        response = await self._request("POST", "/api/v1/agent/model-tasks/claim")
        return ModelTaskClaimResponse.model_validate(response.json()).task

    async def report_download_progress(
        self,
        command: DownloadTaskCommand,
        *,
        downloaded_size: int,
        total_size: int | None,
        speed_bytes_per_second: int | None,
    ) -> DownloadProgressResponse:
        response = await self._request(
            "POST",
            f"/api/v1/agent/download-tasks/{command.task_id}/progress",
            json={
                "lease_token": command.lease_token.get_secret_value(),
                "downloaded_size": downloaded_size,
                "total_size": total_size,
                "speed_bytes_per_second": speed_bytes_per_second,
            },
        )
        return DownloadProgressResponse.model_validate(response.json())

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
    ) -> None:
        await self._request(
            "POST",
            f"/api/v1/agent/download-tasks/{command.task_id}/complete",
            json={
                "lease_token": command.lease_token.get_secret_value(),
                "outcome": outcome,
                "downloaded_size": downloaded_size,
                "total_size": total_size,
                "final_path": final_path,
                "error_code": error_code,
                "error_message": error_message,
            },
        )

    async def complete_delete_task(
        self,
        command: DeleteTaskCommand,
        *,
        outcome: Literal["completed", "failed"],
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        await self._request(
            "POST",
            f"/api/v1/agent/delete-tasks/{command.task_id}/complete",
            json={
                "lease_token": command.lease_token.get_secret_value(),
                "outcome": outcome,
                "error_code": error_code,
                "error_message": error_message,
            },
        )

    async def _report(self, path: str, snapshot: AgentSnapshot) -> AgentReportResponse:
        response = await self._request(
            "POST",
            path,
            json=snapshot.model_dump(mode="json"),
        )
        logger.info(
            "Agent report accepted",
            extra={"event": "agent.report.accepted"},
        )
        return AgentReportResponse.model_validate(response.json())

    async def _request(
        self,
        method: Literal["POST"],
        path: str,
        *,
        json: dict[str, object] | None = None,
    ) -> httpx.Response:
        request_id = str(uuid4())
        try:
            response = await self._client.request(
                method,
                path,
                headers={
                    "authorization": f"Bearer {self._token.get_secret_value()}",
                    "x-request-id": request_id,
                },
                json=json,
            )
            response.raise_for_status()
        except httpx.RequestError as exc:
            raise CentralRequestError(
                f"Central API request failed ({type(exc).__name__})"
            ) from None
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in {401, 403}:
                raise AgentAuthenticationError(
                    f"Central API rejected Agent authentication ({exc.response.status_code})"
                ) from exc
            raise CentralRequestError(
                f"Central API returned HTTP {exc.response.status_code}"
            ) from exc
        return response
