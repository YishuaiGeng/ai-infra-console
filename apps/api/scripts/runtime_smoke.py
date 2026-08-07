import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from secrets import token_urlsafe
from typing import Any

import httpx
from redis import Redis
from rq import Queue

from ai_infra_api.worker import health_probe


def available_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def wait_until(check: Any, *, timeout: float, description: str) -> Any:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except Exception as exc:
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {description}") from last_error


def stop_process(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def process_flags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def main() -> None:
    api_root = Path(__file__).resolve().parents[1]
    redis_executable = shutil.which("redis-server")
    if redis_executable is None:
        raise RuntimeError("redis-server is required for the runtime smoke test")

    redis_port = available_port()
    api_port = available_port()
    admin_username = "phase1-smoke-admin"
    admin_password = token_urlsafe(24)
    jwt_secret = token_urlsafe(48)
    redis_url = f"redis://127.0.0.1:{redis_port}/0"

    redis_process: subprocess.Popen[bytes] | None = None
    api_process: subprocess.Popen[bytes] | None = None
    worker_process: subprocess.Popen[bytes] | None = None

    with tempfile.TemporaryDirectory(prefix="ai-infra-phase1-") as temporary:
        runtime_dir = Path(temporary)
        database_path = (runtime_dir / "api.db").as_posix()
        environment = os.environ.copy()
        environment.update(
            {
                "AI_INFRA_ENVIRONMENT": "test",
                "AI_INFRA_DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
                "AI_INFRA_REDIS_URL": redis_url,
                "AI_INFRA_JWT_SECRET": jwt_secret,
                "AI_INFRA_BOOTSTRAP_ADMIN_USERNAME": admin_username,
                "AI_INFRA_BOOTSTRAP_ADMIN_PASSWORD": admin_password,
            }
        )

        log_path = runtime_dir / "runtime.log"
        with log_path.open("wb") as runtime_log:
            try:
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "alembic",
                        "-c",
                        str(api_root / "alembic.ini"),
                        "upgrade",
                        "head",
                    ],
                    cwd=api_root,
                    env=environment,
                    check=True,
                    stdout=runtime_log,
                    stderr=subprocess.STDOUT,
                    creationflags=process_flags(),
                )

                redis_process = subprocess.Popen(
                    [
                        redis_executable,
                        "--port",
                        str(redis_port),
                        "--bind",
                        "127.0.0.1",
                        "--save",
                        "",
                        "--appendonly",
                        "no",
                        "--dir",
                        str(runtime_dir),
                    ],
                    stdout=runtime_log,
                    stderr=subprocess.STDOUT,
                    creationflags=process_flags(),
                )
                redis = Redis.from_url(redis_url)
                wait_until(redis.ping, timeout=15, description="Redis")

                api_process = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        "ai_infra_api.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(api_port),
                    ],
                    cwd=api_root,
                    env=environment,
                    stdout=runtime_log,
                    stderr=subprocess.STDOUT,
                    creationflags=process_flags(),
                )
                base_url = f"http://127.0.0.1:{api_port}"

                def ready() -> dict[str, Any] | None:
                    response = httpx.get(f"{base_url}/health/ready", timeout=2)
                    return response.json() if response.status_code == 200 else None

                readiness = wait_until(ready, timeout=30, description="API readiness")
                login = httpx.post(
                    f"{base_url}/api/v1/auth/login",
                    json={"username": admin_username, "password": admin_password},
                    headers={"x-request-id": "phase1-runtime-login"},
                    timeout=10,
                )
                login.raise_for_status()
                token = login.json()["access_token"]
                current_user = httpx.get(
                    f"{base_url}/api/v1/auth/me",
                    headers={"authorization": f"Bearer {token}"},
                    timeout=10,
                )
                current_user.raise_for_status()

                worker_process = subprocess.Popen(
                    [sys.executable, "-m", "ai_infra_api.worker"],
                    cwd=api_root,
                    env=environment,
                    stdout=runtime_log,
                    stderr=subprocess.STDOUT,
                    creationflags=process_flags(),
                )
                queue = Queue("default", connection=redis)
                job = queue.enqueue(health_probe, {"source": "runtime-smoke"})

                def completed_job() -> dict[str, Any] | None:
                    job.refresh()
                    if job.is_failed:
                        raise RuntimeError(job.exc_info)
                    result = job.return_value()
                    return result if job.is_finished and isinstance(result, dict) else None

                worker_result = wait_until(
                    completed_job, timeout=20, description="RQ worker health job"
                )
                summary = {
                    "readiness": readiness,
                    "authentication": {
                        "username": current_user.json()["username"],
                        "role": current_user.json()["role"],
                        "token_type": login.json()["token_type"],
                    },
                    "worker": worker_result,
                }
                print(json.dumps(summary, indent=2, sort_keys=True))
            except Exception:
                runtime_log.flush()
                print(log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)
                raise
            finally:
                stop_process(worker_process)
                stop_process(api_process)
                stop_process(redis_process)


if __name__ == "__main__":
    main()
