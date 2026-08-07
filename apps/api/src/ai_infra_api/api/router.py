from fastapi import APIRouter

from ai_infra_api.api.auth import router as auth_router
from ai_infra_api.db.models import User
from ai_infra_api.dependencies import CurrentUser

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("")
async def api_index(user: CurrentUser) -> dict[str, str]:
    authenticated_user: User = user
    return {
        "name": "AI Infra Console API",
        "version": "v1",
        "authenticated_as": authenticated_user.username,
    }
