import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "apps" / "api" / "src", ROOT / "apps" / "agent" / "src")
FORBIDDEN_ROUTE = re.compile(r"[\"']/(?:exec|shell|command)(?:/|[\"'])", re.IGNORECASE)
ALLOWED_SUBPROCESS_FILE = ROOT / "apps" / "agent" / "src" / "ai_infra_agent" / "collectors" / "nvidia.py"
PHASE_5_WEB_PATHS = (
    ROOT / "apps" / "web" / "src" / "app" / "api" / "catalog",
    ROOT / "apps" / "web" / "src" / "app" / "api" / "download-targets",
    ROOT / "apps" / "web" / "src" / "app" / "api" / "downloads",
    ROOT / "apps" / "web" / "src" / "app" / "api" / "model-deletions",
    ROOT / "apps" / "web" / "src" / "app" / "api" / "model-files",
    ROOT / "apps" / "web" / "src" / "components" / "model",
    ROOT / "apps" / "web" / "src" / "features" / "downloads",
    ROOT / "apps" / "web" / "src" / "features" / "models",
    ROOT / "apps" / "web" / "src" / "hooks" / "use-downloads.ts",
    ROOT / "apps" / "web" / "src" / "lib" / "api" / "downloads.ts",
)
PHASE_6_WEB_PATHS = (
    ROOT / "apps" / "web" / "src" / "app" / "api" / "deployment-targets",
    ROOT / "apps" / "web" / "src" / "app" / "api" / "deployments",
    ROOT / "apps" / "web" / "src" / "app" / "(console)" / "deployments",
    ROOT / "apps" / "web" / "src" / "components" / "deployment" / "deploy-model-dialog.tsx",
    ROOT / "apps" / "web" / "src" / "components" / "deployment" / "deployment-actions.tsx",
    ROOT
    / "apps"
    / "web"
    / "src"
    / "components"
    / "deployment"
    / "deployment-log-viewer.tsx",
    ROOT
    / "apps"
    / "web"
    / "src"
    / "components"
    / "deployment"
    / "deployment-metrics.tsx",
    ROOT / "apps" / "web" / "src" / "features" / "deployments",
    ROOT / "apps" / "web" / "src" / "hooks" / "use-deployments.ts",
    ROOT / "apps" / "web" / "src" / "lib" / "api" / "deployments.ts",
)
API_RESOURCE_PATHS = (
    ROOT / "apps" / "api" / "src" / "ai_infra_api" / "api" / "api_resources.py",
    ROOT / "apps" / "api" / "src" / "ai_infra_api" / "services" / "api_resources",
    ROOT / "apps" / "web" / "src" / "app" / "api" / "api-resources",
    ROOT / "apps" / "web" / "src" / "features" / "api-resources",
    ROOT / "apps" / "web" / "src" / "hooks" / "use-api-resources.ts",
    ROOT / "apps" / "web" / "src" / "lib" / "api" / "api-resources.ts",
)
DEPLOYMENT_CONFIG_FILES = (
    ROOT / "compose.yaml",
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / "deploy" / "systemd" / "agent.service",
    ROOT / "deploy" / "systemd" / "agent.env.example",
)
MUTABLE_ALLOWLIST_FILES = (
    ROOT / ".env.example",
    ROOT / "compose.yaml",
    ROOT / ".github" / "workflows" / "ci.yml",
    ROOT / "deploy" / "systemd" / "agent.env.example",
)
BACKUP_HOSTS = ("backup-node-01", "backup-node-02")


def python_sources() -> list[Path]:
    return [path for source_root in SOURCE_ROOTS for path in source_root.rglob("*.py")]


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=False,
    )
    return [item.decode("utf-8") for item in result.stdout.split(b"\0") if item]


def source_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    if path.is_dir():
        return [
            candidate
            for candidate in path.rglob("*")
            if candidate.is_file()
            and candidate.suffix.lower() in {".js", ".jsx", ".py", ".ts", ".tsx"}
        ]
    return []


def main() -> None:
    failures: list[str] = []
    for path in python_sources():
        content = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        if FORBIDDEN_ROUTE.search(content):
            failures.append(f"forbidden generic command route in {relative}")
        if "subprocess." in content and path != ALLOWED_SUBPROCESS_FILE:
            failures.append(f"subprocess use outside fixed NVIDIA adapter in {relative}")
        if "shell=True" in content or "os.system(" in content:
            failures.append(f"shell execution primitive in {relative}")

    for root in PHASE_5_WEB_PATHS:
        for path in source_files(root):
            content = path.read_text(encoding="utf-8")
            if "@/mocks" in content:
                relative = path.relative_to(ROOT).as_posix()
                failures.append(f"Phase 5 Web source imports mock data: {relative}")

    for root in PHASE_6_WEB_PATHS:
        for path in source_files(root):
            content = path.read_text(encoding="utf-8")
            if "@/mocks" in content:
                relative = path.relative_to(ROOT).as_posix()
                failures.append(f"Phase 6 Web source imports mock data: {relative}")

    for root in API_RESOURCE_PATHS:
        for path in source_files(root):
            content = path.read_text(encoding="utf-8")
            relative = path.relative_to(ROOT).as_posix()
            if "@/mocks" in content:
                failures.append(f"API resource source imports mock data: {relative}")
            if "allow_redirects=True" in content or "follow_redirects=True" in content:
                failures.append(f"API resource outbound redirects are enabled: {relative}")

    response_schema = ROOT / "apps" / "api" / "src" / "ai_infra_api" / "schemas" / "api_resources.py"
    if response_schema.exists():
        content = response_schema.read_text(encoding="utf-8")
        for field in ("encrypted_value", "fingerprint"):
            if field in content:
                failures.append(f"credential storage field appears in API response schema: {field}")

    for path in DEPLOYMENT_CONFIG_FILES:
        if path.exists() and "/var/run/docker.sock" in path.read_text(encoding="utf-8"):
            relative = path.relative_to(ROOT).as_posix()
            failures.append(f"Docker socket is exposed by deployment config: {relative}")

    for path in MUTABLE_ALLOWLIST_FILES:
        if not path.exists():
            continue
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "AI_INFRA_MUTABLE_SERVER_NAMES" not in line:
                continue
            lowered = line.lower()
            for host in BACKUP_HOSTS:
                if host in lowered:
                    relative = path.relative_to(ROOT).as_posix()
                    failures.append(
                        f"backup host appears in mutable allowlist at {relative}:{line_number}"
                    )

    for tracked in tracked_files():
        normalized = tracked.replace("\\", "/")
        if normalized == "服务器资料" or normalized.startswith("服务器资料/"):
            failures.append(f"private server material is tracked: {normalized}")
        if Path(normalized).name == ".env":
            failures.append(f"environment secret file is tracked: {normalized}")
        if Path(normalized).suffix.lower() in {".key", ".pem"}:
            failures.append(f"private key material is tracked: {normalized}")

    if failures:
        raise SystemExit("\n".join(failures))
    print("Security boundary scan passed")


if __name__ == "__main__":
    main()
