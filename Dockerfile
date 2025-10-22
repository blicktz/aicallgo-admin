# ============================================================================
# Stage 1: Clone web-backend repository (for CI/CD with private repo)
# ============================================================================
FROM python:3.12-slim AS deps-stage

# Install git for cloning
RUN apt-get update && apt-get install -y \
    git \
    ca-certificates \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Set build arguments for web-backend repository
ARG WEB_BACKEND_REPO=https://github.com/blicktz/aicallgo-backend-cursor.git
ARG WEB_BACKEND_BRANCH=main
ARG USE_LOCAL_COPY=false

# Clone web-backend repository using GitHub token from build secret
# This supports private repositories in CI/CD
WORKDIR /tmp
RUN --mount=type=secret,id=github_token \
    if [ "$USE_LOCAL_COPY" = "false" ]; then \
        if [ -f /run/secrets/github_token ]; then \
            GITHUB_TOKEN=$(cat /run/secrets/github_token); \
            git clone --depth 1 --branch ${WEB_BACKEND_BRANCH} \
                https://x-access-token:${GITHUB_TOKEN}@github.com/blicktz/aicallgo-backend-cursor.git \
                web-backend; \
        else \
            echo "ERROR: github_token secret not provided and USE_LOCAL_COPY=false"; \
            echo "For CI builds: docker build --secret id=github_token,env=GITHUB_TOKEN ..."; \
            echo "For local builds: Use Dockerfile.local instead"; \
            exit 1; \
        fi; \
    fi

# ============================================================================
# Stage 2: Final application image
# ============================================================================
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    libssl-dev \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy web-backend models from deps stage
# Only copy what's needed: app/models/ and app/db/base_class.py
COPY --from=deps-stage /tmp/web-backend/app/models ./web-backend/app/models
COPY --from=deps-stage /tmp/web-backend/app/db ./web-backend/app/db

# Copy admin-board requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy admin-board application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose Streamlit default port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run Streamlit application
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
