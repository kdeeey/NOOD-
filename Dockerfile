# NOOD backend container
# Multi-arch image: works on x86 (your laptop) and ARM (Railway VMs)

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
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project
COPY . .

# Expose port (for clarity; Railway uses PORT env var)
EXPOSE 8000

# Start FastAPI server
# Railway sets PORT env var; fallback to 8080 if not set
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8080}"]

# Backend listens on 8000
EXPOSE 8000

# Models (~1.5 GB) are downloaded on first request into /app/hf_cache.
# Mount a volume there in `docker run` so they persist across container restarts:
#   docker run -v nood_models:/app/hf_cache ...
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
