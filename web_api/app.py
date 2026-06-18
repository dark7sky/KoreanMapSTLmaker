from typing import Any

from web_api.core import WebApiError, build_from_payload, health_payload
from web_api.files import list_artifacts, register_upload_stream, resolve_artifact_download
from web_api.jobs import get_job_status, run_job_from_payload


def create_app():
    try:
        from fastapi import FastAPI, HTTPException
    except ImportError as exc:  # pragma: no cover - import guard documented in requirements
        raise RuntimeError("FastAPI is required to run the web API. Install fastapi and uvicorn.") from exc
    try:  # pragma: no cover - covered by route registration tests with a small FastAPI fake
        from fastapi import File, Form, UploadFile
        from fastapi.responses import FileResponse
    except ImportError:  # pragma: no cover
        File = Form = UploadFile = FileResponse = None

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

    @app.post("/jobs")
    def run_job(payload: dict[str, Any]) -> dict[str, Any]:
        try:
            return run_job_from_payload(payload)
        except WebApiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    @app.get("/jobs/{job_id}")
    def job_status(job_id: str) -> dict[str, Any]:
        try:
            return get_job_status(job_id)
        except WebApiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if File is None or Form is None or UploadFile is None or FileResponse is None:
        return app

    @app.post("/jobs/{job_id}/uploads")
    def upload_file(
        job_id: str,
        file: UploadFile = File(...),
        target_name: str | None = Form(default=None),
    ) -> dict[str, object]:
        try:
            filename = file.filename or "upload.bin"
            return register_upload_stream(job_id, file.file, filename, target_name=target_name)
        except WebApiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    @app.get("/jobs/{job_id}/artifacts")
    def artifacts(job_id: str) -> dict[str, object]:
        try:
            return list_artifacts(job_id)
        except WebApiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    @app.get("/jobs/{job_id}/artifacts/{artifact_path:path}")
    def download_artifact(job_id: str, artifact_path: str):
        try:
            path = resolve_artifact_download(job_id, artifact_path)
        except WebApiError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        return FileResponse(path, filename=path.name)

    return app


app = None
try:  # pragma: no cover - exercised when FastAPI is installed
    app = create_app()
except RuntimeError:
    app = None
