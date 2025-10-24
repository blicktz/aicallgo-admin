# AICallGO Admin Board

Internal administration dashboard for managing AICallGO platform operations.

## Overview

This is a Streamlit-based admin interface for:
- User and business management
- Call log monitoring
- Billing and subscription administration
- Feature entitlement management
- Credit balance adjustments

## Technology Stack

- **Framework**: Streamlit 1.32.0
- **Database**: PostgreSQL with async SQLAlchemy 2.0.23
- **Authentication**: Bcrypt password hashing with session management
- **Design**: Custom CSS matching Next.js frontend theme

## Project Structure

```
admin-board/
├── app.py                    # Main Streamlit entry point
├── requirements.txt          # Python dependencies
├── .env.example             # Example environment variables
├── .streamlit/
│   └── config.toml          # Streamlit configuration
├── config/
│   ├── settings.py          # Environment variable management
│   └── auth.py              # Authentication logic
├── database/
│   ├── connection.py        # Async SQLAlchemy setup
│   └── models.py            # Models imported from web-backend
├── static/
│   └── custom.css           # Design system CSS
├── components/              # Reusable UI components (Phase 2+)
├── services/                # Business logic services (Phase 2+)
├── utils/                   # Helper functions (Phase 2+)
└── pages/                   # Streamlit pages (Phase 2+)
```

## Setup Instructions

### Option A: Production Docker Build (Standalone)

Build a self-contained Docker image with web-backend models included.

#### Prerequisites
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

#### Build and Run
```bash
cd aicallgo-admin

# 1. Build production image (includes web-backend)
make build

# 2. Run container
docker run -d \
  -p 8005:8501 \
  -e DATABASE_URL="postgresql://..." \
  -e ADMIN_USERNAME="admin" \
  -e ADMIN_PASSWORD_HASH="..." \
  --name aicallgo-admin \
  aicallgo-admin:latest

# Access at http://localhost:8005
```

**Note:** The production Dockerfile copies the entire web-backend directory during build, creating a standalone image.

---

### Option B: Docker Compose (Development with Live Reload)

Run with docker-compose using volume mounts for fast development.

#### Prerequisites
- Docker and Docker Compose installed
- Web-backend service running: `cd ../web-backend && docker-compose up -d`

#### Quick Start
```bash
cd aicallgo-admin

# 1. Copy environment file
cp .env.example .env

# 2. Generate password hash
make generate-password

# 3. Edit .env and add the generated ADMIN_PASSWORD_HASH

# 4. Build and start admin board
make share-build
make share-up

# Access at http://localhost:8005
```

#### Docker Commands
```bash
# View logs
make share-logs

# Open shell in container
make share-shell

# Restart admin board
make share-restart

# Stop admin board
make share-down
```

---

### Option C: Local Setup (Without Docker)

#### 1. Install Dependencies

```bash
cd /services/admin-board

# Create virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

#### 2. Generate Admin Password Hash

```bash
# Install passlib if not already installed
pip install "passlib[bcrypt]"

# Generate password hash
python3 -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('YourSecurePassword123!'))"

# Example output: $2b$12$KIX8tWq2mZQX5V...
```

#### 3. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and update:
# - DATABASE_URL with your PostgreSQL connection string
# - ADMIN_PASSWORD_HASH with the hash from step 2
```

Example `.env`:
```env
DATABASE_URL=postgresql://aicallgo_user:password@localhost:5432/aicallgo_staging
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=$2b$12$...
APP_ENV=development
DEBUG=true
SESSION_TIMEOUT_HOURS=8
```

#### 4. Port-Forward to Staging Database (for local development)

```bash
# Set kubeconfig
export KUBECONFIG=~/staging-kubeconfig.txt

# Port-forward PostgreSQL
kubectl port-forward -n aicallgo-staging svc/postgres-postgresql 5432:5432

# Keep this terminal open while running the admin board
```

#### 5. Run Streamlit

```bash
streamlit run app.py

# Should see:
#   You can now view your Streamlit app in your browser.
#   Local URL: http://localhost:8501
```

## Usage

### Authentication

**Docker (recommended):**
- Navigate to `http://localhost:8005`

**Local setup:**
- Navigate to `http://localhost:8501`

Login with the username and password you configured. Session expires after 8 hours of inactivity.

### Features (Phase 1)

Current Phase 1 features:
- ✅ Secure authentication with bcrypt
- ✅ Database connection health check
- ✅ System information dashboard
- ✅ Custom design matching Next.js frontend

### Upcoming Features

**Phase 2 (4-5 days)**: Read-only pages
- Dashboard with KPIs and charts
- User search and detail view
- Business profiles and configuration
- Call log history with transcripts
- Billing and subscription monitoring

**Phase 3 (5-6 days)**: Data manipulation
- Feature entitlement management
- Credit balance adjustments
- Transaction audit trails

## Development

### Database Models

Models are imported directly from `web-backend/app/models/` to ensure schema consistency. Any changes to the database schema should be made in the web-backend service.

### Authentication

