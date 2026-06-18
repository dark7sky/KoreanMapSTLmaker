FROM python:3.11-slim-bookworm

WORKDIR /workspace

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_DATA_DIR=/workspace/data \
    APP_OUTPUT_DIR=/workspace/output \
    APP_SAMPLE_DIR=/workspace/data/sample

RUN apt-get update \
    && apt-get install -y --no-install-recommends gdal-bin libgdal-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt fastapi uvicorn[standard]

COPY . .

EXPOSE 8000

CMD ["uvicorn", "web_api.app:app", "--host", "0.0.0.0", "--port", "8000"]
