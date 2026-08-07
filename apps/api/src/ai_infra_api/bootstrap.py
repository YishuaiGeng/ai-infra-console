import asyncio

from ai_infra_api.core.config import get_settings
from ai_infra_api.core.logging import configure_logging
from ai_infra_api.db.session import Database
from ai_infra_api.services.bootstrap import bootstrap_admin


async def bootstrap() -> bool:
    settings = get_settings()
    configure_logging(settings.log_level)
    database = Database(settings.database_url)
    try:
        async with database.session_factory() as session:
            return await bootstrap_admin(session, settings)
    finally:
        await database.close()


def run() -> None:
    asyncio.run(bootstrap())


if __name__ == "__main__":
    run()
