# NOOD backend container
# Multi-arch image: works on x86 (your laptop) and ARM (Oracle Cloud Ampere VM)

FROM python:3.11-slim

# ---------------------------------------------------------------------------
# System dependencies
#   ffmpeg          : extracts audio from uploaded videos
#   libgl1, libglib : required by opencv (it uses GUI libs even in headless mode)
#   libsndfile1     : required by soundfile (audio I/O)
#   gcc, g++, build : some pip packages compile from source on ARM
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libsndfile1 \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps FIRST (separate layer = faster rebuilds when only code changes)
COPY requirements.txt backend/requirements_api.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements_api.txt

# Copy the rest of the project
COPY . .

# Backend listens on 8000
EXPOSE 8000

# Models (~1.5 GB) are downloaded on first request into /app/hf_cache.
# Mount a volume there in `docker run` so they persist across container restarts:
#   docker run -v nood_models:/app/hf_cache ...
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
