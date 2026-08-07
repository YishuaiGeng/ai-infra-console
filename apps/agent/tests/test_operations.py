import pytest
from pydantic import ValidationError

from ai_infra_agent.operations import (
    HANDLERS,
    OperationName,
    OperationRequest,
    dispatch_operation,
)


def test_allowlisted_operation_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(HANDLERS, OperationName.GET_GPU_INFO, lambda: [{"uuid": "GPU-test"}])

    result = dispatch_operation(OperationRequest(name=OperationName.GET_GPU_INFO))

    assert result.name == OperationName.GET_GPU_INFO
    assert result.result == [{"uuid": "GPU-test"}]


@pytest.mark.parametrize("name", ["exec", "shell", "command", "download_model"])
def test_unknown_or_not_yet_enabled_operations_fail_closed(name: str) -> None:
    with pytest.raises(ValidationError):
        OperationRequest.model_validate({"name": name})


def test_operation_payload_must_be_empty() -> None:
    with pytest.raises(ValidationError):
        OperationRequest(name=OperationName.GET_SYSTEM_INFO, payload={"command": "whoami"})
