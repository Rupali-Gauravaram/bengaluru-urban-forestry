# syntax=docker/dockerfile:1
###############################################################################
# Bengaluru Urban Forestry — multi-stage build
#
# Stage 1 (builder): installs dependencies into an isolated virtualenv.
# Stage 2 (runtime): copies ONLY the built virtualenv + app code into a clean,
#                    slim base. Build tools never reach the final image, so it
#                    is smaller and has a smaller attack surface.
###############################################################################

# ---------------------------------------------------------------------------
# Stage 1 — builder
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS builder

# Build-time system deps. shapely needs libgeos; pdfplumber pulls pillow which
# wants build headers. These live ONLY in the builder, never in runtime.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtualenv we can copy out wholesale into the next stage.
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app

# Dependencies first — this layer changes RARELY, so it caches across rebuilds.
# (Editing src/ below does NOT bust this expensive pip layer.)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Stage 2 — runtime
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Runtime system deps only: shapely needs the libgeos shared library at run time
# (the -dev headers from the builder are NOT needed here).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgeos-c1v5 \
    && rm -rf /var/lib/apt/lists/*

# Copy the ready-built virtualenv from the builder stage.
ENV VIRTUAL_ENV=/opt/venv
COPY --from=builder $VIRTUAL_ENV $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Run as a non-root user — never run containers as root in production.
RUN useradd --create-home --uid 1000 appuser
WORKDIR /app

# Code last — this layer changes OFTEN. A code edit rebuilds only from here down.
COPY src/ ./src/
COPY main.py ./

# Default data/output locations inside the container (mount real data over these).
ENV DATA_DIR=/app/data \
    OUTPUT_DIR=/app/output \
    PYTHONUNBUFFERED=1
RUN mkdir -p /app/data /app/output && chown -R appuser:appuser /app

USER appuser

# Batch pipeline: run all stages, write CSVs to /app/output, then exit.
ENTRYPOINT ["python", "main.py"]
