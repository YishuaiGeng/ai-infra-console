import json
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from functools import cache
from http.cookies import SimpleCookie
from typing import Any, TypeVar
from urllib.parse import quote_plus

T = TypeVar("T")
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))


@cache
def service_container_id(service: str) -> str:
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.service={service}",
            "--filter",
            "label=com.docker.compose.oneoff=False",
            "--format",
            "{{.ID}}",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(container_ids) != 1:
        raise RuntimeError(
            f"Expected one running Compose {service} container, found {len(container_ids)}"
        )
    return container_ids[0]


def compose_exec(*arguments: str) -> str:
    result = subprocess.run(
        ["docker", "exec", service_container_id("api"), *arguments],
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
    _, inspect, network_name = running_service_context("api")
    process_environment = (environment or os.environ).copy()
    override_names = set(environment_variables)
    service_environment = {
        name: value
        for item in inspect["Config"].get("Env", [])
        for name, _, value in [str(item).partition("=")]
    }
    for name, value in service_environment.items():
        if name not in override_names and value is not None:
            process_environment[name] = str(value)
    command = ["docker", "run", "--rm", "--network", network_name]
    for name in service_environment.keys() | override_names:
        command.extend(("--env", name))
    command.extend((str(inspect["Config"]["Image"]), *arguments))
    result = subprocess.run(
        command,
        check=True,
        capture_output=True,
        env=process_environment,
        text=True,
        timeout=120,
    )
    return result.stdout.strip()


def postgres_exec(*arguments: str) -> str:
    result = subprocess.run(
        ["docker", "exec", service_container_id("postgres"), *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


@cache
def running_service_context(service: str) -> tuple[str, dict[str, Any], str]:
    container_id = service_container_id(service)
    inspect_result = subprocess.run(
        ["docker", "inspect", container_id],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    inspect = dict(json.loads(inspect_result.stdout)[0])
    networks = dict(inspect["NetworkSettings"]["Networks"])
    network_name = next(
        (name for name in networks if name.endswith("_backend")),
        None,
    )
    if network_name is None:
        raise RuntimeError("Compose backend network is unavailable")
    return container_id, inspect, network_name


def agent_container_arguments(token: str) -> tuple[list[str], dict[str, str]]:
    _, _, network_name = running_service_context("api")
    model_fixtures = os.path.join(ROOT, "apps", "agent", "tests", "fixtures", "models")
    provider_fixtures = os.path.join(ROOT, "apps", "agent", "tests", "fixtures", "provider")
    arguments = [
        "docker",
        "run",
        "--rm",
        "--network",
        network_name,
        "--hostname",
        "phase2-agent-smoke",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges:true",
        "--tmpfs",
        "/tmp:uid=1002,gid=1002,mode=0750",  # noqa: S108 - container tmpfs mount
        "--tmpfs",
        "/downloads:uid=1002,gid=1002,mode=0750",
        "--mount",
        f"type=bind,source={model_fixtures},target=/models,readonly",
        "--mount",
        f"type=bind,source={provider_fixtures},target=/provider-fixtures,readonly",
    ]
    environment = os.environ.copy()
    environment["AI_INFRA_AGENT_TOKEN"] = token
    agent_environment = {
        "AI_INFRA_AGENT_CENTRAL_URL": "http://api:8000",
        "AI_INFRA_AGENT_TOKEN": None,
        "AI_INFRA_AGENT_ENVIRONMENT": "development",
        "AI_INFRA_AGENT_HEARTBEAT_SECONDS": "1",
        "AI_INFRA_AGENT_TLS_VERIFY": "true",
        "AI_INFRA_AGENT_ALLOWED_MODEL_DIRECTORIES": '["/models","/downloads"]',
        "AI_INFRA_AGENT_DEFAULT_MODEL_DIRECTORY": "/downloads",
        "AI_INFRA_AGENT_MODEL_SCAN_INTERVAL_SECONDS": "10",
        "AI_INFRA_AGENT_ENABLE_MODEL_MUTATIONS": "true",
        "AI_INFRA_AGENT_MODEL_TASK_PROGRESS_SECONDS": "0.25",
        "AI_INFRA_AGENT_MODEL_DOWNLOAD_FIXTURE_SOURCE": "/provider-fixtures",
        "AI_INFRA_AGENT_ENABLE_DEPLOYMENTS": "true",
        "AI_INFRA_AGENT_DEPLOYMENT_OPERATION_PROGRESS_SECONDS": "0.5",
        "AI_INFRA_AGENT_DEPLOYMENT_RECONCILE_SECONDS": "1",
        "AI_INFRA_AGENT_DEPLOYMENT_RUNTIME_FIXTURE": "true",
        "AI_INFRA_AGENT_DEPLOYMENT_GPU_FIXTURE": "true",
    }
    for name, value in agent_environment.items():
        arguments.extend(("--env", name if value is None else f"{name}={value}"))
    arguments.append("ai-infra-console-agent:latest")
    return arguments, environment


def compose_agent(
    command: str,
    token: str,
    *,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    arguments, environment = agent_container_arguments(token)
    arguments.extend(("ai-infra-agent", command))
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


def start_agent_runtime(token: str) -> str:
    arguments, environment = agent_container_arguments(token)
    arguments.insert(3, "-d")
    arguments.extend(("ai-infra-agent", "run"))
    result = subprocess.run(
        arguments,
        check=True,
        capture_output=True,
        env=environment,
        text=True,
        timeout=30,
    )
    container_id = result.stdout.strip()
    if not container_id:
        raise RuntimeError("Detached Agent did not return a container ID")
    return container_id


def stop_agent_runtime(container_id: str) -> None:
    subprocess.run(
        ["docker", "stop", "--time", "10", container_id],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )


def assert_container_path_absent(container_id: str, path: str) -> None:
    code = "from pathlib import Path; import sys; sys.exit(1 if Path(sys.argv[1]).exists() else 0)"
    subprocess.run(
        ["docker", "exec", container_id, "python", "-c", code, path],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )


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


def wait_for_task_status(
    url: str,
    token: str,
    expected: set[str],
    *,
    timeout: float = 45,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = dict(request_json(url, token=token))
        status_value = str(last.get("status", ""))
        if status_value in expected:
            return last
        if status_value == "failed":
            raise RuntimeError(
                f"Task failed: {last.get('error_code')}: {last.get('error_message')}"
            )
        time.sleep(0.5)
    raise TimeoutError(f"Task did not reach {sorted(expected)}; last state: {last}")


def wait_for_model_installation(
    base_url: str,
    token: str,
    server_id: str,
    source_id: str,
    status: str,
    *,
    timeout: float = 45,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        models = request_json(f"{base_url}/api/v1/models?server_id={server_id}", token=token)
        match = next(
            (
                item
                for item in models
                if item.get("source_id") == source_id and item.get("status") == status
            ),
            None,
        )
        if isinstance(match, dict):
            return match
        time.sleep(0.5)
    raise TimeoutError(f"Model {source_id} did not reach inventory state {status}")


def wait_for_deployment(
    base_url: str,
    token: str,
    deployment_id: str,
    status: str,
    *,
    health_status: str | None = None,
    timeout: float = 45,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = dict(
            request_json(f"{base_url}/api/v1/deployments/{deployment_id}", token=token)
        )
        if last.get("status") == "failed":
            raise RuntimeError(
                f"Deployment failed: {last.get('error_code')}: {last.get('error_message')}"
            )
        if last.get("status") == status and (
            health_status is None or last.get("health_status") == health_status
        ):
            return last
        time.sleep(0.5)
    raise TimeoutError(
        f"Deployment did not reach {status}/{health_status or '*'}; last state: {last}"
    )


def wait_for_deployment_absence(
    base_url: str,
    token: str,
    deployment_id: str,
    *,
    timeout: float = 45,
) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        status = request_status(
            f"{base_url}/api/v1/deployments/{deployment_id}",
            token=token,
        )
        if status == 404:
            return
        time.sleep(0.5)
    raise TimeoutError("Deployment was not removed after the delete operation")


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
            "boot_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600)),
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
    server_id: str,
    trigger: Callable[[], object],
    *,
    expected_kind: str,
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
    trigger()
    thread.join(timeout=20)
    if thread.is_alive():
        raise TimeoutError("SSE client did not receive an infrastructure event")
    if "error" in result:
        raise RuntimeError(f"SSE client failed: {result['error']}")
    event = result.get("event")
    if not isinstance(event, dict) or event.get("server_id") != server_id:
        raise RuntimeError("SSE event does not identify the reporting server")
    if event.get("kind") != expected_kind:
        raise RuntimeError(f"SSE event kind is not {expected_kind}")
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
        summary = dict(json.loads(response.read().decode("utf-8")))
    models_request = urllib.request.Request(
        f"{web_url}/api/models",
        headers={"cookie": f"aic_session={morsel.value}"},
    )
    with urllib.request.urlopen(models_request, timeout=10) as response:
        models = list(json.loads(response.read().decode("utf-8")))
    downloads_request = urllib.request.Request(
        f"{web_url}/api/downloads",
        headers={"cookie": f"aic_session={morsel.value}"},
    )
    with urllib.request.urlopen(downloads_request, timeout=10) as response:
        downloads = list(json.loads(response.read().decode("utf-8")))
    targets_request = urllib.request.Request(
        f"{web_url}/api/download-targets",
        headers={"cookie": f"aic_session={morsel.value}"},
    )
    with urllib.request.urlopen(targets_request, timeout=10) as response:
        targets = list(json.loads(response.read().decode("utf-8")))
    deployment_targets_request = urllib.request.Request(
        f"{web_url}/api/deployment-targets",
        headers={"cookie": f"aic_session={morsel.value}"},
    )
    with urllib.request.urlopen(deployment_targets_request, timeout=10) as response:
        deployment_targets = list(json.loads(response.read().decode("utf-8")))
    deployments_request = urllib.request.Request(
        f"{web_url}/api/deployments",
        headers={"cookie": f"aic_session={morsel.value}"},
    )
    with urllib.request.urlopen(deployments_request, timeout=10) as response:
        deployments = list(json.loads(response.read().decode("utf-8")))
    return {
        "deployment_targets": deployment_targets,
        "deployments": deployments,
        "downloads": downloads,
        "models": models,
        "summary": summary,
        "targets": targets,
    }


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
    _, api_inspect, _ = running_service_context("api")
    project = api_inspect["Config"]["Labels"].get("com.docker.compose.project")
    if not project:
        raise RuntimeError("API container is missing its Compose project label")
    result = subprocess.run(
        [
            "docker",
            "ps",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.ID}}",
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    container_ids = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not container_ids:
        return []
    inspect_result = subprocess.run(
        ["docker", "inspect", *container_ids],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    services = []
    for item in json.loads(inspect_result.stdout):
        labels = dict(item["Config"].get("Labels") or {})
        if labels.get("com.docker.compose.oneoff") != "False":
            continue
        health = dict(item["State"].get("Health") or {}).get("Status", "")
        services.append(
            {
                "Service": labels.get("com.docker.compose.service", ""),
                "State": item["State"]["Status"],
                "Health": health,
            }
        )
    return services


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
        f"postgresql+asyncpg://ai_infra:{quote_plus(password)}@postgres:5432/{database_name}"
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
        lambda: request_json(f"{base_url}/api/v1/auth/me", token=str(login["access_token"])),
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
                "tags": ["ci", "cpu-only", "model-storage"],
            },
            token=admin_token,
        ),
    )
    agent_token = str(registration["registration_token"])
    run_check(
        "Agent container registration",
        lambda: compose_agent("register", agent_token),
    )
    run_check("Agent container heartbeat", lambda: compose_agent("heartbeat", agent_token))

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
        lambda: request_json(f"{base_url}/api/v1/servers", token=viewer_token),
    )
    if not isinstance(server_inventory, list):
        raise RuntimeError("Server inventory response is not a list")
    reported_server = next(
        (item for item in server_inventory if item.get("id") == registration["server_id"]),
        None,
    )
    if reported_server is None or reported_server.get("status") != "online":
        raise RuntimeError("Registered Agent is not online in server inventory")
    if reported_server.get("model_count") != 2:
        raise RuntimeError("Registered Agent model fixture count is incorrect")
    if len(server_inventory) != 3:
        raise RuntimeError("Expected exactly three Phase 3 server fixtures")
    offline_server = next(
        (item for item in server_inventory if item.get("id") == synthetic_offline["server_id"]),
        None,
    )
    if offline_server is None or offline_server.get("status") != "offline":
        raise RuntimeError("Expired Agent was not marked offline")

    infrastructure = run_check(
        "infrastructure summary",
        lambda: request_json(f"{base_url}/api/v1/infrastructure/summary", token=viewer_token),
    )
    expected_summary = {
        "server_count": 3,
        "online_server_count": 2,
        "offline_server_count": 1,
        "gpu_count": 6,
        "available_gpu_count": 4,
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

    model_inventory = run_check(
        "Agent model inventory",
        lambda: request_json(
            f"{base_url}/api/v1/models?server_id={registration['server_id']}",
            token=viewer_token,
        ),
    )
    if not isinstance(model_inventory, list) or len(model_inventory) != 2:
        raise RuntimeError("Agent model inventory does not contain two fixture locations")
    if {item.get("format") for item in model_inventory} != {"safetensors", "gguf"}:
        raise RuntimeError("Agent model inventory formats are incorrect")
    if any(not str(item.get("path", "")).startswith("/models") for item in model_inventory):
        raise RuntimeError("Agent model inventory escaped the configured root")
    model_summary = run_check(
        "model inventory summary",
        lambda: request_json(
            f"{base_url}/api/v1/model-inventory/summary",
            token=viewer_token,
        ),
    )
    if (
        model_summary.get("model_count") != 2
        or model_summary.get("current_installation_count") != 2
    ):
        raise RuntimeError("Model inventory summary does not match fixture models")
    model_directories = run_check(
        "Agent model directory state",
        lambda: request_json(
            f"{base_url}/api/v1/servers/{registration['server_id']}/model-directories",
            token=viewer_token,
        ),
    )
    if (
        not isinstance(model_directories, list)
        or len(model_directories) != 2
        or {item.get("path") for item in model_directories} != {"/models", "/downloads"}
    ):
        raise RuntimeError("Agent model directory state is incorrect")
    inventory_directory = next(item for item in model_directories if item.get("path") == "/models")
    download_directory = next(
        item for item in model_directories if item.get("path") == "/downloads"
    )
    if inventory_directory.get("model_count") != 2 or download_directory.get("model_count") != 0:
        raise RuntimeError("Agent model directory counts are incorrect")

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
            str(registration["server_id"]),
            lambda: compose_agent("heartbeat", agent_token),
            expected_kind="server.updated",
        ),
    )
    viewer_default_status = run_check(
        "Viewer model directory mutation boundary",
        lambda: request_status(
            f"{base_url}/api/v1/servers/{registration['server_id']}/model-directories/default",
            method="PUT",
            payload={"directory_id": inventory_directory["id"]},
            token=viewer_token,
        ),
    )
    if viewer_default_status != 403:
        raise RuntimeError("Viewer was allowed to change the default model directory")
    model_sse_event = run_check(
        "model inventory SSE event",
        lambda: verify_sse_event(
            base_url,
            viewer_token,
            str(registration["server_id"]),
            lambda: request_json(
                f"{base_url}/api/v1/servers/{registration['server_id']}/model-directories/default",
                method="PUT",
                payload={"directory_id": inventory_directory["id"]},
                token=admin_token,
            ),
            expected_kind="model.inventory.updated",
        ),
    )

    download_targets = run_check(
        "allowlisted download targets",
        lambda: request_json(f"{base_url}/api/v1/download-targets", token=viewer_token),
    )
    if (
        not isinstance(download_targets, list)
        or len(download_targets) != 1
        or download_targets[0].get("server", {}).get("id") != registration["server_id"]
        or {item.get("path") for item in download_targets[0].get("directories", [])}
        != {"/models", "/downloads"}
    ):
        raise RuntimeError("Download targets escaped the Central mutable-server policy")

    download_payload = {
        "provider": "huggingface",
        "source_id": "Qwen/Qwen3-Tiny",
        "revision": "compose-revision",
        "server_id": registration["server_id"],
        "directory_id": download_directory["id"],
    }
    viewer_download_status = run_check(
        "Viewer download mutation boundary",
        lambda: request_status(
            f"{base_url}/api/v1/downloads",
            method="POST",
            payload=download_payload,
            token=viewer_token,
        ),
    )
    if viewer_download_status != 403:
        raise RuntimeError("Viewer was allowed to create a model download")

    queued_download: dict[str, Any] = {}

    def queue_download() -> None:
        queued_download.update(
            request_json(
                f"{base_url}/api/v1/downloads",
                method="POST",
                payload=download_payload,
                token=admin_token,
            )
        )

    download_sse_event = run_check(
        "download task SSE event",
        lambda: verify_sse_event(
            base_url,
            viewer_token,
            str(registration["server_id"]),
            queue_download,
            expected_kind="model.download.updated",
        ),
    )
    if (
        queued_download.get("status") != "queued"
        or queued_download.get("target_path") != "/downloads/huggingface/Qwen/Qwen3-Tiny"
    ):
        raise RuntimeError("Download task did not resolve the advertised directory")
    download_id = str(queued_download["id"])
    cancelled_download = run_check(
        "queued download cancellation",
        lambda: request_json(
            f"{base_url}/api/v1/downloads/{download_id}/cancel",
            method="POST",
            token=admin_token,
        ),
    )
    if cancelled_download.get("status") != "cancelled":
        raise RuntimeError("Queued download was not cancelled")
    retried_download = run_check(
        "cancelled download retry",
        lambda: request_json(
            f"{base_url}/api/v1/downloads/{download_id}/retry",
            method="POST",
            token=admin_token,
        ),
    )
    if retried_download.get("status") != "queued":
        raise RuntimeError("Cancelled download was not requeued")

    agent_runtime = run_check("model task Agent runtime", lambda: start_agent_runtime(agent_token))
    try:
        completed_download = run_check(
            "fixture model download completion",
            lambda: wait_for_task_status(
                f"{base_url}/api/v1/downloads/{download_id}",
                viewer_token,
                {"completed"},
            ),
        )
        if (
            completed_download.get("progress") != 100.0
            or completed_download.get("attempt_count") != 1
        ):
            raise RuntimeError("Completed download progress or attempt count is incorrect")
        downloaded_model = run_check(
            "download inventory convergence",
            lambda: wait_for_model_installation(
                base_url,
                viewer_token,
                str(registration["server_id"]),
                "Qwen/Qwen3-Tiny",
                "discovered",
            ),
        )
        if downloaded_model.get("path") != queued_download.get("target_path"):
            raise RuntimeError("Downloaded model inventory path differs from the task")

        confirmation_mismatch = run_check(
            "delete confirmation boundary",
            lambda: request_status(
                f"{base_url}/api/v1/model-files/{downloaded_model['id']}/delete",
                method="POST",
                payload={"confirmation": "wrong/model"},
                token=admin_token,
            ),
        )
        if confirmation_mismatch != 422:
            raise RuntimeError("Deletion accepted an incorrect model source ID")
        viewer_delete_status = run_check(
            "Viewer deletion boundary",
            lambda: request_status(
                f"{base_url}/api/v1/model-files/{downloaded_model['id']}/delete",
                method="POST",
                payload={"confirmation": "Qwen/Qwen3-Tiny"},
                token=viewer_token,
            ),
        )
        if viewer_delete_status != 403:
            raise RuntimeError("Viewer was allowed to delete a model installation")
        delete_task = run_check(
            "model deletion queue",
            lambda: request_json(
                f"{base_url}/api/v1/model-files/{downloaded_model['id']}/delete",
                method="POST",
                payload={"confirmation": "Qwen/Qwen3-Tiny"},
                token=admin_token,
            ),
        )
        completed_delete = run_check(
            "model deletion completion",
            lambda: wait_for_task_status(
                f"{base_url}/api/v1/model-deletions/{delete_task['id']}",
                viewer_token,
                {"completed"},
            ),
        )
        run_check(
            "deleted path absence",
            lambda: assert_container_path_absent(
                agent_runtime, str(completed_delete["target_path"])
            ),
        )
        run_check(
            "deleted inventory convergence",
            lambda: wait_for_model_installation(
                base_url,
                viewer_token,
                str(registration["server_id"]),
                "Qwen/Qwen3-Tiny",
                "missing",
            ),
        )

        deployment_targets = run_check(
            "deployment target discovery",
            lambda: request_json(f"{base_url}/api/v1/deployment-targets", token=viewer_token),
        )
        if (
            not isinstance(deployment_targets, list)
            or len(deployment_targets) != 1
            or deployment_targets[0].get("server", {}).get("id")
            != registration["server_id"]
            or deployment_targets[0].get("docker_available") is not True
        ):
            raise RuntimeError("Deployment targets escaped the mutable Agent boundary")
        deployment_model = next(
            (
                item
                for item in deployment_targets[0].get("model_files", [])
                if item.get("format") == "safetensors"
            ),
            None,
        )
        deployment_gpu = next(iter(deployment_targets[0].get("gpus", [])), None)
        if not isinstance(deployment_model, dict) or not isinstance(deployment_gpu, dict):
            raise RuntimeError("Deployment target is missing the fixture model or GPU")
        deployment_payload = {
            "name": "qwen3-8b-compose",
            "model_file_id": deployment_model["model_file_id"],
            "selection_mode": "manual",
            "gpu_ids": [deployment_gpu["id"]],
            "port": 8001,
            "config": {
                "tensor_parallel_size": 1,
                "gpu_memory_utilization": 0.9,
                "max_model_length": 32768,
                "data_type": "auto",
                "trust_remote_code": False,
                "extra_arguments": ["--enable-prefix-caching", "--max-num-seqs", "128"],
            },
        }
        viewer_deployment_status = run_check(
            "Viewer deployment mutation boundary",
            lambda: request_status(
                f"{base_url}/api/v1/deployments",
                method="POST",
                payload=deployment_payload,
                token=viewer_token,
            ),
        )
        if viewer_deployment_status != 403:
            raise RuntimeError("Viewer was allowed to create a deployment")
        queued_deployment: dict[str, Any] = {}

        def queue_deployment() -> None:
            queued_deployment.update(
                request_json(
                    f"{base_url}/api/v1/deployments",
                    method="POST",
                    payload=deployment_payload,
                    token=admin_token,
                )
            )

        deployment_sse_event = run_check(
            "deployment create SSE event",
            lambda: verify_sse_event(
                base_url,
                viewer_token,
                str(registration["server_id"]),
                queue_deployment,
                expected_kind="deployment.updated",
            ),
        )
        if queued_deployment.get("status") != "queued":
            raise RuntimeError("Deployment was not queued")
        deployment_id = str(queued_deployment["id"])
        running_deployment = run_check(
            "deployment create, reconcile, and health",
            lambda: wait_for_deployment(
                base_url,
                viewer_token,
                deployment_id,
                "running",
                health_status="healthy",
            ),
        )
        if (
            running_deployment.get("gpus", [{}])[0].get("id") != deployment_gpu["id"]
            or not str(running_deployment.get("endpoint", "")).endswith(":8001/v1")
        ):
            raise RuntimeError("Deployment placement or endpoint is incorrect")
        deployment_logs = run_check(
            "deployment log forwarding",
            lambda: request_json(
                f"{base_url}/api/v1/deployments/{deployment_id}/logs?limit=20",
                token=viewer_token,
            ),
        )
        if not any(
            "fixture vLLM runtime is ready" in item.get("message", "")
            for item in deployment_logs
        ):
            raise RuntimeError("Deployment logs did not converge from the Agent")
        allocated_gpus = run_check(
            "deployment GPU allocation overlay",
            lambda: request_json(f"{base_url}/api/v1/gpus", token=viewer_token),
        )
        allocated_gpu = next(
            (item for item in allocated_gpus if item.get("id") == deployment_gpu["id"]),
            None,
        )
        if (
            not isinstance(allocated_gpu, dict)
            or allocated_gpu.get("status") != "active"
            or allocated_gpu.get("deployment_id") != deployment_id
        ):
            raise RuntimeError("GPU inventory did not expose the active deployment")
        repeated_start = run_check(
            "idempotent running start",
            lambda: request_json(
                f"{base_url}/api/v1/deployments/{deployment_id}/start",
                method="POST",
                token=admin_token,
            ),
        )
        if repeated_start.get("status") != "running":
            raise RuntimeError("Repeated start changed a running deployment")
        run_check(
            "deployment stop request",
            lambda: request_json(
                f"{base_url}/api/v1/deployments/{deployment_id}/stop",
                method="POST",
                token=admin_token,
            ),
        )
        stopped_deployment = run_check(
            "deployment stop convergence",
            lambda: wait_for_deployment(
                base_url, viewer_token, deployment_id, "stopped"
            ),
        )
        if stopped_deployment.get("health_status") != "unknown":
            raise RuntimeError("Stopped deployment retained a live health state")
        released_gpus = request_json(f"{base_url}/api/v1/gpus", token=viewer_token)
        released_gpu = next(
            (item for item in released_gpus if item.get("id") == deployment_gpu["id"]),
            None,
        )
        if not isinstance(released_gpu, dict) or released_gpu.get("deployment_id") is not None:
            raise RuntimeError("Stopped deployment retained its runtime GPU allocation")
        run_check(
            "deployment start request",
            lambda: request_json(
                f"{base_url}/api/v1/deployments/{deployment_id}/start",
                method="POST",
                token=admin_token,
            ),
        )
        run_check(
            "deployment start convergence",
            lambda: wait_for_deployment(
                base_url,
                viewer_token,
                deployment_id,
                "running",
                health_status="healthy",
            ),
        )
        run_check(
            "deployment restart request",
            lambda: request_json(
                f"{base_url}/api/v1/deployments/{deployment_id}/restart",
                method="POST",
                token=admin_token,
            ),
        )
        run_check(
            "deployment restart convergence",
            lambda: wait_for_deployment(
                base_url,
                viewer_token,
                deployment_id,
                "running",
                health_status="healthy",
            ),
        )
        bad_deployment_delete = run_check(
            "deployment delete confirmation boundary",
            lambda: request_status(
                f"{base_url}/api/v1/deployments/{deployment_id}",
                method="DELETE",
                payload={"confirmation": "wrong-deployment"},
                token=admin_token,
            ),
        )
        if bad_deployment_delete != 422:
            raise RuntimeError("Deployment deletion accepted an incorrect confirmation")
        viewer_deployment_delete = run_check(
            "Viewer deployment deletion boundary",
            lambda: request_status(
                f"{base_url}/api/v1/deployments/{deployment_id}",
                method="DELETE",
                payload={"confirmation": "qwen3-8b-compose"},
                token=viewer_token,
            ),
        )
        if viewer_deployment_delete != 403:
            raise RuntimeError("Viewer was allowed to delete a deployment")
        run_check(
            "deployment delete request",
            lambda: request_json(
                f"{base_url}/api/v1/deployments/{deployment_id}",
                method="DELETE",
                payload={"confirmation": "qwen3-8b-compose"},
                token=admin_token,
            ),
        )
        run_check(
            "deployment delete convergence",
            lambda: wait_for_deployment_absence(
                base_url, viewer_token, deployment_id
            ),
        )
        preserved_model = run_check(
            "deployment delete preserves model installation",
            lambda: wait_for_model_installation(
                base_url,
                viewer_token,
                str(registration["server_id"]),
                str(deployment_model["source_id"]),
                "discovered",
            ),
        )
        if (
            preserved_model.get("id") != deployment_model.get("model_file_id")
            or preserved_model.get("model_id") != deployment_model.get("id")
        ):
            raise RuntimeError("Deployment deletion changed the model installation")
    finally:
        run_check("model task Agent shutdown", lambda: stop_agent_runtime(agent_runtime))

    web_result = run_check(
        "Web HttpOnly session and BFF",
        lambda: verify_web_session(web_url, username=username, password=password),
    )
    web_summary = web_result["summary"]
    if any(web_summary.get(key) != value for key, value in expected_summary.items()):
        raise RuntimeError("Web BFF summary differs from the Central API")
    web_models = web_result["models"]
    if (
        not isinstance(web_models, list)
        or len([item for item in web_models if item.get("status") == "discovered"]) != 2
        or not any(
            item.get("source_id") == "Qwen/Qwen3-Tiny" and item.get("status") == "missing"
            for item in web_models
        )
    ):
        raise RuntimeError("Web BFF model inventory differs from the Central API")
    if (
        len(web_result["downloads"]) != 1
        or web_result["downloads"][0].get("status") != "completed"
        or len(web_result["targets"]) != 1
    ):
        raise RuntimeError("Web BFF download workflow differs from the Central API")
    if len(web_result["deployment_targets"]) != 1 or web_result["deployments"]:
        raise RuntimeError("Web BFF deployment workflow differs from the Central API")

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
                "models": {
                    "formats": sorted(item["format"] for item in model_inventory),
                    "installation_count": model_summary["installation_count"],
                    "download_sse_kind": download_sse_event["kind"],
                    "download_status": completed_download["status"],
                    "delete_status": completed_delete["status"],
                    "sse_kind": model_sse_event["kind"],
                    "viewer_read_verified": True,
                    "web_bff_verified": True,
                },
                "deployments": {
                    "delete_verified": True,
                    "health": running_deployment["health_status"],
                    "logs_verified": True,
                    "sse_kind": deployment_sse_event["kind"],
                    "viewer_mutation_denied": True,
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
