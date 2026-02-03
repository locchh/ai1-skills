---
name: docker-best-practices
description: >-
  Docker containerization patterns for Python/React projects. Use when creating or
  modifying Dockerfiles, optimizing image size, setting up Docker Compose for local
  development, or hardening container security. Covers multi-stage builds for Python
  (python:3.12-slim) and React (node:20-alpine -> nginx:alpine), layer optimization,
  .dockerignore, non-root user, security scanning with Trivy, Docker Compose for
  dev (backend + frontend + PostgreSQL + Redis), and image tagging strategy.
  Does NOT cover deployment orchestration (use deployment-pipeline).
license: MIT
compatibility: 'Docker 24+, Docker Compose v2'
metadata:
  author: platform-team
  version: '1.0.0'
  sdlc-phase: deployment
allowed-tools: Read Edit Write Bash(docker:*)
context: fork
---

# Docker Best Practices

## When to Use

Use this skill when you need to:

- **Create or modify Dockerfiles** for Python backend or React frontend applications
- **Optimize Docker image size** by reducing layers, choosing smaller base images, or restructuring builds
- **Set up Docker Compose** for local development with multiple services (backend, frontend, database, cache)
- **Harden container security** by running as non-root, scanning for vulnerabilities, or restricting filesystem access

Do **NOT** use this skill for:

- Deployment orchestration, CI/CD pipelines, or production rollout strategies -- use `deployment-pipeline` instead
- Monitoring or observability setup inside containers -- use `monitoring-setup` instead

## Instructions

### Multi-Stage Builds

Multi-stage builds are mandatory for all production images. They separate build-time dependencies from the runtime image, dramatically reducing image size and attack surface.

#### Python Backend (FastAPI)

Use a two-stage build: a builder stage for installing dependencies and a runtime stage with only the application code and compiled packages.

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies for compiled packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install only runtime system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY ./src ./src
COPY alembic.ini .
COPY alembic/ ./alembic/

# Switch to non-root user
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Key points:
- The builder stage installs all dependencies including build tools (gcc, libpq-dev)
- `pip install --prefix=/install` isolates installed packages for clean copy
- The runtime stage only includes runtime libraries (libpq5, not libpq-dev)
- The runtime image does not contain pip, gcc, or any build tooling

#### React Frontend

Use a three-stage conceptual flow: install dependencies, build the production bundle, then serve with nginx.

```dockerfile
# Stage 1: Builder
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files first for better caching
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

# Copy source and build
COPY . .
RUN npm run build

# Stage 2: Runtime
FROM nginx:alpine AS runtime

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Create non-root user for nginx
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

Key points:
- `npm ci` ensures reproducible installs from the lockfile
- The final image is nginx:alpine, which is only ~25MB
- No Node.js runtime, node_modules, or source code in the production image

### Base Image Selection

Choose base images deliberately. Every base image decision affects size, security, and compatibility.

**Recommended Base Images:**

| Purpose | Image | Size | Notes |
|---------|-------|------|-------|
| Python backend | `python:3.12-slim` | ~150MB | Debian-based, includes essential C libraries |
| Node.js build | `node:20-alpine` | ~130MB | Alpine-based, smallest Node image |
| Static serving | `nginx:alpine` | ~25MB | Minimal nginx for serving built assets |
| PostgreSQL | `postgres:16-alpine` | ~80MB | For local development and CI |
| Redis | `redis:7-alpine` | ~30MB | For local development and CI |

**Rules:**
- ALWAYS pin the major and minor version: `python:3.12-slim`, not `python:slim` or `python:latest`
- Prefer `-slim` variants over full images for Python (eliminates ~400MB of build tools)
- Prefer `-alpine` variants for Node.js and infrastructure services
- Never use `latest` tag in any Dockerfile or Compose file
- Document the reason when choosing a non-default base image

### Layer Optimization

Docker builds each instruction as a layer. Optimize layers to maximize cache hits and minimize image size.

**Rule 1: Copy dependency files before source code.**

```dockerfile
# GOOD: Dependencies cached separately from source
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./src ./src

