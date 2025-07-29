# =======================
# Stage 1: Builder
# =======================
FROM python:3.10.14-slim AS builder

# Environment settings
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies (needed for native packages like Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libjpeg-dev \
    zlib1g-dev \
    libpng-dev \
    libfreetype6-dev \
    liblcms2-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libwebp-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# =======================
# Stage 2: Final Image
# =======================
FROM python:3.10.14-slim

# Accept build args for UID/GID
ARG HOST_UID=1000
ARG HOST_GID=1000

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client \
    sshpass \
    bash \
    sqlite3 \
    libjpeg62-turbo \
    libopenjp2-7 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Create group and user with host UID/GID
RUN groupadd -g ${HOST_GID} appuser && \
    useradd -m -u ${HOST_UID} -g appuser appuser

# Copy Python site-packages and binaries from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy project files
COPY . .

# Prepare directories and set ownership
RUN mkdir -p /app/db /app/static/data && \
    chown -R ${HOST_UID}:${HOST_GID} /app/db /app/static/data

# Set permissions for entrypoint
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER appuser

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import os; os.system('echo OK')"]

# Default command
CMD ["/app/entrypoint.sh"]
