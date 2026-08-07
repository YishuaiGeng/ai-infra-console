import logging
from uuid import uuid4

import httpx
from pydantic import SecretStr

from ai_infra_agent.config import AgentSettings
from ai_infra_agent.schemas import AgentReportResponse, AgentSnapshot

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

    async def _report(self, path: str, snapshot: AgentSnapshot) -> AgentReportResponse:
        request_id = str(uuid4())
        try:
            response = await self._client.post(
                path,
                headers={
                    "authorization": f"Bearer {self._token.get_secret_value()}",
                    "x-request-id": request_id,
                },
                json=snapshot.model_dump(mode="json"),
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
        logger.info(
            "Agent report accepted",
            extra={"event": "agent.report.accepted", "request_id": request_id},
        )
        return AgentReportResponse.model_validate(response.json())
