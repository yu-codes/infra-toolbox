# Docker Rules

## Dockerfile Best Practices

- Use specific base image tags (e.g., `python:3.12-slim`, not `python:latest`)
- Multi-stage builds for smaller production images
- Run as non-root user in production
- Place frequently changing layers last for cache efficiency
- Use `.dockerignore` to exclude unnecessary files

## Python Dockerfile Template

```dockerfile
# Stage 1: Builder
FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: Runtime
FROM python:3.12-slim
WORKDIR /app
RUN useradd -m appuser
COPY --from=builder /install /usr/local
COPY . .
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker Compose Conventions

- Use named volumes for persistent data
- Define explicit networks for service isolation
- Use environment files (`.env`) for configuration
- Always set `restart: unless-stopped` for production services
- Pin image versions in compose files
- Use health checks for dependency ordering

## Security

- Never store secrets in images or Dockerfiles
- Use Docker secrets or environment variables at runtime
- Scan images regularly for vulnerabilities
- Limit container capabilities (no `--privileged` unless required)
- Use read-only root filesystem when possible
