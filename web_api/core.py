from collections.abc import Callable, Mapping
from typing import Any

from app.ui_state import to_build_options
from src.pipeline import BuildOptions, build_model


class WebApiError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def health_payload() -> dict[str, str]:
    return {"status": "ok"}


def build_from_payload(
    payload: Mapping[str, Any],
    build_fn: Callable[[BuildOptions], dict] = build_model,
) -> dict:
    try:
        options = to_build_options(payload)
    except KeyError as exc:
        raise WebApiError(422, f"Missing required field: {exc.args[0]}") from exc
    except (TypeError, ValueError) as exc:
        raise WebApiError(422, f"Invalid build request: {exc}") from exc

    try:
        return build_fn(options)
    except FileNotFoundError as exc:
        raise WebApiError(400, f"Input file not found: {exc}") from exc
    except ValueError as exc:
        raise WebApiError(400, str(exc)) from exc
    except Exception as exc:  # pragma: no cover - exercised through wrapper tests
        raise WebApiError(500, "Build failed.") from exc
