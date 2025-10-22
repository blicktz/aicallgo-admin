# Docker Setup - Admin Board

## ✅ Files Created

1. **Dockerfile** - Production build (standalone, includes web-backend)
2. **Dockerfile.share** - Development build (uses volume mounts)
3. **.dockerignore** - Exclude unnecessary files from build
4. **docker-compose.share.yml** - Local development with shared services
5. **Makefile** - Convenient build and run commands

---

## 📦 Two Dockerfile Approach

### Dockerfile (Production - Standalone)
- **Purpose:** Self-contained production image
- **Build Context:** Parent directory (requires web-backend as sibling)
- **Includes:** Entire web-backend directory copied into image
- **Use Case:** Production deployment, CI/CD, distribution
- **Command:** `make build`

### Dockerfile.share (Development - Live Reload)
- **Purpose:** Fast development with live code changes
- **Build Context:** Current directory
- **Mounts:** web-backend via docker-compose volume
- **Use Case:** Local development, debugging
- **Command:** `make share-build`

---

## 🚀 Quick Start (Development Mode)

### Prerequisites

1. **Web-backend must be running first:**
   ```bash
   cd ../web-backend
   docker-compose up -d
   ```

2. **Configure environment:**
   ```bash
   cd ../admin-board

   # Copy environment file
   cp .env.example .env

   # Generate password hash
   make generate-password

   # Edit .env and add ADMIN_PASSWORD_HASH
   ```

### Start Admin Board

```bash
# Build Docker image
make share-build

# Start admin board
make share-up

# Access at http://localhost:8005
```

---

## 📋 Available Commands

### Build & Run (Production)
```bash
make build           # Build standalone production image (requires ../web-backend)
```

### Build & Run (Development)
```bash
make share-build     # Build development Docker image
make share-up        # Start admin board container
make share-down      # Stop admin board container
make share-restart   # Restart admin board
```

### Monitoring
```bash
make share-logs      # View logs (follow mode)
make share-shell     # Open bash shell in container
```

### Development
```bash
make run             # Run locally without Docker
make install         # Install dependencies locally
make clean           # Clean Python cache files
make help            # Show all available commands
```

### Setup
```bash
make env-copy           # Copy .env.example to .env
make generate-password  # Interactive password generation
make setup              # Run setup_helper.py
```

---

## 🏗️ Architecture

### Network Configuration

**Network:** `aicallgo_cursor_aicallgo_network` (external, created by web-backend)

**Services:**
```
aicallgo_network
├── aicallgo_postgres:5432     (PostgreSQL)
├── aicallgo_redis:6379        (Redis)
├── aicallgo_app:8000          (Web Backend)
├── ai_agent_backend:8001      (AI Agent)
└── aicallgo_admin_board:8501  (Admin Board)
```

### Port Mapping

- **Host:** `8005` (external access)
- **Container:** `8501` (Streamlit internal)
- **Mapping:** `8005:8501`

### Database Access

**PostgreSQL:**
- Docker URL: `postgresql://postgres:password@aicallgo_postgres:5432/aicallgo_dev`
- Accessible via shared Docker network

**Redis:**
- Docker URL: `redis://:aicallgo_redis_password@aicallgo_redis:6379/0`
- Accessible via shared Docker network

### Volume Mounts

**Live Reload (development):**
- `./app.py` → `/app/app.py`
- `./config` → `/app/config`
- `./database` → `/app/database`
- `./static` → `/app/static`
- `./.env` → `/app/.env`

**Web-backend Models:**
- `../web-backend` → `/app/web-backend`
- Provides access to database models (single source of truth)

---

## 🔧 Dockerfile Details

**Base Image:** `python:3.12-slim`

**System Dependencies:**
- build-essential
- libpq-dev (PostgreSQL client)
- curl (health checks)

**Security:**
- Runs as non-root user `appuser` (UID 1000)
- No unnecessary packages included

**Health Check:**
- Endpoint: `http://localhost:8501/_stcore/health`
- Interval: 30s
- Timeout: 10s
- Retries: 3

**Command:**
```bash
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

---

## 🐛 Troubleshooting

### Container won't start

**Check web-backend is running:**
```bash
docker ps | grep aicallgo
# Should see: aicallgo_postgres, aicallgo_redis, aicallgo_app
```

**Check network exists:**
```bash
docker network ls | grep aicallgo_cursor
# Should see: aicallgo_cursor_aicallgo_network
```

**View container logs:**
```bash
make share-logs
```

### Cannot connect to database

**Check PostgreSQL container:**
```bash
docker ps | grep postgres
docker logs aicallgo_postgres
```

**Test database connection:**
```bash
make share-shell
# Inside container:
psql postgresql://postgres:password@aicallgo_postgres:5432/aicallgo_dev
```

### Web-backend models not found

**Check volume mount:**
```bash
make share-shell
# Inside container:
ls -la /app/web-backend/app/models/
```

**Verify web-backend location:**
```bash
ls -la ../web-backend/app/models/
```

### Port 8005 already in use

**Find process using port:**
```bash
lsof -i :8005
```

**Stop conflicting service:**
```bash
# Kill the process or change admin board port in docker-compose.share.yml
```

---

## 🔄 Complete Workflow

### Initial Setup (One Time)
```bash
# 1. Start web-backend
cd ../web-backend
docker-compose up -d

# 2. Setup admin board
cd ../admin-board
make env-copy
make generate-password
# Edit .env with password hash

# 3. Build and start
make share-build
make share-up
```

### Daily Development
```bash
# Start admin board (web-backend already running)
make share-up

# View logs
make share-logs

# Make code changes (auto-reload enabled)

# Restart if needed
make share-restart

# Stop when done
make share-down
```

---

## 📦 Production Deployment

The `Dockerfile` creates a self-contained image with web-backend included.

### Prerequisites for Production Build

```bash
# Clone both repositories as siblings
cd parent-directory
git clone https://github.com/blicktz/aicallgo-admin.git
git clone https://github.com/your-org/web-backend.git

# Directory structure:
# parent-directory/
# ├── aicallgo-admin/
# └── web-backend/
```

### Build Production Image

**Using Makefile (recommended):**
```bash
cd aicallgo-admin
make build
```

**Manual build:**
```bash
cd parent-directory
docker build -f aicallgo-admin/Dockerfile -t aicallgo-admin:latest .
```

### Run Production Container

**Run standalone:**
```bash
docker run -d \
  -p 8005:8501 \
  -e DATABASE_URL="postgresql://..." \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD_HASH="..." \
  --name aicallgo-admin \
  aicallgo-admin:latest
```

### Use Cases

- **Digital Ocean Kubernetes:** Deploy Phase 6
- **Container Registry:** Push for distribution
- **CI/CD:** Automated builds in GitHub Actions
- **Cloud Deployment:** AWS, GCP, Azure

---

## 🎯 Next Steps

1. **Phase 2:** Add read-only data pages (Users, Businesses, Call Logs)
2. **Phase 3:** Add data manipulation features
3. **Phase 6:** Deploy to Digital Ocean Kubernetes
4. **CI/CD:** Add GitHub Actions for automated builds

---

## 📚 References

- **Docker Compose Docs:** https://docs.docker.com/compose/
- **Streamlit Docker:** https://docs.streamlit.io/knowledge-base/tutorials/deploy/docker
- **Pattern Source:** Based on `ai-agent-backend/docker-compose.share.yml`

---

**Status:** ✅ Docker setup complete and ready for development!