# BAD: Any source change invalidates the pip install cache
COPY . .
RUN pip install -r requirements.txt
```

**Rule 2: Combine RUN commands to reduce layers.**

```dockerfile
# GOOD: Single layer for related operations
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# BAD: Three layers, and the apt cache persists in layer 1
RUN apt-get update
RUN apt-get install -y curl
RUN rm -rf /var/lib/apt/lists/*
```

**Rule 3: Clean up in the same layer.**

```dockerfile
# GOOD: Build artifacts cleaned in same layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc && \
    pip install --no-cache-dir -r requirements.txt && \
    apt-get purge -y gcc && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

# BAD: gcc persists in an earlier layer even after removal
RUN apt-get update && apt-get install -y gcc
RUN pip install -r requirements.txt
RUN apt-get purge -y gcc
```

**Rule 4: Order instructions from least to most frequently changed.**

```dockerfile
# System packages change rarely -> dependency install -> source code changes often
RUN apt-get update && apt-get install -y --no-install-recommends libpq5
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ./src ./src
```

### .dockerignore

Always include a `.dockerignore` file in the project root. Without it, the Docker build context includes everything, slowing builds and potentially leaking secrets.

**Standard .dockerignore for Python/React projects:**

```
# Version control
.git
.gitignore

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.venv
venv
env
.mypy_cache
.pytest_cache
.ruff_cache
htmlcov
.coverage
*.egg-info

# Node.js
node_modules
.next
.nuxt

# Build outputs
dist
build

# IDE
.vscode
.idea
*.swp
*.swo

# Environment and secrets
.env
.env.*
*.pem
*.key

# Docker
Dockerfile
docker-compose*.yml
.dockerignore

# Documentation
*.md
docs/
LICENSE

# CI
.github
.gitlab-ci.yml
```

**Why each entry matters:**
- `.git` can be hundreds of megabytes and is never needed in the image
- `node_modules` is rebuilt inside the container via `npm ci`
- `.env` files contain secrets that must never be baked into images
- `__pycache__` and `.pyc` files are platform-specific and rebuilt at runtime

### Security

Container security is not optional. Every image must follow these practices.

**Non-Root User:**

Never run containers as root in production.

```dockerfile
# Create a dedicated user and group
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home --shell /sbin/nologin appuser

# Set ownership of application files
COPY --chown=appuser:appuser ./src ./src

# Switch to non-root before CMD
USER appuser
```

For Alpine-based images:

```dockerfile
RUN addgroup -g 1000 appuser && \
    adduser -u 1000 -G appuser -D -s /sbin/nologin appuser
USER appuser
```

**No Secrets in Images:**

Secrets must be injected at runtime via environment variables or mounted volumes, never baked into the image.

```dockerfile
# NEVER do this
ENV DATABASE_PASSWORD=supersecret
COPY .env /app/.env

# CORRECT: Pass at runtime
# docker run -e DATABASE_URL=postgresql://... myapp
# docker run --env-file .env.production myapp
```

**Security Scanning with Trivy:**

Scan every image before pushing to the registry.

```bash
# Scan for vulnerabilities
trivy image --severity HIGH,CRITICAL app-backend:1.2.3

# Scan with exit code for CI integration
trivy image --exit-code 1 --severity CRITICAL app-backend:1.2.3

# Scan the Dockerfile itself for misconfigurations
trivy config Dockerfile
```

**Read-Only Filesystem:**

Run containers with a read-only root filesystem where possible.

```yaml
# In docker-compose or orchestrator config
services:
  backend:
    image: app-backend:1.2.3
    read_only: true
    tmpfs:
      - /tmp
      - /var/run
```

**Additional Security Practices:**
- Drop all Linux capabilities and add back only what is needed
- Set `no-new-privileges` to prevent privilege escalation
- Use `COPY` instead of `ADD` (ADD can auto-extract archives and fetch URLs)
- Never install SSH servers or debugging tools in production images

### Docker Compose for Development

Use Docker Compose to run the full application stack locally.

```yaml
version: "3.9"

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - ./backend/src:/app/src:cached
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/app_dev
      - REDIS_URL=redis://redis:6379/0
      - LOG_LEVEL=DEBUG
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    ports:
      - "3000:3000"
    volumes:
      - ./frontend/src:/app/src:cached
      - ./frontend/public:/app/public:cached
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB: app_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 3s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

volumes:
  postgres_data:
```

**Key Patterns:**

- **Volume mounts for hot reload:** Mount source directories so code changes are reflected immediately without rebuilding. Use the `:cached` flag on macOS for better performance.
- **Health checks on all services:** Use `depends_on` with `condition: service_healthy` to ensure services start in the correct order.
- **Named volumes for data persistence:** PostgreSQL data persists across container restarts using a named volume.
- **Development Dockerfiles:** Use separate `Dockerfile.dev` files that include development dependencies and enable debug modes.

**Development Dockerfile for Python (Dockerfile.dev):**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-dev.txt

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### Image Tagging Strategy

Use a consistent, informative tagging strategy across all images.

**Tag Format:**

```
<app-name>:<semver>-<git-sha-short>
```

Examples:
- `app-backend:1.2.3-abc1234`
- `app-frontend:1.2.3-abc1234`

**Tagging Rules:**
- Every build produces a tag with the version and git SHA
- The git SHA enables tracing any running image back to the exact commit
- Never use `:latest` in production. It is ambiguous and defeats the purpose of versioning.
- Use `:latest` only for local development convenience
- Tag release candidates as `app-backend:1.2.3-rc.1`
- Tag hotfixes as `app-backend:1.2.4` (patch increment)

**Automated Tagging in CI:**

```bash
VERSION=$(cat VERSION)
GIT_SHA=$(git rev-parse --short HEAD)
IMAGE_TAG="${VERSION}-${GIT_SHA}"

docker build -t "app-backend:${IMAGE_TAG}" .
docker tag "app-backend:${IMAGE_TAG}" "app-backend:latest"
```

## Examples

### Optimized Dockerfile for FastAPI (1.2GB to 180MB)

This example shows the transformation from a naive Dockerfile to an optimized one.

**Before (1.2GB):**

```dockerfile
FROM python:3.12
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0"]
```

Problems: full Python image (900MB+), no .dockerignore, no multi-stage build, no non-root user, pip cache retained.

**After (180MB):**

```dockerfile
FROM python:3.12-slim AS builder
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid 1000 --no-create-home appuser
COPY --from=builder /install /usr/local
COPY --chown=appuser:appuser ./src ./src
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Savings breakdown:
- `python:3.12-slim` instead of `python:3.12`: saves ~600MB
- Multi-stage build (no gcc/build tools in runtime): saves ~200MB
- `--no-cache-dir` on pip: saves ~100MB
- Proper .dockerignore (no .git, node_modules): saves ~100MB of build context

## Edge Cases

### C Extensions Requiring Build Dependencies

Some Python packages (e.g., `psycopg2`, `numpy`, `Pillow`) require C compilers and system libraries at build time.

**Solution:** Install build dependencies only in the builder stage.

```dockerfile
FROM python:3.12-slim AS builder
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc g++ libpq-dev libjpeg-dev zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 libjpeg62 zlib1g && \
    rm -rf /var/lib/apt/lists/*
COPY --from=builder /install /usr/local
```

Note: the runtime stage installs the runtime shared libraries (libpq5) but not the development headers (libpq-dev).

### Private npm Registry

When the project uses packages from a private npm registry, authentication must be handled carefully.

**Solution:** Use build-time secrets (Docker BuildKit).

```dockerfile
# syntax=docker/dockerfile:1
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json .npmrc ./
RUN --mount=type=secret,id=npm_token \
    NPM_TOKEN=$(cat /run/secrets/npm_token) npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
```

Build command:

```bash
DOCKER_BUILDKIT=1 docker build --secret id=npm_token,src=$HOME/.npm_token .
```

The secret is never stored in any image layer.

### Hot Reload in Docker

File watching for hot reload can be unreliable with Docker volume mounts, especially on macOS.

**Solution for Python (uvicorn):**

```yaml
# docker-compose.yml
backend:
  volumes:
    - ./backend/src:/app/src:cached
  command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload --reload-dir /app/src
```

**Solution for React (Vite):**

```yaml
# docker-compose.yml
frontend:
  volumes:
    - ./frontend/src:/app/src:cached
  environment:
    - CHOKIDAR_USEPOLLING=true
    - WATCHPACK_POLLING=true
```

In `vite.config.ts`:

```typescript
export default defineConfig({
  server: {
    watch: {
      usePolling: true,
      interval: 1000,
    },
    host: '0.0.0.0',
    port: 3000,
  },
});
```

Using polling increases CPU usage but ensures reliable file change detection across all platforms when running inside Docker.
