---
name: security-review
description: Comprehensive security checklist for web applications. Use before releases, after auth changes, or when handling sensitive data.
---

# Security Review Checklist

## Quick Scan Commands

```bash
# Python dependencies
pip-audit
bandit -r app/ -ll

# Node dependencies
npm audit --audit-level=high

# Secrets in code
grep -rn "sk-\|ghp_\|AKIA\|password\s*=\s*[\"']" --include="*.py" --include="*.ts" --include="*.env*" .

# Docker security
docker scout cves <image-name>
```

## OWASP Top 10 for FastAPI + Vue

### 1. Injection
- [ ] All SQL uses ORM or parameterized queries
- [ ] No `f"SELECT..."` patterns
- [ ] No `os.system()` or `subprocess.run(shell=True)` with user input
- [ ] GraphQL queries use parameterized variables

### 2. Broken Authentication
- [ ] Passwords hashed with bcrypt/argon2 (never MD5/SHA1)
- [ ] JWT tokens validated (signature, expiry, issuer)
- [ ] Rate limiting on login endpoints
- [ ] Session tokens rotated after login

### 3. Sensitive Data Exposure
- [ ] No secrets in source code or Docker images
- [ ] HTTPS enforced in production
- [ ] PII encrypted at rest
- [ ] Secrets via environment variables only
- [ ] No sensitive data in logs

### 4. Broken Access Control
- [ ] Auth checked on EVERY endpoint (use `Depends(get_current_user)`)
- [ ] Resource ownership verified (user can only access their data)
- [ ] CORS configured for specific origins only
- [ ] Admin routes have role checks

### 5. Security Misconfiguration
- [ ] Debug mode OFF in production
- [ ] Default credentials changed
- [ ] Security headers set (X-Content-Type-Options, X-Frame-Options, CSP)
- [ ] Error messages don't leak internal details
- [ ] Docker containers run as non-root

### 6. XSS (Vue-specific)
- [ ] No `v-html` with user-provided content
- [ ] CSP headers configured
- [ ] Input sanitized before rendering

### 7. Dependencies
- [ ] `pip-audit` / `npm audit` clean
- [ ] No packages with known CVEs
- [ ] Lock files committed (requirements.txt / pnpm-lock.yaml)

## FastAPI Security Patterns

```python
# Rate limiting
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/auth/login")
@limiter.limit("5/minute")
async def login(request: Request, credentials: LoginSchema):
    ...

# Input validation (Pydantic does this automatically)
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

# Auth dependency
async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    user = await get_user(payload["sub"])
    if not user:
        raise HTTPException(401)
    return user
```

## Docker Security

- [ ] Multi-stage build (no build tools in production)
- [ ] Non-root user: `USER nonroot`
- [ ] No secrets in Dockerfile
- [ ] Minimal base image (slim/alpine)
- [ ] Read-only filesystem where possible
- [ ] Resource limits set in docker-compose

## Severity Levels

| Level | Examples | Action |
|-------|----------|--------|
| CRITICAL | Hardcoded secrets, SQL injection, no auth | Fix immediately |
| HIGH | Missing rate limiting, no CORS, root Docker | Fix before merge |
| MEDIUM | Missing security headers, verbose errors | Fix soon |
| LOW | Outdated non-vulnerable deps | Track |
