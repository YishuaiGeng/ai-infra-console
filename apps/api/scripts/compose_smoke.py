import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable
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
    payload: dict[str, str] | None = None,
    token: str | None = None,
) -> dict[str, Any]:
    headers = {"accept": "application/json"}
    data = None
    if payload is not None:
        headers["content-type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


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
    base_url = f"http://127.0.0.1:{api_port}"
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
