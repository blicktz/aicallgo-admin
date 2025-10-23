# Phase 5: Admin Board Deployment Plan

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Infrastructure Updates (Terraform)](#infrastructure-updates-terraform)
4. [GitHub CI/CD Setup](#github-cicd-setup)
5. [GitHub Secrets Configuration](#github-secrets-configuration)
6. [Deployment Process](#deployment-process)
7. [DNS and SSL Configuration](#dns-and-ssl-configuration)
8. [Validation and Testing](#validation-and-testing)
9. [Rollback Procedure](#rollback-procedure)
10. [Post-Deployment Tasks](#post-deployment-tasks)

---

## Overview

### Objectives
Deploy the Admin Board service to Digital Ocean Kubernetes cluster for both staging and production environments with automated CI/CD.

### Architecture
- **Service Type**: Streamlit web application
- **Port**: 8501 (internal container port)
- **Dependencies**: PostgreSQL database (shared with web-backend)
- **Authentication**: Password-based (ADMIN_PASSWORD_HASH environment variable)
- **Deployment Strategy**: Rolling update with zero-downtime
- **CI/CD**: GitHub Actions with automatic deployment on push to staging/main branches

### Success Criteria
- [ ] Admin board accessible at `staging-admin.julya.ai` (staging) and `admin.julya.ai` (production)
- [ ] SSL certificate automatically provisioned
- [ ] CI/CD pipeline functioning for both staging and production
- [ ] Database connection working (read/write access)
- [ ] Authentication system operational
- [ ] All core features accessible (Dashboard, Users, Businesses, etc.)

---

## Prerequisites

### Completed Tasks
- ✅ Phase 1-4 implementation complete
- ✅ Dockerfile created and tested
- ✅ Admin board repository: https://github.com/blicktz/aicallgo-admin
- ✅ Admin board added as submodule to infra-repo

### Required Access
- [ ] GitHub admin access to `blicktz/aicallgo-admin` repository
- [ ] Digital Ocean infrastructure admin access
- [ ] Terraform state access (Spaces backend)
- [ ] Domain DNS management access (Cloudflare)

### Environment Preparation
- [ ] Terraform workspace `staging` ready
- [ ] Terraform workspace `prod` ready (when needed)
- [ ] `source .envrc` configured for Digital Ocean authentication

---

## Infrastructure Updates (Terraform)

### Step 1: Add Admin Board Variables

**File**: `/Users/blickt/Documents/src/aicallgo-infra-repo/terraform/variables.tf`

Add the following variable after the other image tag variables:

```hcl
variable "admin_board_image_tag" {
  description = "Image tag for admin-board service"
  type        = string
  default     = "latest"
}
```

**Files**: `terraform/staging-public.tfvars` and `terraform/prod-public.tfvars`

Add:
```hcl
# Admin Board Configuration
admin_board_image_tag = "latest"  # Will be updated by CI/CD
```

### Step 2: Add Admin Board Resource Configuration Variables

**File**: `terraform/variables.tf`

Add resource configuration variables:

```hcl
# Admin Board Resource Configuration
variable "admin_board_cpu_request" {
  description = "CPU request for admin-board"
  type        = string
  default     = "100m"
}

variable "admin_board_cpu_limit" {
  description = "CPU limit for admin-board"
  type        = string
  default     = "500m"
}

variable "admin_board_memory_request" {
  description = "Memory request for admin-board"
  type        = string
  default     = "256Mi"
}

variable "admin_board_memory_limit" {
  description = "Memory limit for admin-board"
  type        = string
  default     = "512Mi"
}
```

**Files**: `terraform/staging-public.tfvars` and `terraform/prod-public.tfvars`

Add:
```hcl
# Admin Board Resources
admin_board_cpu_request    = "100m"
admin_board_cpu_limit      = "500m"
admin_board_memory_request = "256Mi"
admin_board_memory_limit   = "512Mi"
```

### Step 3: Pass Variables to k8s_config Module

**File**: `terraform/main.tf`

Add to the `module "k8s_config"` block (around line 350-430):

```hcl
  # Admin Board Configuration
  admin_board_image_tag      = var.admin_board_image_tag
  admin_board_cpu_request    = var.admin_board_cpu_request
  admin_board_cpu_limit      = var.admin_board_cpu_limit
  admin_board_memory_request = var.admin_board_memory_request
  admin_board_memory_limit   = var.admin_board_memory_limit
  admin_password_hash        = var.admin_password_hash
```

### Step 4: Add Admin Password Variable

**File**: `terraform/variables.tf`

```hcl
variable "admin_password_hash" {
  description = "Bcrypt hash of admin password for admin board"
  type        = string
  sensitive   = true
}
```

**Files**: `terraform/staging-public.tfvars` and `terraform/prod-public.tfvars`

```hcl
# Admin Board Authentication
admin_password_hash = "YOUR_BCRYPT_HASH_HERE"  # Generate using: python -c "import bcrypt; print(bcrypt.hashpw(b'your_password', bcrypt.gensalt()).decode())"
```

### Step 5: Update k8s_config Module Variables

**File**: `terraform/modules/k8s_config/variables.tf`

Add at the end:

```hcl
# Admin Board Configuration
variable "admin_board_image_tag" {
  description = "Image tag for admin-board service"
  type        = string
}

variable "admin_board_cpu_request" {
  description = "CPU request for admin-board"
  type        = string
}

variable "admin_board_cpu_limit" {
  description = "CPU limit for admin-board"
  type        = string
}

variable "admin_board_memory_request" {
  description = "Memory request for admin-board"
  type        = string
}

variable "admin_board_memory_limit" {
  description = "Memory limit for admin-board"
  type        = string
}

variable "admin_password_hash" {
  description = "Bcrypt hash of admin password"
  type        = string
  sensitive   = true
}
```

### Step 6: Create Admin Board Deployment

**File**: `terraform/modules/k8s_config/deployments.tf`

Add at the end of the file:

```hcl
# Admin Board Deployment
resource "kubernetes_deployment" "admin_board" {
  metadata {
    name      = "admin-board"
    namespace = var.namespace

    labels = {
      app        = "admin-board"
      component  = "admin"
      managed_by = "terraform"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app       = "admin-board"
        component = "admin"
      }
    }

    template {
      metadata {
        labels = {
          app       = "admin-board"
          component = "admin"
        }

        annotations = {
          # Force pod restart on secret changes
          "checksum/secrets" = sha256(jsonencode(kubernetes_secret.admin_board_secrets.data))
        }
      }

      spec {
        # Use the registry pull secret
        image_pull_secrets {
          name = kubernetes_secret.registry_pull_secret.metadata[0].name
        }

        # Security context for the pod
        security_context {
          run_as_non_root = true
          run_as_user     = 1000
          fs_group        = 1000
          seccomp_profile {
            type = "RuntimeDefault"
          }
        }

        container {
          name  = "admin-board"
          image = "${var.registry_endpoint}/aicallgo-${var.environment}/admin-board:${local.final_image_tags["admin-board"]}"

          # Container ports
          port {
            name           = "http"
            container_port = 8501
            protocol       = "TCP"
          }

          # Environment variables from secret
          env_from {
            secret_ref {
              name = kubernetes_secret.admin_board_secrets.metadata[0].name
            }
          }

          # Resource limits
          resources {
            requests = {
              cpu    = var.admin_board_cpu_request
              memory = var.admin_board_memory_request
            }
            limits = {
              cpu    = var.admin_board_cpu_limit
              memory = var.admin_board_memory_limit
            }
          }

          # Liveness probe
          liveness_probe {
            http_get {
              path = "/_stcore/health"
              port = 8501
            }
            initial_delay_seconds = 30
            period_seconds        = 10
            timeout_seconds       = 5
            failure_threshold     = 3
          }

          # Readiness probe
          readiness_probe {
            http_get {
              path = "/_stcore/health"
              port = 8501
            }
            initial_delay_seconds = 10
            period_seconds        = 5
            timeout_seconds       = 3
            failure_threshold     = 3
          }

          # Security context
          security_context {
            allow_privilege_escalation = false
            read_only_root_filesystem  = false
            run_as_non_root            = true
            run_as_user                = 1000
            capabilities {
              drop = ["ALL"]
            }
            seccomp_profile {
              type = "RuntimeDefault"
            }
          }
        }
      }
    }
  }

  # Lifecycle management
  lifecycle {
    ignore_changes = [
      spec[0].template[0].spec[0].container[0].image
    ]
  }
}
```

### Step 7: Create Admin Board Service

**File**: `terraform/modules/k8s_config/services.tf`

Add at the end:

```hcl
# Admin Board Service
resource "kubernetes_service" "admin_board" {
  metadata {
    name      = "admin-board"
    namespace = var.namespace

    labels = {
      app        = "admin-board"
      component  = "admin"
      managed_by = "terraform"
    }
  }

  spec {
    type = "ClusterIP"

    selector = {
      app       = "admin-board"
      component = "admin"
    }

    port {
      name        = "http"
      port        = 8501
      target_port = 8501
      protocol    = "TCP"
    }

    session_affinity = "ClientIP"

    session_affinity_config {
      client_ip {
        timeout_seconds = 10800 # 3 hours
      }
    }
  }

  depends_on = [
    kubernetes_deployment.admin_board
  ]
}
```

### Step 8: Create Admin Board Secret

**File**: `terraform/modules/k8s_config/secrets.tf`

Add at the end:

```hcl
# Admin Board Secrets
resource "kubernetes_secret" "admin_board_secrets" {
  metadata {
    name      = "admin-board-secrets"
    namespace = var.namespace

    labels = {
      app        = "admin-board"
      managed_by = "terraform"
    }
  }

  type = "Opaque"

  data = {
    # Database connection (async PostgreSQL)
    DATABASE_URL = "postgresql+asyncpg://${var.postgres_username}:${var.postgres_password}@${var.postgres_private_host}:${var.postgres_port}/${var.postgres_database}"

    # Authentication
    ADMIN_PASSWORD_HASH = var.admin_password_hash

    # Application settings
    ENVIRONMENT = var.environment
  }
}
```

### Step 9: Update Ingress Configuration

**File**: `terraform/modules/k8s_config/ingress.tf`

Update the TLS hosts section to include admin subdomain:

```hcl
spec {
  tls {
    hosts = [
      var.domain_name,
      var.environment == "staging" ? "staging-admin.${replace(var.domain_name, "staging.", "")}" : "admin.${var.domain_name}",
      var.environment == "staging" ? "staging-n8n.${replace(var.domain_name, "staging.", "")}" : "n8n.${var.domain_name}",
      var.environment == "staging" ? "staging-odoo.${replace(var.domain_name, "staging.", "")}" : "odoo.${var.domain_name}"
    ]
    secret_name = "aicallgo-tls-${var.environment}"
  }
```

Add the admin board ingress rule (add after the odoo rule, before closing the `spec` block):

```hcl
  # Admin Board
  rule {
    host = var.environment == "staging" ? "staging-admin.${replace(var.domain_name, "staging.", "")}" : "admin.${var.domain_name}"

    http {
      path {
        path      = "/"
        path_type = "Prefix"

        backend {
          service {
            name = "admin-board"
            port {
              number = 8501
            }
          }
        }
      }
    }
  }
```

### Step 10: Update Image Tags Data Source

**File**: `terraform/modules/k8s_config/data.tf`

Add admin-board to the `local.final_image_tags` map:

```hcl
locals {
  # ... existing code ...

  final_image_tags = var.use_dynamic_image_tags ? {
    "web-backend"       = data.external.latest_image_tags[0].result["web-backend"]
    "ai-agent-backend"  = data.external.latest_image_tags[0].result["ai-agent-backend"]
    "nextjs-frontend"   = data.external.latest_image_tags[0].result["nextjs-frontend"]
    "chatwoot-frontend" = data.external.latest_image_tags[0].result["chatwoot-frontend"]
    "crawl4ai-service"  = data.external.latest_image_tags[0].result["crawl4ai-service"]
    "admin-board"       = data.external.latest_image_tags[0].result["admin-board"]
  } : {
    "web-backend"       = var.web_backend_image_tag
    "ai-agent-backend"  = var.ai_agent_backend_image_tag
    "nextjs-frontend"   = var.nextjs_frontend_image_tag
    "chatwoot-frontend" = var.chatwoot_frontend_image_tag
    "crawl4ai-service"  = var.crawl4ai_service_image_tag
    "admin-board"       = var.admin_board_image_tag
  }
}
```

---

## GitHub CI/CD Setup

### Step 1: Create GitHub Actions Workflow

**File**: `/Users/blickt/Documents/src/aicallgo-infra-repo/services/admin-board/.github/workflows/deploy.yml`

Create the directory and file:

```bash
mkdir -p .github/workflows
```

**Content** (adapt from web-backend pattern):

```yaml
name: Deploy Admin Board

on:
  push:
    branches: [staging, main]
  repository_dispatch:
    types: [infrastructure-updated]
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to deploy to'
        type: choice
        options: [staging, production]
        default: staging

jobs:
  deploy:
    name: Deploy to Kubernetes
    runs-on: ubuntu-latest
    environment: ${{ github.event.inputs.environment || github.event.client_payload.environment || (github.ref == 'refs/heads/main' && 'production' || 'staging') }}

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.11.4

      - name: Set up environment variables
        id: setup
        run: |
          # Determine workspace based on environment
          ENV_NAME="${{ github.event.inputs.environment || github.event.client_payload.environment || (github.ref == 'refs/heads/main' && 'production' || 'staging') }}"

          if [[ "$ENV_NAME" == "production" || "$ENV_NAME" == "prod" ]]; then
            echo "workspace=prod" >> $GITHUB_OUTPUT
            echo "backend_config=backend.hcl" >> $GITHUB_OUTPUT
          else
            echo "workspace=staging" >> $GITHUB_OUTPUT
            echo "backend_config=backend.hcl" >> $GITHUB_OUTPUT
          fi

          # Use commit SHA with timestamp for unique image tag
          IMAGE_TAG="${{ github.sha }}-$(date +%Y%m%d-%H%M%S)"
          echo "image_tag=$IMAGE_TAG" >> $GITHUB_OUTPUT

      - name: Get infrastructure configuration
        id: infra
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.SPACES_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.SPACES_SECRET_KEY }}
          DIGITALOCEAN_ACCESS_TOKEN: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}
        run: |
          echo "🔍 Fetching infrastructure configuration from Terraform state..."

          # Clone infrastructure repo
          git clone https://x-access-token:${{ secrets.INFRA_REPO_TOKEN }}@github.com/${{ github.repository_owner }}/aicallgo-infra-repo.git /tmp/infra
          cd /tmp/infra/terraform

          # Initialize Terraform with remote backend
          terraform init -backend-config=${{ steps.setup.outputs.backend_config }} -backend-config="key=terraform.tfstate"
          terraform workspace select ${{ steps.setup.outputs.workspace }}

          # Extract outputs
          REGISTRY_URL=$(terraform output -raw registry_endpoint)
          NAMESPACE=$(terraform output -raw kubernetes_namespace)
          DOMAIN=$(terraform output -raw domain_name)
          CLUSTER_ID=$(terraform output -raw cluster_id)

          echo "registry_url=$REGISTRY_URL" >> $GITHUB_OUTPUT
          echo "namespace=$NAMESPACE" >> $GITHUB_OUTPUT
          echo "domain=$DOMAIN" >> $GITHUB_OUTPUT
          echo "cluster_id=$CLUSTER_ID" >> $GITHUB_OUTPUT

          echo "✅ Retrieved configuration for ${{ steps.setup.outputs.workspace }} environment"
          echo "   Registry: $REGISTRY_URL"
          echo "   Namespace: $NAMESPACE"
          echo "   Domain: $DOMAIN"

      - name: Install doctl
        uses: digitalocean/action-doctl@v2
        with:
          token: ${{ secrets.DIGITALOCEAN_ACCESS_TOKEN }}

      - name: Log in to DigitalOcean Container Registry
        run: |
          doctl registry login --expiry-seconds 1200

      - name: Configure kubectl with fresh credentials
        run: |
          echo "🔐 Getting fresh kubeconfig for cluster..."
          doctl kubernetes cluster kubeconfig save ${{ steps.infra.outputs.cluster_id }} --expiry-seconds 600
          echo "✅ kubectl configured with fresh credentials (10-minute expiry)"

      - name: Build Docker image
        run: |
          docker build \
            -f ./Dockerfile \
            --secret id=github_token,env=GITHUB_TOKEN \
            --build-arg WEB_BACKEND_REPO=https://github.com/blicktz/aicallgo-backend-cursor.git \
            --build-arg WEB_BACKEND_BRANCH=main \
            -t ${{ steps.infra.outputs.registry_url }}/aicallgo-${{ steps.setup.outputs.workspace }}/admin-board:${{ steps.setup.outputs.image_tag }} \
            -t ${{ steps.infra.outputs.registry_url }}/aicallgo-${{ steps.setup.outputs.workspace }}/admin-board:latest \
            .
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          DOCKER_BUILDKIT: 1

      - name: Push Docker image
        run: |
          docker push ${{ steps.infra.outputs.registry_url }}/aicallgo-${{ steps.setup.outputs.workspace }}/admin-board:${{ steps.setup.outputs.image_tag }}
          docker push ${{ steps.infra.outputs.registry_url }}/aicallgo-${{ steps.setup.outputs.workspace }}/admin-board:latest

      - name: Deploy to Kubernetes
        run: |
          echo "🚀 Deploying admin-board to ${{ steps.infra.outputs.namespace }}"

          # Update deployment with new image
          kubectl set image deployment/admin-board \
            admin-board=${{ steps.infra.outputs.registry_url }}/aicallgo-${{ steps.setup.outputs.workspace }}/admin-board:${{ steps.setup.outputs.image_tag }} \
            -n ${{ steps.infra.outputs.namespace }}

          # Wait for rollout to complete
          echo "⏳ Waiting for admin-board rollout..."
          kubectl rollout status deployment/admin-board \
            -n ${{ steps.infra.outputs.namespace }} \
            --timeout=300s

      - name: Verify deployment health
        run: |
          echo "🏥 Checking deployment health..."

          # Get pod status
          echo "📊 Admin Board pods:"
          kubectl get pods -n ${{ steps.infra.outputs.namespace }} \
            -l app=admin-board \
            -o wide

          # Check health
          echo "🔍 Checking health..."
          HEALTHY=false
          for i in {1..30}; do
            POD_NAME=$(kubectl get pods -n ${{ steps.infra.outputs.namespace }} \
              -l app=admin-board \
              -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)

            if [[ -n "$POD_NAME" ]]; then
              POD_STATUS=$(kubectl get pod $POD_NAME -n ${{ steps.infra.outputs.namespace }} \
                -o jsonpath='{.status.phase}')

              if [[ "$POD_STATUS" == "Running" ]]; then
                echo "✅ Pod $POD_NAME is running"

                # Check if health endpoint is accessible
                if kubectl exec $POD_NAME -n ${{ steps.infra.outputs.namespace }} -- \
                   curl -s -f http://localhost:8501/_stcore/health > /dev/null 2>&1; then
                  echo "✅ Health check passed"
                  HEALTHY=true
                  break
                else
                  echo "⚠️  Health check pending..."
                fi
              fi
            fi

            echo "Waiting for deployment to be ready... ($i/30)"
            sleep 10
          done

          # Final health check
          if [[ "$HEALTHY" == "true" ]]; then
            echo "✅ Deployment is healthy"
            exit 0
          else
            echo "❌ Deployment health check failed"
            echo "📋 Pod logs:"
            kubectl logs -n ${{ steps.infra.outputs.namespace }} \
              -l app=admin-board \
              --tail=50
            exit 1
          fi

      - name: Report deployment status
        if: always()
        run: |
          if [[ "${{ job.status }}" == "success" ]]; then
            echo "🎉 Successfully deployed admin-board to ${{ steps.setup.outputs.workspace }}"
            echo "📦 Image: ${{ steps.infra.outputs.registry_url }}/aicallgo-${{ steps.setup.outputs.workspace }}/admin-board:${{ steps.setup.outputs.image_tag }}"

            # Determine admin URL based on environment and domain
            if [[ "${{ steps.setup.outputs.workspace }}" == "staging" ]]; then
              ADMIN_URL="https://staging-admin.julya.ai"
            else
              ADMIN_URL="https://admin.${{ steps.infra.outputs.domain }}"
            fi
            echo "🌐 Admin URL: $ADMIN_URL"
          else
            echo "❌ Deployment failed for admin-board"
          fi
```

### Step 2: Commit and Push Workflow

```bash
cd /Users/blickt/Documents/src/aicallgo-infra-repo/services/admin-board
git add .github/workflows/deploy.yml
git commit -m "feat: add GitHub Actions deployment workflow for admin-board"
git push origin staging
```

---

## GitHub Secrets Configuration

### Step 1: Update CICD Script to Include Admin Board

**File**: `terraform/scripts/cicd/setup-github-env-secrets.sh`

Update the `REPOSITORIES` array (line 23-29) to include admin-board:

```bash
declare -a REPOSITORIES=(
    "aicallgo-backend-cursor"
    "aicallgo-aiagent"
    "aicallgo-frontend-v0"
    "aicallgo-crawl4ai"
    "aicallgo-chatwoot"
    "aicallgo-admin"
)
```

### Step 2: Extract Terraform Outputs

```bash
cd /Users/blickt/Documents/src/aicallgo-infra-repo/terraform/scripts/cicd

# Extract staging outputs
./extract-terraform-outputs.sh -d ../../terraform -w staging
```

Expected output files in `./outputs/`:
- `staging-kubeconfig.txt`
- `staging-registry-url.txt`
- `staging-registry-username.txt`
- `staging-registry-password.txt`
- `staging-cluster-id.txt`
- `staging-namespace.txt`
- `staging-domain.txt`

### Step 3: Configure GitHub Secrets for Admin Board Repository

```bash
# Configure secrets for admin-board repository
./setup-github-env-secrets.sh -w staging -r aicallgo-admin
```

This will create a `staging` environment in the `aicallgo-admin` repository with the following secrets:
- `DIGITALOCEAN_ACCESS_TOKEN`
- `SPACES_ACCESS_KEY_ID`
- `SPACES_SECRET_KEY`
- `INFRA_REPO_TOKEN`

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions.

### Step 4: Verify Secrets in GitHub

1. Go to https://github.com/blicktz/aicallgo-admin/settings/environments
2. Verify `staging` environment exists
3. Verify all secrets are configured

### Step 5: Repeat for Production (When Ready)

```bash
# Extract production outputs
./extract-terraform-outputs.sh -d ../../terraform -w prod

# Configure production secrets
./setup-github-env-secrets.sh -w prod -r aicallgo-admin --protect
```

---

## Deployment Process

### Step 1: Generate Admin Password Hash

Before deploying, generate a bcrypt hash for the admin password:

```bash
# Using Python
python3 -c "import bcrypt; password = input('Enter admin password: ').encode(); print(bcrypt.hashpw(password, bcrypt.gensalt()).decode())"
```

Example output:
```
$2b$12$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJ
```

### Step 2: Update Terraform Variables

**File**: `terraform/staging-public.tfvars`

```hcl
# Add the generated hash
admin_password_hash = "$2b$12$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJ"
```

**Important**: Also update `prod-public.tfvars` with a different password for production.

### Step 3: Apply Terraform Changes (Staging)

```bash
cd /Users/blickt/Documents/src/aicallgo-infra-repo/terraform

# Source Digital Ocean credentials
source .envrc

# Initialize and plan
make staging-init
make staging-plan

# Review the plan - should show:
# - kubernetes_deployment.admin_board (new)
# - kubernetes_service.admin_board (new)
# - kubernetes_secret.admin_board_secrets (new)
# - kubernetes_ingress_v1.aicallgo (modified - new rule)

# Apply changes
make staging-apply
```

### Step 4: Trigger Initial CI/CD Build

Since the deployment exists but no image is available yet, manually trigger the first build:

```bash
# Option 1: Push to staging branch
cd /Users/blickt/Documents/src/aicallgo-infra-repo/services/admin-board
git push origin staging

# Option 2: Use workflow_dispatch
# Go to: https://github.com/blicktz/aicallgo-admin/actions
# Click "Deploy Admin Board" → "Run workflow" → Select "staging"
```

### Step 5: Monitor Deployment

```bash
# Watch the GitHub Actions workflow
# https://github.com/blicktz/aicallgo-admin/actions

# Or monitor from command line
export KUBECONFIG=~/staging-kubeconfig.txt

# Watch pod creation
kubectl get pods -n aicallgo-staging -l app=admin-board -w

# Check deployment status
kubectl rollout status deployment/admin-board -n aicallgo-staging

# View logs
kubectl logs -f deployment/admin-board -n aicallgo-staging
```

---

## DNS and SSL Configuration

### Automatic Configuration

The ingress controller and cert-manager will automatically:
1. Request SSL certificate from Let's Encrypt for the admin subdomain
2. Configure DNS via Cloudflare (if using Cloudflare DNS-01 challenge)
3. Route traffic to the admin-board service

### DNS Records (Manual Setup if Needed)

If DNS is not managed by Terraform, create the following A records in your DNS provider:

**Staging**:
- `staging-admin.julya.ai` → Load balancer IP

**Production**:
- `admin.julya.ai` → Load balancer IP

Get the load balancer IP:
```bash
kubectl get ingress aicallgo-ingress -n aicallgo-staging -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### Verify SSL Certificate

```bash
# Check certificate status
kubectl get certificate -n aicallgo-staging

# Check certificate details
kubectl describe certificate aicallgo-tls-staging -n aicallgo-staging

# Verify HTTPS access
curl -I https://admin-staging.julya.ai
```

Expected output:
```
HTTP/2 200
server: nginx
```

---

## Validation and Testing

### Step 1: Access Check

```bash
# Staging
open https://staging-admin.julya.ai

# Production (when deployed)
open https://admin.julya.ai
```

### Step 2: Authentication Test

1. Navigate to admin URL
2. Enter admin password
3. Verify successful login
4. Check that session persists across page refreshes

### Step 3: Database Connection Test

1. Navigate to Dashboard page
2. Verify metrics are loading (user count, call count, etc.)
3. Navigate to Users page
4. Search for a user
5. Verify user data is displayed correctly

### Step 4: Feature Test

Test each major feature:
- [ ] Dashboard metrics display
- [ ] User search and detail view
- [ ] Business listing and detail view
- [ ] Call logs with filters
- [ ] Billing information (read-only)
- [ ] Entitlements management (if implemented)
- [ ] Credits adjustment (if implemented)

### Step 5: Performance Test

```bash
# Check pod resource usage
kubectl top pod -n aicallgo-staging -l app=admin-board

# Expected:
# NAME                           CPU(cores)   MEMORY(bytes)
# admin-board-xxxxxxxxxx-xxxxx   50m          256Mi
```

### Step 6: Health Check Verification

```bash
# Check health endpoint
kubectl exec -it deployment/admin-board -n aicallgo-staging -- curl http://localhost:8501/_stcore/health

# Expected output: OK
```

---

## Rollback Procedure

### Scenario 1: Deployment Fails During CI/CD

The workflow includes automatic rollback via Kubernetes:

```bash
# Check rollout status
kubectl rollout status deployment/admin-board -n aicallgo-staging

# If unhealthy, Kubernetes will automatically keep previous pods running
# Manual rollback to previous version:
kubectl rollout undo deployment/admin-board -n aicallgo-staging
```

### Scenario 2: Bad Configuration Change

If Terraform changes cause issues:

```bash
cd /Users/blickt/Documents/src/aicallgo-infra-repo/terraform

# Revert the tfvars or .tf files
git revert <commit-hash>

# Re-apply
make staging-apply
```

### Scenario 3: Complete Removal

To completely remove the admin-board deployment:

```bash
# Comment out or remove admin-board resources in Terraform files
# Then apply:
make staging-apply

# Or delete directly via kubectl:
kubectl delete deployment admin-board -n aicallgo-staging
kubectl delete service admin-board -n aicallgo-staging
kubectl delete secret admin-board-secrets -n aicallgo-staging
```

---

## Post-Deployment Tasks

### Step 1: Update Documentation

- [ ] Update main README with admin board access instructions
- [ ] Document admin credentials management process
- [ ] Create user guide for admin operations

### Step 2: Set Up Monitoring

```bash
# Add Grafana dashboard for admin-board
# Monitor metrics:
# - Pod CPU/Memory usage
# - Request count
# - Error rate
# - Response time
```

### Step 3: Configure Alerts

Create alerts for:
- Admin board pod crashes
- High memory usage (>80%)
- Failed authentication attempts
- Database connection failures

### Step 4: IP Whitelisting (Optional)

If additional security is needed, configure IP whitelisting in ingress:

**File**: `terraform/modules/k8s_config/ingress.tf`

Add annotation to admin-board ingress rule:

```hcl
annotations = {
  "nginx.ingress.kubernetes.io/whitelist-source-range" = "1.2.3.4/32,5.6.7.8/32"
}
```

### Step 5: Backup and Disaster Recovery

- [ ] Verify database backups include admin-accessible data
- [ ] Document admin password recovery process
- [ ] Test disaster recovery for admin-board deployment

### Step 6: Production Deployment (Phase 10)

When ready to deploy to production:

1. Update `prod-public.tfvars` with production admin password hash
2. Run through this entire plan with `workspace=prod`
3. Test thoroughly in production
4. Document any production-specific configurations

---

## Troubleshooting

### Issue: Pod CrashLoopBackOff

```bash
# Check pod logs
kubectl logs -f deployment/admin-board -n aicallgo-staging

# Common causes:
# - DATABASE_URL incorrect
# - Admin password hash malformed
# - Web-backend models import failing
```

**Solution**:
```bash
# Verify secret
kubectl get secret admin-board-secrets -n aicallgo-staging -o yaml

# Update secret if needed
kubectl delete secret admin-board-secrets -n aicallgo-staging
# Re-apply Terraform
make staging-apply
```

### Issue: 502 Bad Gateway

```bash
# Check service endpoints
kubectl get endpoints admin-board -n aicallgo-staging

# Check ingress
kubectl describe ingress aicallgo-ingress -n aicallgo-staging
```

**Solution**:
- Verify service selector matches deployment labels
- Check pod is in Running state
- Verify health check endpoint is responding

### Issue: Database Connection Refused

```bash
# Test database connectivity from pod
kubectl exec -it deployment/admin-board -n aicallgo-staging -- /bin/bash
# Inside pod:
curl -v telnet://postgres-private:5432
```

**Solution**:
- Verify `DATABASE_URL` uses `postgres-private` host
- Check database firewall rules allow cluster access
- Verify database credentials are correct

### Issue: Authentication Not Working

```bash
# Check admin password hash in secret
kubectl get secret admin-board-secrets -n aicallgo-staging -o jsonpath='{.data.ADMIN_PASSWORD_HASH}' | base64 -d

# Regenerate hash if needed
python3 -c "import bcrypt; print(bcrypt.hashpw(b'your_password', bcrypt.gensalt()).decode())"
```

### Issue: CI/CD Build Failing

Common causes:
- `GITHUB_TOKEN` doesn't have access to private web-backend repo
- Registry credentials expired
- Terraform state locked

**Solution**:
```bash
# Verify secrets in GitHub
gh secret list -R blicktz/aicallgo-admin

# Check Terraform lock
cd terraform
terraform force-unlock <lock-id>
```

---

## Summary Checklist

### Pre-Deployment
- [ ] Terraform variables added for admin-board
- [ ] Admin password hash generated
- [ ] Terraform tfvars updated
- [ ] GitHub workflow created
- [ ] GitHub secrets configured

### Deployment
- [ ] Terraform applied successfully
- [ ] Initial CI/CD build triggered
- [ ] Deployment rolled out successfully
- [ ] Pods are in Running state
- [ ] Health checks passing

### Post-Deployment
- [ ] HTTPS access working
- [ ] SSL certificate valid
- [ ] Authentication working
- [ ] Database connection working
- [ ] All features tested
- [ ] Monitoring configured
- [ ] Documentation updated

### Production (Phase 10)
- [ ] Production tfvars configured
- [ ] Production secrets set
- [ ] Production deployment tested
- [ ] Production URL accessible
- [ ] Production monitoring enabled

---

## References

- **Web Backend Deploy Workflow**: `/Users/blickt/Documents/src/aicallgo-infra-repo/services/web-backend/.github/workflows/deploy.yml`
- **Terraform K8s Config**: `/Users/blickt/Documents/src/aicallgo-infra-repo/terraform/modules/k8s_config/`
- **CICD Scripts**: `/Users/blickt/Documents/src/aicallgo-infra-repo/terraform/scripts/cicd/`
- **Admin Board Dockerfile**: `/Users/blickt/Documents/src/aicallgo-infra-repo/services/admin-board/Dockerfile`
- **Implementation Plan**: `/Users/blickt/Documents/src/aicallgo-infra-repo/services/admin-board/docs/IMPLEMENTATION_PLAN.md`

---

**Last Updated**: 2025-10-22
**Version**: 1.0
**Status**: Ready for Implementation
