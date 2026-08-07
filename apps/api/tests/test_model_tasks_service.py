from datetime import UTC, datetime, timedelta

import pytest

from ai_infra_api.services.model_tasks import (
    ModelTaskError,
    build_target_path,
    validate_repository_id,
)


def test_repository_identity_and_target_path_are_bounded() -> None:
    assert validate_repository_id("Qwen/Qwen3-8B") == ("Qwen", "Qwen3-8B")
    assert (
        build_target_path("/data/models", "huggingface", "Qwen/Qwen3-8B")
        == "/data/models/huggingface/Qwen/Qwen3-8B"
    )
    assert (
        build_target_path("D:\\models", "modelscope", "Qwen/Qwen3-8B")
        == "D:\\models\\modelscope\\Qwen\\Qwen3-8B"
    )
    for invalid in ("Qwen", "../Qwen", "Qwen/..", "https://host/repo", "Qwen/a/b"):
        with pytest.raises(ModelTaskError, match="source ID"):
            validate_repository_id(invalid)


def test_timezone_fixture_is_explicit() -> None:
    now = datetime.now(UTC)
    assert now + timedelta(seconds=60) > now
