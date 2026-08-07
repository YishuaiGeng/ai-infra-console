import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from http.cookies import SimpleCookie
from typing import Any, TypeVar
from urllib.parse import quote_plus

T = TypeVar("T")


def compose_exec(*arguments: str) -> str:
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def compose_run(
    *arguments: str,
    environment: dict[str, str] | None = None,
    environment_variables: tuple[str, ...] = (),
) -> str:
    command = ["docker", "compose", "run", "--rm", "--no-deps"]
    for variable in environment_variables:
        command.extend(("-e", variable))
    command.extend(("api", *arguments))
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        env=environment,
        text=True,
    )
    return result.stdout.strip()


def postgres_exec(*arguments: str) -> str:
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "postgres", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def compose_agent(
    command: str,
    token: str,
    *,
    build: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["AI_INFRA_AGENT_TOKEN"] = token
    arguments = ["docker", "compose", "--profile", "agent", "run", "--rm", "--no-deps"]
    if build:
        arguments.append("--build")
    arguments.extend(("-e", "AI_INFRA_AGENT_TOKEN", "agent", "ai-infra-agent", command))
    result = subprocess.run(
        arguments,
        check=False,
        capture_output=True,
        env=environment,
        text=True,
        timeout=120,
    )
    if check and result.returncode != 0:
        output = result.stderr.strip() or result.stdout.strip()
        detail = " | ".join(line.strip() for line in output.splitlines()[-8:] if line.strip())
        raise RuntimeError(f"Agent container {command} failed: {detail[:1800]}")
    return result


def run_check(name: str, check: Callable[[], T]) -> T:
    print(f"[compose-smoke] starting: {name}", flush=True)
    started_at = time.monotonic()
    try:
        result = check()
    except Exception as exc:
        elapsed = time.monotonic() - started_at
        print(
            f"[compose-smoke] failed: {name} ({elapsed:.1f}s): {type(exc).__name__}: {exc}",
            file=sys.stderr,
            flush=True,
        )
        if isinstance(exc, subprocess.CalledProcessError):
            if exc.stdout:
                print(exc.stdout.rstrip(), file=sys.stderr, flush=True)
            if exc.stderr:
                print(exc.stderr.rstrip(), file=sys.stderr, flush=True)
        if isinstance(exc, urllib.error.HTTPError):
            print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr, flush=True)
        raise
    elapsed = time.monotonic() - started_at
    print(f"[compose-smoke] passed: {name} ({elapsed:.1f}s)", flush=True)
    return result


def request_json(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    headers = {"accept": "application/json"}
    data = None
    if payload is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        body = response.read()
        return json.loads(body.decode("utf-8")) if body else {}


def request_status(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    token: str | None = None,
) -> int:
    try:
        request_json(url, method=method, payload=payload, token=token)
    except urllib.error.HTTPError as exc:
        exc.read()
        return exc.code
    return 200


def synthetic_snapshot(
    hostname: str,
    *,
    gpu_count: int,
    process_on_first_gpu: bool = False,
) -> dict[str, Any]:
    now = time.time()
    gpus = []
    for index in range(gpu_count):
        processes = []
        if index == 0 and process_on_first_gpu:
            processes.append(
                {
                    "pid": 4200,
                    "username": "compose-user",
                    "command": "python",
                    "memory_used": 8 * 1024**3,
                }
            )
        gpus.append(
            {
                "index": index,
                "uuid": f"GPU-{hostname}-{index}",
                "name": "NVIDIA Synthetic GPU",
                "memory_total": 24 * 1024**3,
                "memory_used": (8 + index) * 1024**3,
                "utilization": 45 + index,
                "temperature": 55 + index,
                "power_usage": 180 + index,
                "power_limit": 450,
                "fan_speed": 35,
                "driver_version": "580.00",
                "cuda_version": "13.0",
                "processes": processes,
            }
        )
    return {
        "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "agent_version": "0.1.0-compose",
        "host": {
            "hostname": hostname,
            "os": "Linux",
            "kernel": "6.8.0-compose",
            "architecture": "x86_64",
            "boot_time": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600)
            ),
            "cpu": {
                "model": "Compose Test CPU",
                "physical_cores": 8,
                "logical_cores": 16,
                "utilization": 25,
                "load_average": [0.5, 0.4, 0.3],
            },
            "memory": {
                "total": 64 * 1024**3,
                "used": 32 * 1024**3,
                "percent": 50,
            },
            "disks": [
                {
                    "mountpoint": "/models",
                    "filesystem": "ext4",
                    "total": 1024 * 1024**3,
                    "used": 256 * 1024**3,
                    "percent": 25,
                }
            ],
            "network": {"bytes_sent": 1000, "bytes_received": 2000},
            "runtimes": {
                "python": {"available": True, "version": "3.12"},
                "docker": {"available": True, "version": "27"},
                "ollama": {"available": False, "detail": "not installed"},
            },
        },
        "gpus": gpus,
        "gpu_collector": {"available": gpu_count > 0, "version": "synthetic"},
    }


