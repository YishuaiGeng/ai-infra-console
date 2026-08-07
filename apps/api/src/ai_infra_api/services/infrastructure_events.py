import json
import logging
import time
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Literal

from fastapi import Request
from pydantic import ValidationError
from redis.asyncio import Redis

from ai_infra_api.schemas.infrastructure import InfrastructureEvent

logger = logging.getLogger(__name__)

INFRASTRUCTURE_EVENT_CHANNEL = "ai-infra-console:infrastructure:v1"


async def _publish_update(
    redis: Redis,
    server_id: uuid.UUID,
    kind: Literal["server.updated", "server.offline", "model.inventory.updated"],
) -> None:
    event = InfrastructureEvent(
        id=str(uuid.uuid4()),
        kind=kind,
        server_id=server_id,
        occurred_at=datetime.now(UTC),
    )
    try:
        await redis.publish(INFRASTRUCTURE_EVENT_CHANNEL, event.model_dump_json())
    except Exception:
        logger.warning(
            "infrastructure event publish failed",
            extra={"event": "infrastructure.publish_failed", "server_id": str(server_id)},
            exc_info=True,
        )


async def publish_server_update(redis: Redis, server_id: uuid.UUID) -> None:
    await _publish_update(redis, server_id, "server.updated")


async def publish_model_inventory_update(redis: Redis, server_id: uuid.UUID) -> None:
    await _publish_update(redis, server_id, "model.inventory.updated")


def encode_sse(event: InfrastructureEvent) -> str:
    data = json.dumps(event.model_dump(mode="json"), separators=(",", ":"))
    return f"id: {event.id}\nevent: infrastructure\ndata: {data}\n\n"


async def stream_infrastructure_events(
    request: Request,
    redis: Redis,
    *,
    keepalive_seconds: float = 15.0,
) -> AsyncIterator[str]:
    pubsub = redis.pubsub()
    subscribed = False
    last_sent = time.monotonic()
    try:
        try:
            await pubsub.subscribe(INFRASTRUCTURE_EVENT_CHANNEL)
            subscribed = True
        except Exception:
            logger.warning(
                "infrastructure event subscription failed",
                extra={"event": "infrastructure.subscription_failed"},
                exc_info=True,
            )
            yield "retry: 5000\n\n"
            return
        yield "retry: 5000\n\n"
        while not await request.is_disconnected():
            try:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=min(1.0, keepalive_seconds),
                )
            except Exception:
                logger.warning(
                    "infrastructure event stream disconnected",
                    extra={"event": "infrastructure.stream_disconnected"},
                    exc_info=True,
                )
                return
            if message is not None:
                try:
                    event = InfrastructureEvent.model_validate_json(message["data"])
                except (KeyError, TypeError, ValidationError):
                    logger.warning(
                        "invalid infrastructure event ignored",
                        extra={"event": "infrastructure.invalid_event"},
                    )
                else:
                    yield encode_sse(event)
                    last_sent = time.monotonic()
            if time.monotonic() - last_sent >= keepalive_seconds:
                yield ": keepalive\n\n"
                last_sent = time.monotonic()
    finally:
        if subscribed:
            await pubsub.unsubscribe(INFRASTRUCTURE_EVENT_CHANNEL)
        await pubsub.aclose()
