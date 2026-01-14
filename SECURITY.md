# Security Policy

## Reporting a Vulnerability

The Batchivo team takes security seriously. We appreciate your efforts to responsibly disclose any security vulnerabilities you find.

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report security vulnerabilities by emailing:

**security@batchivo.com**

Include the following information in your report:
- Type of vulnerability (e.g., SQL injection, XSS, authentication bypass)
- Location of the affected code (file path, line number if known)
- Step-by-step instructions to reproduce the issue
- Proof of concept or exploit code (if available)
- Potential impact of the vulnerability
- Any suggested remediation

### What to Expect

| Timeline | Action |
|----------|--------|
| 24-48 hours | Acknowledgment of your report |
| 7 days | Initial assessment and severity determination |
| 30 days | Target for resolution of critical/high severity issues |
| 90 days | Target for resolution of medium/low severity issues |

We will keep you informed of our progress throughout the process.

### Disclosure Policy

- We request that you give us reasonable time to address the vulnerability before public disclosure
- We will coordinate with you on the disclosure timeline
- We will credit you in our security advisories (unless you prefer to remain anonymous)

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.x.x (current development) | Yes |

As Batchivo is currently in active development (pre-1.0), we support the latest version only. Once we reach 1.0, we will establish a formal LTS (Long Term Support) policy.

---

## Security Features

Batchivo implements the following security measures:

### Authentication & Authorization

- **JWT-based authentication** with secure refresh token rotation
- **bcrypt password hashing** with appropriate work factors
- **Row-Level Security (RLS)** in PostgreSQL for multi-tenant data isolation
- **Tenant-scoped queries** enforced at the application layer

### Data Protection

- **Input validation** via Pydantic schemas on all API endpoints
- **SQL injection protection** via SQLAlchemy ORM (parameterized queries)
- **XSS protection** via React's default escaping
- **CORS configuration** limiting cross-origin requests
- **Rate limiting** on authentication endpoints

### Infrastructure

- **TLS encryption** via Cloudflare (all traffic)
- **Non-root containers** in production
- **Secrets management** via Kubernetes Secrets
- **Minimal base images** (Alpine Linux)

### Observability

- **Request tracing** via OpenTelemetry
- **Centralized logging** via Loki
- **Metrics collection** via Prometheus

---

## Security Best Practices for Contributors

When contributing to Batchivo, please follow these security guidelines:

### Code

1. **Never commit secrets** - Use environment variables or Kubernetes Secrets
2. **Validate all input** - Use Pydantic schemas for request validation
3. **Use parameterized queries** - Always use SQLAlchemy ORM, never raw SQL
4. **Check tenant scope** - Every query must include tenant isolation
5. **Handle errors safely** - Never expose stack traces or internal errors to users

### Dependencies

1. Keep dependencies up to date
2. Review security advisories for dependencies
3. Use `poetry audit` and `npm audit` regularly
4. Avoid dependencies with known vulnerabilities

### Authentication

1. Never log passwords or tokens
2. Use constant-time comparison for secrets
3. Implement proper session invalidation
4. Follow OAuth 2.0 / OpenID Connect best practices

---

## Security Advisories

Security advisories will be published through:

1. GitHub Security Advisories
2. Project CHANGELOG
3. Direct notification to affected users (for critical issues)

---

## Bug Bounty

We do not currently operate a formal bug bounty program. However, we deeply appreciate security researchers who report vulnerabilities responsibly.

Significant security contributions may be acknowledged in:
- Security advisories
- Project documentation
- Release notes

---

## Contact

For security-related inquiries:
- **Email**: security@batchivo.com
- **Response Time**: Within 48 hours

For general questions, please use GitHub Discussions.

---

*Last Updated: January 2026*
