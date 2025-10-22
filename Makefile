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
	streamlit run app.py

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

# Production Docker Build (standalone)
build: ## Build production Docker image (requires web-backend as sibling)
	@echo "Building production Docker image..."
	@echo "Prerequisites: web-backend repo must exist as sibling directory"
	@if [ ! -d "../web-backend" ]; then \
		echo "ERROR: web-backend not found at ../web-backend"; \
		echo "Please clone web-backend as a sibling directory"; \
		exit 1; \
	fi
	cd .. && docker build -f aicallgo-admin/Dockerfile -t aicallgo-admin:latest .
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
	@python3 -c "from passlib.context import CryptContext; print('\nAdd this to .env:\nADMIN_PASSWORD_HASH=' + CryptContext(schemes=['bcrypt']).hash('$(PASSWORD)'))"