The authentication system uses:
- Bcrypt password hashing (matching web-backend security patterns)
- Streamlit session state for session management
- Configurable session timeout (default: 8 hours)

### Design System

The custom CSS (`static/custom.css`) matches the color palette from `nextjs-frontend/tailwind.config.ts`:
- Primary: `#5f8a4e` (green-toned purple-500)
- Gray scale: Standard Tailwind gray palette
- Consistent typography and spacing

## Troubleshooting

### Database Connection Fails

```bash
# Check port-forward is running
lsof -i :5432

# Test direct connection
psql "postgresql://aicallgo_user:password@localhost:5432/aicallgo_staging"
```

### Login Fails

```bash
# Verify password hash in .env
cat .env | grep ADMIN_PASSWORD_HASH

# Test password verification
python3 -c "
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'])
hash = '\$2b\$12\$...'  # your hash
plain = 'YourPassword'
print('Valid:', pwd_context.verify(plain, hash))
"
```

### CSS Not Loading

```bash
# Check file exists
ls -la static/custom.css

# Restart Streamlit (CSS is loaded on startup)
# Press Ctrl+C and run again
streamlit run app.py
```

### Import Errors

```bash
# Verify web-backend path
ls -la ../web-backend/app/models/

# Ensure web-backend is in the correct location relative to admin-board
```

## Docker Architecture

### Two Dockerfile Approach

The admin board provides two Dockerfiles for different use cases:

**1. `Dockerfile` (Production - Standalone)**
- **Build Context:** Parent directory (containing both aicallgo-admin and web-backend)
- **Copies:** Entire web-backend directory into image
- **Use Case:** Production deployment, CI/CD, standalone distribution
- **Build Command:** `make build` or `cd .. && docker build -f aicallgo-admin/Dockerfile -t aicallgo-admin:latest .`
- **Result:** Self-contained image (no external dependencies)

**2. `Dockerfile.share` (Development - Volume Mounts)**
- **Build Context:** Current directory (aicallgo-admin)
- **Mounts:** web-backend via docker-compose volume
- **Use Case:** Local development with live reload
- **Build Command:** `make share-build` or `docker-compose -f docker-compose.share.yml build`
- **Result:** Fast rebuilds, code changes reflected immediately

### Network Topology (Development Mode)

When using docker-compose.share.yml, the admin board joins a shared Docker network:

```
aicallgo_network (Docker bridge)
├── aicallgo_postgres (PostgreSQL - managed by web-backend)
├── aicallgo_redis (Redis - managed by web-backend)
├── aicallgo_app (Web Backend API - port 8000)
├── ai_agent_backend (AI Agent - port 8001)
└── aicallgo_admin_board (Admin Board - port 8005)
```

### Service Communication

**Admin Board connects to:**
- PostgreSQL: `aicallgo_postgres:5432` (Docker internal URL)
- Redis: `aicallgo_redis:6379` (Docker internal URL)
- Web-backend models: via volume mount at `/app/web-backend`

**Port Mapping:**
- Host port: `8005`
- Container port: `8501` (Streamlit default)

### Volume Mounts

Live reload is enabled for development:
- `./app.py`, `./config`, `./database`, `./static` → Hot reload application code
- `../web-backend` → Access to database models (single source of truth)
- `./.env` → Local environment configuration

### Prerequisites

The admin board requires web-backend to be running first:
```bash
cd ../web-backend
docker-compose up -d
```

This creates:
- `aicallgo_cursor_aicallgo_network` Docker bridge network
- `aicallgo_postgres` PostgreSQL container
- `aicallgo_redis` Redis container

## Security Notes

- Never commit `.env` file to version control
- Use strong passwords and rotate them regularly
- Session timeout is configurable via `SESSION_TIMEOUT_HOURS`
- XSRF protection is enabled in Streamlit config
- Database credentials should only be in environment variables

## Testing Checklist

**Authentication Tests:**
- [ ] Login page appears
- [ ] Invalid credentials show error
- [ ] Valid credentials grant access
- [ ] Session persists across refreshes
- [ ] Logout clears session
- [ ] Session timeout works

**Database Tests:**
- [ ] Health check succeeds
- [ ] Statistics display correctly
- [ ] No connection errors in logs

**Design Tests:**
- [ ] Colors match frontend theme
- [ ] Typography is consistent
- [ ] Buttons have proper styling
- [ ] Messages display correctly

## Contributing

This admin board follows the implementation plan in `docs/IMPLEMENTATION_PLAN.md` and `docs/PHASE_1_DETAILED_PLAN.md`.

When adding new features:
1. Follow the phased approach outlined in the docs
2. Maintain consistency with web-backend patterns
3. Keep design aligned with Next.js frontend
4. Document any new environment variables in `.env.example`

## Support

For issues or questions:
- Check the implementation plan documents in `docs/`
- Review the web-backend service for model definitions
- Consult the Phase 1 detailed plan for setup guidance

## License

Internal tool for AICallGO platform. Not for external distribution.


### trigger deploy 2