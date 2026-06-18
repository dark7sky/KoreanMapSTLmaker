from typing import Any

from web_api.core import WebApiError, build_from_payload, health_payload


def create_app():
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover - import guard documented in requirements
        raise RuntimeError("FastAPI is required to run the web API. Install fastapi and uvicorn.") from exc

    app = FastAPI(title="MAP Web API")

    @app.get("/health")
    def health() -> dict[str, str]:
        return health_payload()

    @app.post("/build")
    def build(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return build_from_payload(payload)
        except WebApiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    return app


app = None
try:  # pragma: no cover - exercised when FastAPI is installed
    app = create_app()
except RuntimeError:
    app = None
