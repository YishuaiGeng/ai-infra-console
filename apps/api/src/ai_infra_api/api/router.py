from fastapi import APIRouter

from ai_infra_api.api.activity import router as activity_router
from ai_infra_api.api.agent import router as agent_router
from ai_infra_api.api.api_resources import router as api_resources_router
from ai_infra_api.api.auth import router as auth_router
from ai_infra_api.api.deployments import router as deployments_router
from ai_infra_api.api.downloads import router as downloads_router
from ai_infra_api.api.infrastructure import router as infrastructure_router
from ai_infra_api.api.models import router as models_router
from ai_infra_api.api.monitoring import router as monitoring_router
from ai_infra_api.api.servers import router as servers_router
from ai_infra_api.api.settings import router as settings_router
from ai_infra_api.db.models import User
from ai_infra_api.dependencies import CurrentUser

api_router = APIRouter()
api_router.include_router(activity_router)
api_router.include_router(api_resources_router)
api_router.include_router(auth_router)
api_router.include_router(servers_router)
api_router.include_router(agent_router)
api_router.include_router(infrastructure_router)
api_router.include_router(models_router)
api_router.include_router(downloads_router)
api_router.include_router(deployments_router)
api_router.include_router(monitoring_router)
api_router.include_router(settings_router)


@api_router.get("")
async def api_index(user: CurrentUser) -> dict[str, str]:
    authenticated_user: User = user
    return {
        "name": "AI Infra Console API",
        "version": "v1",
        "authenticated_as": authenticated_user.username,
    }
