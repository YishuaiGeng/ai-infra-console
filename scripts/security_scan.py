import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "apps" / "api" / "src", ROOT / "apps" / "agent" / "src")
FORBIDDEN_ROUTE = re.compile(r"[\"']/(?:exec|shell|command)(?:/|[\"'])", re.IGNORECASE)
ALLOWED_SUBPROCESS_FILE = ROOT / "apps" / "agent" / "src" / "ai_infra_agent" / "collectors" / "nvidia.py"


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

    for tracked in tracked_files():
        normalized = tracked.replace("\\", "/")
        if normalized.startswith("服务器资料/"):
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