def create_reported_server(
    base_url: str,
    admin_token: str,
    *,
    name: str,
    hostname: str,
    gpu_count: int,
    process_on_first_gpu: bool = False,
) -> dict[str, Any]:
    registration = request_json(
        f"{base_url}/api/v1/servers/registrations",
        method="POST",
        payload={"name": name, "type": "local", "tags": ["compose", "phase-3"]},
        token=admin_token,
    )
    request_json(
        f"{base_url}/api/v1/agent/register",
        method="POST",
        payload=synthetic_snapshot(
            hostname,
            gpu_count=gpu_count,
            process_on_first_gpu=process_on_first_gpu,
        ),
        token=str(registration["registration_token"]),
    )
    return dict(registration)


def backdate_server(server_id: str) -> None:
    code = f"""
import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID
from ai_infra_api.core.config import get_settings
from ai_infra_api.db.models import Server
from ai_infra_api.db.session import Database

async def main():
    database = Database(get_settings().database_url)
    async with database.session_factory() as session:
        server = await session.get(Server, UUID('{server_id}'))
        if server is None:
            raise RuntimeError('server not found')
        server.last_seen = datetime.now(UTC) - timedelta(seconds=60)
        await session.commit()
    await database.close()

asyncio.run(main())
"""
    compose_exec("python", "-c", code)


def create_viewer_token() -> str:
    code = """
import asyncio
from secrets import token_urlsafe
from ai_infra_api.core.config import get_settings
from ai_infra_api.core.security import create_access_token, hash_password
from ai_infra_api.db.models import User, UserRole
from ai_infra_api.db.session import Database

async def main():
    settings = get_settings()
    database = Database(settings.database_url)
    async with database.session_factory() as session:
        user = User(
            username='phase3-compose-viewer',
            password_hash=hash_password(token_urlsafe(32)),
            role=UserRole.VIEWER,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        token, _ = create_access_token(user, settings)
        print(token)
    await database.close()

asyncio.run(main())
"""
    return compose_exec("python", "-c", code)


