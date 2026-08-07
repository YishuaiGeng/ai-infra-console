from datetime import UTC, datetime

from ai_infra_api.core.security import create_agent_token
from ai_infra_api.db.models import ServerAgent


def rotate_agent_token(agent: ServerAgent) -> str:
    token, token_hash = create_agent_token()
    agent.token_hash = token_hash
    agent.revoked_at = None
    return token


def revoke_agent_token(agent: ServerAgent) -> None:
    agent.revoked_at = datetime.now(UTC)
