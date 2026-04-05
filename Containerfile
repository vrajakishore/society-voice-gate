# Society Voice Gate — Podman/Docker build
# Works with: podman build, docker build, buildah bud

FROM python:3.12-slim

WORKDIR /app

# curl is needed by the compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install dependencies first (cache layer)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY backend/app ./app

# Persistent ticket store (mount a volume over this in production)
RUN mkdir -p /app/data

EXPOSE 8000

# Run as non-root for security
# -m creates /home/appuser so the ~/.azure volume mount lands correctly
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
ENV HOME=/home/appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
