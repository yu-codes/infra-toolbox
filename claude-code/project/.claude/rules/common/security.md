# Security Guidelines

## Mandatory Security Checks

Before ANY commit:
- [ ] No hardcoded secrets (API keys, passwords, tokens)
- [ ] All user inputs validated and sanitized
- [ ] SQL injection prevention (parameterized queries / ORM)
- [ ] XSS prevention (sanitized output)
- [ ] CSRF protection enabled
- [ ] Authentication/authorization verified
- [ ] Rate limiting on public endpoints
- [ ] Error messages don't leak sensitive data

## Secret Management

- NEVER hardcode secrets in source code
- ALWAYS use environment variables or a secret manager
- Add `.env` files to `.gitignore`
- Validate that required secrets are present at startup
- Rotate any secrets that may have been exposed

## Docker Security

- Use official base images with specific tags (not `latest`)
- Run containers as non-root user
- Don't store secrets in Docker images or layers
- Use multi-stage builds to minimize attack surface
- Scan images for vulnerabilities

## API Security

- Always use HTTPS in production
- Validate and sanitize all request body/params
- Implement proper CORS configuration
- Use JWT with appropriate expiration times
- Log authentication failures for monitoring
