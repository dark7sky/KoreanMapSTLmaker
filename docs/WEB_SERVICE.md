# Local Web Service Scaffold

This repository keeps the CLI workflow as the primary path. The Docker/FastAPI setup in this repo is an optional local scaffold for a future API layer and for containerized smoke testing.

It currently exposes:

- `GET /health`
- `POST /build`
- `POST /jobs`
- `GET /jobs/{job_id}`
- `POST /jobs/{job_id}/uploads`
- `GET /jobs/{job_id}/artifacts`
- `GET /jobs/{job_id}/artifacts/{artifact_path}`
- the default FastAPI docs at `/docs` when FastAPI is available in the container

The `/build` endpoint runs the existing local build pipeline synchronously from a JSON payload that mirrors the Streamlit form/build options. The job endpoint also runs synchronously: it creates a job directory, calls the same build path, writes metadata, and returns the final status. The file endpoints are small storage helpers for local tooling and smoke tests; they do not create or run asynchronous jobs.

## Job Endpoints

`POST /jobs` accepts either a nested build payload:

```json
{
  "job_id": "sample-job",
  "payload": {
    "area_path": "data/sample/area.geojson",
    "buildings_path": "data/sample/buildings.geojson",
    "dem_path": "data/sample/dem.tif",
    "out_path": "output/model.stl"
  }
}
```

or the build fields directly with an optional top-level `job_id`.

If `job_id` is omitted, the service generates a safe `job-<uuid>` id. Supplied job IDs are deterministic, but they must be simple path names with no absolute paths, nested paths, or `..` traversal.

Each run writes metadata to:

```text
.web_api/jobs/<job_id>/job.json
```

`GET /jobs/{job_id}` returns that persisted metadata. Successful jobs use `status: "succeeded"` and include `result`; failed builds use `status: "failed"` and include an `error` object. There is no background worker or queue yet.

## File Endpoints

Files are stored below `.web_api/jobs/<job_id>/` in the workspace. Job IDs must be simple path names, and upload or artifact names must stay relative to their storage directory. Absolute paths and `..` traversal are rejected.

`POST /jobs/{job_id}/uploads` accepts a multipart file field named `file` and an optional form field named `target_name`. The upload is copied into:

```text
.web_api/jobs/<job_id>/uploads/<target_name-or-original-filename>
```

The response includes:

```json
{
  "job_id": "job-123",
  "name": "inputs/area.geojson",
  "size_bytes": 1234
}
```

`GET /jobs/{job_id}/artifacts` lists files below:

```text
.web_api/jobs/<job_id>/artifacts/
```

Each listed artifact includes a relative `name`, `size_bytes`, and `download_url`.

`GET /jobs/{job_id}/artifacts/{artifact_path}` downloads one stored artifact. Missing artifacts return `404`; invalid job IDs or escaping paths return `400`.

## Run With Docker Compose

```powershell
docker compose up --build web
```

Then open:

- `http://localhost:8000/health`
- `http://localhost:8000/docs`

## Optional Static Frontend

Open `web_frontend/index.html` directly in a browser for a minimal local console.

The page has no Node/npm dependency. It can:

- call `GET /health` against `http://localhost:8000`
- prepare the JSON payload expected by `POST /build`
- submit that payload to the optional FastAPI service when it is running

Because it is a static helper, it is safe to keep offline-testable. The page does not bundle a Vite app or require `npm install` for repository tests.

## Paths And Volumes

The compose file bind-mounts the repository root at `/workspace`.

That gives the container access to:

- `/workspace/app`
- `/workspace/src`
- `/workspace/scripts`
- `/workspace/data`
- `/workspace/output`

The service reads these container paths from environment variables:

- `APP_WORKSPACE` defaults to the current working directory and controls where `.web_api/jobs` is created
- `APP_DATA_DIR` defaults to `/workspace/data`
- `APP_OUTPUT_DIR` defaults to `/workspace/output`
- `APP_SAMPLE_DIR` defaults to `/workspace/data/sample`

Override them in `docker-compose.yml` or on the command line if your local folder layout is different.

## Docker Image Notes

The image installs the project requirements plus `fastapi` and `uvicorn`.

The `data/` and `output/` directories are intentionally kept out of the build context by `.dockerignore` so the image stays small. They are supplied at runtime through the bind mount.

## What This Is Not Yet

This is not the planned production API. The job queue and upload/download browser workflows remain future work.
