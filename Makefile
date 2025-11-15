.PHONY: help install run clean share-build share-up share-down share-logs share-shell env-copy

# Default target
.DEFAULT_GOAL := help

# Help command
help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation
install: ## Install dependencies with pip
	pip install -r requirements.txt

# Running locally (without Docker)
run: ## Run Streamlit application locally
	streamlit run streamlit_app.py

# Cleaning
clean: ## Clean up generated files
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf .venv/

# Environment setup
env-copy: ## Copy .env.example to .env
	cp .env.example .env

# Production Docker Build (for CI/CD with GitHub token)
build: ## Build production Docker image (requires GITHUB_TOKEN for private repo)
	@echo "Building production Docker image..."
	@echo "Note: This requires GITHUB_TOKEN to clone private web-backend repo"
	@echo ""
	@if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "ERROR: GITHUB_TOKEN environment variable not set"; \
		echo ""; \
		echo "For CI/CD: Set GITHUB_TOKEN in GitHub Actions secrets"; \
		echo "For local testing: Use 'make build-local' instead"; \
		echo ""; \
		exit 1; \
	fi
	DOCKER_BUILDKIT=1 docker build \
		--secret id=github_token,env=GITHUB_TOKEN \
		-t aicallgo-admin:latest .
	@echo ""
	@echo "Build complete! Image: aicallgo-admin:latest"

# Local Docker Build (uses local web-backend from infra-repo)
build-local: ## Build Docker image locally using web-backend submodule
	@echo "Building Docker image for local testing..."
	@echo "Using web-backend from ../web-backend (submodule)"
	@if [ ! -d "../web-backend/app/models" ]; then \
		echo ""; \
		echo "ERROR: web-backend not found at ../web-backend"; \
		echo ""; \
		echo "Make sure you're in the infra-repo and submodules are initialized:"; \
		echo "  git submodule update --init --recursive"; \
		echo ""; \
		exit 1; \
	fi
	cd .. && docker build -f admin-board/Dockerfile.local -t aicallgo-admin:local .
	@echo ""
	@echo "Build complete! Image: aicallgo-admin:local"
	@echo ""
	@echo "To run: docker run -d -p 8005:8501 --name admin-board aicallgo-admin:local"

# Alternative build with custom web-backend repo/branch (for CI)
build-custom: ## Build with custom web-backend repository or branch
	@echo "Building with custom web-backend configuration..."
	@if [ -z "$$GITHUB_TOKEN" ]; then \
		echo "ERROR: GITHUB_TOKEN environment variable not set"; \
		exit 1; \
	fi
	@read -p "Enter web-backend repository URL [https://github.com/blicktz/aicallgo-backend-cursor.git]: " repo; \
	repo=$${repo:-https://github.com/blicktz/aicallgo-backend-cursor.git}; \
	read -p "Enter web-backend branch [main]: " branch; \
	branch=$${branch:-main}; \
	DOCKER_BUILDKIT=1 docker build \
		--secret id=github_token,env=GITHUB_TOKEN \
		--build-arg WEB_BACKEND_REPO=$$repo \
		--build-arg WEB_BACKEND_BRANCH=$$branch \
		-t aicallgo-admin:latest .
	@echo ""
	@echo "Build complete! Image: aicallgo-admin:latest"

# Shared Docker Setup (with webbackend - for development)
share-build: ## Build Docker image for shared setup (development)
	docker-compose -f docker-compose.share.yml build

share-up: ## Start Admin Board with shared webbackend services
	docker-compose -f docker-compose.share.yml up -d

share-down: ## Stop shared Docker setup
	docker-compose -f docker-compose.share.yml down

share-logs: ## View shared Docker setup logs
	docker-compose -f docker-compose.share.yml logs -f

share-shell: ## Open shell in admin board container
	docker-compose -f docker-compose.share.yml exec admin_board bash

share-restart: ## Restart admin board container
	docker-compose -f docker-compose.share.yml restart admin_board

share-rebuild: ## Rebuild and restart shared Docker setup (down -> build -> up)
	$(MAKE) share-down && $(MAKE) share-build && $(MAKE) share-up

share-full: ## Complete shared setup with instructions
	@echo "Starting Admin Board with shared webbackend services..."
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Webbackend must be running: cd ../web-backend && docker-compose up -d"
	@echo "  2. Configure .env file with ADMIN_PASSWORD_HASH"
	@echo ""
	@echo "Starting Admin Board..."
	$(MAKE) share-up
	@echo ""
	@echo "Shared setup complete!"
	@echo "Admin Board: http://localhost:8005"
	@echo "Webbackend API: http://localhost:8000"
	@echo ""
	@echo "To view logs: make share-logs"
	@echo "To stop: make share-down"

# Development workflow
dev: install env-copy ## Set up development environment
	@echo "Development environment ready!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Edit .env with your configuration"
	@echo "  2. Generate password hash: python3 setup_helper.py"
	@echo "  3. Start webbackend: cd ../web-backend && docker-compose up -d"
	@echo "  4. Start admin board: make share-up"
	@echo ""
	@echo "Or run locally without Docker: make run"

# Setup helper
setup: ## Run interactive setup helper
	python3 setup_helper.py

# Password generation helper
generate-password: ## Generate bcrypt password hash (interactive)
	@echo "Checking for required dependencies..."
	@if ! python3 -c "import passlib" 2>/dev/null; then \
		echo ""; \
		echo "❌ passlib not installed"; \
		echo ""; \
		echo "Please install dependencies first:"; \
		echo "  pip install -r requirements.txt"; \
		echo ""; \
		echo "Then use one of these methods:"; \
		echo "  1. make setup              (recommended - interactive)"; \
		echo "  2. make generate-password  (command line)"; \
		echo "  3. make hash-password PASSWORD='yourpass'  (non-interactive)"; \
		echo ""; \
		exit 1; \
	fi
	@echo ""
	@python3 -c "from passlib.context import CryptContext; import getpass; pwd = getpass.getpass('Enter admin password: '); print('\nAdd this to .env:\nADMIN_PASSWORD_HASH=' + CryptContext(schemes=['bcrypt']).hash(pwd))"

hash-password: ## Generate hash for a specific password (non-interactive)
	@if [ -z "$(PASSWORD)" ]; then \
		echo "Usage: make hash-password PASSWORD='your-password'"; \
		echo "Example: make hash-password PASSWORD='MySecurePass123'"; \
		exit 1; \
	fi
	@echo ""
	@echo "Generating bcrypt hash..."
	@echo ""
	@python3 -c "import sys; from passlib.context import CryptContext; hash_val = CryptContext(schemes=['bcrypt']).hash('$(PASSWORD)'); escaped_hash = hash_val.replace('\$$', '\$$\$$'); print('Add this to .env (for docker-compose):\nADMIN_PASSWORD_HASH=' + escaped_hash); print('\nFor direct use (without docker-compose):\nADMIN_PASSWORD_HASH=' + hash_val)"
