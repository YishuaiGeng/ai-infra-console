import argparse
import asyncio
import json

from ai_infra_agent import __version__
from ai_infra_agent.client import CentralClient
from ai_infra_agent.collectors import collect_snapshot
from ai_infra_agent.config import get_settings
from ai_infra_agent.logging import configure_logging
from ai_infra_agent.runner import AgentRunner


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="ai-infra-agent")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "validate-config", help="Validate Agent environment configuration."
    )
    commands.add_parser("collect", help="Collect and print one hardware snapshot.")
    commands.add_parser("register", help="Register once and print the assigned server ID.")
    commands.add_parser("heartbeat", help="Send one heartbeat and print the assigned server ID.")
    commands.add_parser("run", help="Run the registration and heartbeat loop.")
    return root


async def async_command(command: str) -> None:
    settings = get_settings()
    if command == "collect":
        print(json.dumps(collect_snapshot().model_dump(mode="json"), indent=2, sort_keys=True))
        return
    async with CentralClient(settings) as client:
        if command == "register":
            result = await client.register(await asyncio.to_thread(collect_snapshot))
            print(str(result.server_id))
            return
        if command == "heartbeat":
            result = await client.heartbeat(await asyncio.to_thread(collect_snapshot))
            print(str(result.server_id))
            return
        runner = AgentRunner(
            client,
            collect_snapshot,
            heartbeat_seconds=settings.heartbeat_seconds,
        )
        await runner.run()


def run() -> None:
    arguments = parser().parse_args()
    settings = get_settings()
    configure_logging(settings.log_level)
    if arguments.command == "validate-config":
        print(f"configuration valid for {settings.central_api_url}")
        return
    try:
        asyncio.run(async_command(arguments.command))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    run()