def verify_sse_event(
    base_url: str,
    user_token: str,
    agent_token: str,
    server_id: str,
) -> dict[str, Any]:
    result: dict[str, Any] = {}

    def consume() -> None:
        request = urllib.request.Request(
            f"{base_url}/api/v1/infrastructure/events",
            headers={
                "accept": "text/event-stream",
                "authorization": f"Bearer {user_token}",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=15) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        result["event"] = json.loads(line.removeprefix("data: "))
                        return
        except Exception as exc:
            result["error"] = exc

    thread = threading.Thread(target=consume, daemon=True)
    thread.start()
    time.sleep(0.5)
    compose_agent("heartbeat", agent_token)
    thread.join(timeout=20)
    if thread.is_alive():
        raise TimeoutError("SSE client did not receive an infrastructure event")
    if "error" in result:
        raise RuntimeError(f"SSE client failed: {result['error']}")
    event = result.get("event")
    if not isinstance(event, dict) or event.get("server_id") != server_id:
        raise RuntimeError("SSE event does not identify the reporting server")
    return event


def verify_web_session(
    web_url: str,
    *,
    username: str,
    password: str,
) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{web_url}/api/session/login",
        data=json.dumps({"username": username, "password": password}).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = json.loads(response.read().decode("utf-8"))
        set_cookie = response.headers.get("set-cookie", "")
    if body != {"authenticated": True} or "central-secret" in json.dumps(body):
        raise RuntimeError("Web login response exposed unexpected data")
    cookie = SimpleCookie()
    cookie.load(set_cookie)
    morsel = cookie.get("aic_session")
    if morsel is None or not morsel["httponly"] or not morsel["secure"]:
        raise RuntimeError("Web session cookie is not HttpOnly and Secure")
    summary_request = urllib.request.Request(
        f"{web_url}/api/infrastructure/summary",
        headers={"cookie": f"aic_session={morsel.value}"},
    )
    with urllib.request.urlopen(summary_request, timeout=10) as response:
        return dict(json.loads(response.read().decode("utf-8")))


def wait_for_ready(base_url: str, timeout: float = 90) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = request_json(f"{base_url}/health/ready")
            if response.get("status") == "ready":
                return response
        except (OSError, urllib.error.URLError, json.JSONDecodeError) as exc:
            last_error = exc
        time.sleep(1)
    raise RuntimeError("API did not become ready") from last_error


def compose_services() -> list[dict[str, Any]]:
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout.strip()
    if not output:
        return []
    if output.startswith("["):
        value = json.loads(output)
        return list(value)
    return [json.loads(line) for line in output.splitlines()]


def verify_service_state() -> dict[str, str]:
    services = compose_services()
    states = {str(item["Service"]): str(item.get("Health") or item["State"]) for item in services}
    expected = {"web", "api", "postgres", "redis", "worker"}
    if set(states) != expected:
        raise RuntimeError(f"Unexpected Compose services: {sorted(states)}")
    unhealthy = {
        name: state for name, state in states.items() if state.lower() not in {"healthy", "running"}
    }
    if unhealthy:
        raise RuntimeError(f"Compose services are not healthy: {unhealthy}")
    return states


def verify_worker() -> dict[str, Any]:
    code = """
import json
import time
from redis import Redis
from rq import Queue
from ai_infra_api.worker import health_probe

connection = Redis.from_url('redis://redis:6379/0')
job = Queue('default', connection=connection).enqueue(
    health_probe, {'source': 'compose-smoke'}
)
for _ in range(100):
    job.refresh()
    if job.is_failed:
        raise RuntimeError(job.exc_info)
    result = job.return_value()
    if job.is_finished and isinstance(result, dict):
        print(json.dumps(result, sort_keys=True))
        break
    time.sleep(0.2)
else:
    raise TimeoutError('worker did not process the verification job')
"""
    return json.loads(compose_exec("python", "-c", code))


def verify_postgres_migrations() -> None:
    database_name = "ai_infra_migration_smoke"
    password = os.environ.get("AI_INFRA_POSTGRES_PASSWORD")
    if not password:
        raise RuntimeError("AI_INFRA_POSTGRES_PASSWORD is required for migration smoke")

    environment = os.environ.copy()
    environment["AI_INFRA_DATABASE_URL"] = (
        "postgresql+asyncpg://ai_infra:"
        f"{quote_plus(password)}@postgres:5432/{database_name}"
    )
    postgres_exec("dropdb", "--if-exists", "--username", "ai_infra", database_name)
    postgres_exec("createdb", "--username", "ai_infra", database_name)
    try:
        compose_run(
            "alembic",
            "upgrade",
            "head",
            environment=environment,
            environment_variables=("AI_INFRA_DATABASE_URL",),
        )
        compose_run(
            "alembic",
            "downgrade",
            "base",
            environment=environment,
            environment_variables=("AI_INFRA_DATABASE_URL",),
        )
        compose_run(
            "alembic",
            "upgrade",
            "head",
            environment=environment,
            environment_variables=("AI_INFRA_DATABASE_URL",),
        )
    finally:
        postgres_exec("dropdb", "--if-exists", "--username", "ai_infra", database_name)


def main() -> None:
    api_port = os.environ.get("AI_INFRA_API_PORT", "8000")
    web_port = os.environ.get("AI_INFRA_WEB_PORT", "3000")
    base_url = f"http://127.0.0.1:{api_port}"
    web_url = f"http://127.0.0.1:{web_port}"
    username = os.environ.get("AI_INFRA_BOOTSTRAP_ADMIN_USERNAME", "admin")
    password = os.environ.get("AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD is required for Compose smoke")

    run_check("initial readiness", lambda: wait_for_ready(base_url))
    run_check("PostgreSQL migration cycle", verify_postgres_migrations)
    readiness = run_check("post-migration readiness", lambda: wait_for_ready(base_url))

    login = run_check(
        "administrator login",
        lambda: request_json(
            f"{base_url}/api/v1/auth/login",
            method="POST",
            payload={"username": username, "password": password},
        ),
    )
    current_user = run_check(
        "authenticated identity",
        lambda: request_json(
            f"{base_url}/api/v1/auth/me", token=str(login["access_token"])
        ),
    )
    admin_token = str(login["access_token"])
    registration = run_check(
        "Agent token provisioning",
        lambda: request_json(
            f"{base_url}/api/v1/servers/registrations",
            method="POST",
            payload={
                "name": "phase3-cpu-agent",
                "type": "local",
                "tags": ["ci", "cpu-only"],
            },
            token=admin_token,
        ),
    )
    agent_token = str(registration["registration_token"])
    run_check(
        "Agent container registration",
        lambda: compose_agent("register", agent_token, build=True),
    )
    run_check(
        "Agent container heartbeat", lambda: compose_agent("heartbeat", agent_token)
    )

    synthetic_online = run_check(
        "four-GPU Agent report",
        lambda: create_reported_server(
            base_url,
            admin_token,
            name="phase3-four-gpu",
            hostname="phase3-four-gpu-node",
            gpu_count=4,
            process_on_first_gpu=True,
        ),
    )
    synthetic_offline = run_check(
        "offline Agent fixture",
        lambda: create_reported_server(
            base_url,
            admin_token,
            name="phase3-offline-gpu",
            hostname="phase3-offline-node",
            gpu_count=1,
        ),
    )
    run_check(
        "offline heartbeat expiry",
        lambda: backdate_server(str(synthetic_offline["server_id"])),
    )

    viewer_token = run_check("Viewer provisioning", create_viewer_token)
    server_inventory = run_check(
        "multi-server inventory",
        lambda: request_json(
            f"{base_url}/api/v1/servers", token=viewer_token
        ),
    )
    if not isinstance(server_inventory, list):
        raise RuntimeError("Server inventory response is not a list")
    reported_server = next(
        (item for item in server_inventory if item.get("id") == registration["server_id"]),
        None,
    )
    if reported_server is None or reported_server.get("status") != "online":
        raise RuntimeError("Registered Agent is not online in server inventory")
    if len(server_inventory) != 3:
        raise RuntimeError("Expected exactly three Phase 3 server fixtures")
    offline_server = next(
        (
            item
            for item in server_inventory
            if item.get("id") == synthetic_offline["server_id"]
        ),
        None,
    )
    if offline_server is None or offline_server.get("status") != "offline":
        raise RuntimeError("Expired Agent was not marked offline")

    infrastructure = run_check(
        "infrastructure summary",
        lambda: request_json(
            f"{base_url}/api/v1/infrastructure/summary", token=viewer_token
        ),
    )
    expected_summary = {
        "server_count": 3,
        "online_server_count": 2,
        "offline_server_count": 1,
        "gpu_count": 5,
        "available_gpu_count": 3,
    }
    if any(infrastructure.get(key) != value for key, value in expected_summary.items()):
        raise RuntimeError("Infrastructure summary does not match the Phase 3 fixtures")

    gpu_inventory = run_check(
        "cross-server GPU inventory",
        lambda: request_json(f"{base_url}/api/v1/gpus", token=viewer_token),
    )
    if not isinstance(gpu_inventory, list) or len(gpu_inventory) != 5:
        raise RuntimeError("Cross-server GPU inventory is incomplete")
    statuses = [item.get("status") for item in gpu_inventory]
    if statuses.count("active") != 1 or statuses.count("unavailable") != 1:
        raise RuntimeError("GPU status derivation is incorrect")

    server_detail = run_check(
        "server detail and process shape",
        lambda: request_json(
            f"{base_url}/api/v1/servers/{synthetic_online['server_id']}",
            token=viewer_token,
        ),
    )
    if len(server_detail.get("gpus", [])) != 4 or len(server_detail.get("processes", [])) != 1:
        raise RuntimeError("Server detail does not include the expected GPUs and process")
    if "registration_token" in json.dumps(server_detail) or "token_hash" in json.dumps(
        server_detail
    ):
        raise RuntimeError("Infrastructure response exposed an Agent credential field")

    viewer_mutation_status = run_check(
        "Viewer mutation boundary",
        lambda: request_status(
            f"{base_url}/api/v1/servers/registrations",
            method="POST",
            payload={"name": "viewer-must-not-create"},
            token=viewer_token,
        ),
    )
    if viewer_mutation_status != 403:
        raise RuntimeError("Viewer was allowed to create a server registration")

    sse_event = run_check(
        "heartbeat SSE event",
        lambda: verify_sse_event(
            base_url,
            viewer_token,
            agent_token,
            str(registration["server_id"]),
        ),
    )
    web_summary = run_check(
        "Web HttpOnly session and BFF",
        lambda: verify_web_session(web_url, username=username, password=password),
    )
    if any(web_summary.get(key) != value for key, value in expected_summary.items()):
        raise RuntimeError("Web BFF summary differs from the Central API")

    run_check(
        "Agent token revocation",
        lambda: request_json(
            f"{base_url}/api/v1/servers/{registration['server_id']}/agent-token/revoke",
            method="POST",
            token=admin_token,
        ),
    )
    revoked_heartbeat = run_check(
        "revoked Agent rejection",
        lambda: compose_agent("heartbeat", agent_token, check=False),
    )
    if revoked_heartbeat.returncode == 0:
        raise RuntimeError("Revoked Agent token was accepted")
    worker = run_check("worker job", verify_worker)
    services = run_check("service states", verify_service_state)

    print(
        json.dumps(
            {
                "authentication": {
                    "role": current_user["role"],
                    "token_type": login["token_type"],
                    "username": current_user["username"],
                },
                "agent": {
                    "agent_version": reported_server.get("agent_version"),
                    "hostname": reported_server.get("hostname"),
                    "revocation_verified": True,
                    "server_id": registration["server_id"],
                    "status": reported_server.get("status"),
                },
                "infrastructure": {
                    "gpu_count": infrastructure["gpu_count"],
                    "offline_server_count": infrastructure["offline_server_count"],
                    "server_count": infrastructure["server_count"],
                    "sse_kind": sse_event["kind"],
                    "viewer_read_verified": True,
                    "web_bff_verified": True,
                },
                "readiness": readiness,
                "services": services,
                "worker": worker,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
