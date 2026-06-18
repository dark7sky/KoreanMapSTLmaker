# Local Web Service Scaffold

This repository keeps the CLI workflow as the primary path. The Docker/FastAPI setup in this repo is an optional local scaffold for a future API layer and for containerized smoke testing.

It currently exposes:

- `GET /health`
- `POST /build`
- the default FastAPI docs at `/docs` when FastAPI is available in the container

The `/build` endpoint runs the existing local build pipeline synchronously from a JSON payload that mirrors the Streamlit form/build options. Upload, download, and asynchronous job routes are still future work.

## Run With Docker Compose

```powershell
docker compose up --build web
```

Then open:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## Paths And Volumes

The compose file bind-mounts the repository root at `/workspace`.

That gives the container access to:

- `/workspace/app`
- `/workspace/src`
- `/workspace/scripts`
- `/workspace/data`
- `/workspace/output`

The service reads these container paths from environment variables:

- `APP_DATA_DIR` defaults to `/workspace/data`
- `APP_OUTPUT_DIR` defaults to `/workspace/output`
- `APP_SAMPLE_DIR` defaults to `/workspace/data/sample`

Override them in `docker-compose.yml` or on the command line if your local folder layout is different.

## Docker Image Notes

The image installs the project requirements plus `fastapi` and `uvicorn`.

The `data/` and `output/` directories are intentionally kept out of the build context by `.dockerignore` so the image stays small. They are supplied at runtime through the bind mount.

## What This Is Not Yet

This is not the planned production API. The job queue, upload/download endpoints, and any browser frontend remain future work.
