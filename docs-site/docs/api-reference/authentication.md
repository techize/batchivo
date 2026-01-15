---
sidebar_position: 2
---

# Authentication

Batchivo uses JWT (JSON Web Tokens) for API authentication.

## Login

Obtain access and refresh tokens:

```bash
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## Using Tokens

Include the access token in the Authorization header:

```bash
curl -X GET 'http://localhost:8000/api/v1/spools' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

## Token Refresh

Access tokens expire after 30 minutes. Use the refresh token to get new tokens:

```bash
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

## Token Lifetimes

| Token | Default Lifetime | Configurable |
|-------|------------------|--------------|
| Access Token | 30 minutes | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | 7 days | `REFRESH_TOKEN_EXPIRE_DAYS` |

## Logout

Invalidate refresh token:

```bash
POST /api/v1/auth/logout
Authorization: Bearer eyJ...
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

## Current User

Get authenticated user details:

```bash
GET /api/v1/auth/me
Authorization: Bearer eyJ...
```

**Response:**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "name": "John Doe",
  "created_at": "2024-01-01T00:00:00Z",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

## Multi-Tenant Access

Batchivo is multi-tenant. Each user belongs to a tenant, and all data is isolated by tenant using Row-Level Security (RLS).

The tenant is automatically determined from the authenticated user's token.

## Error Responses

### Invalid Credentials

```json
{
  "detail": "Incorrect email or password",
  "code": "INVALID_CREDENTIALS"
}
```

### Token Expired

```json
{
  "detail": "Token has expired",
  "code": "TOKEN_EXPIRED"
}
```

### Invalid Token

```json
{
  "detail": "Could not validate credentials",
  "code": "INVALID_TOKEN"
}
```

## Security Best Practices

1. **Never share tokens** - Treat like passwords
2. **Use HTTPS** - Always in production
3. **Store securely** - Use secure storage for tokens
4. **Refresh proactively** - Refresh before expiration
5. **Logout on compromise** - Invalidate tokens if leaked

## API Keys (Coming Soon)

For server-to-server integration, API keys will be supported:

```bash
X-API-Key: batchivo_live_xxx...
```
