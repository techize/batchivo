# Authentication

The Batchivo API uses JWT (JSON Web Tokens) for authentication. This document covers the complete authentication flow.

## Authentication Flow

1. **Register** or **Login** to obtain access and refresh tokens
2. Include the access token in the `Authorization` header for API requests
3. When the access token expires, use the refresh token to obtain a new one
4. Handle token refresh automatically in your client

## Endpoints

### Register

Create a new user account and workspace.

```
POST /api/v1/auth/register
```

**Rate Limit:** 5 requests/minute

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "full_name": "John Doe",
  "tenant_name": "My 3D Print Shop"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| email | string | Yes | Valid email address |
| password | string | Yes | Min 8 characters |
| full_name | string | Yes | User's full name |
| tenant_name | string | No | Workspace name (defaults to email-based name) |

**Response: 201 Created**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Email already registered |
| 422 | Validation error |
| 429 | Rate limit exceeded |

---

### Login

Authenticate with email and password to obtain tokens.

```
POST /api/v1/auth/login
```

**Rate Limit:** 5 requests/minute

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response: 200 OK**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 401 | Incorrect email or password |
| 403 | User account is inactive |
| 429 | Rate limit exceeded |

---

### Refresh Token

Exchange a valid refresh token for a new access token.

```
POST /api/v1/auth/refresh
```

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response: 200 OK**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 401 | Invalid refresh token |
| 401 | User not found or inactive |

---

### Logout

Logout the current user. For JWT-based auth, this is primarily handled client-side by discarding tokens.

```
POST /api/v1/auth/logout
```

**Response: 200 OK**

```json
{
  "message": "Logged out successfully. Please discard your tokens client-side."
}
```

---

### Forgot Password

Request a password reset token. For security, always returns success even if email doesn't exist.

```
POST /api/v1/auth/forgot-password
```

**Rate Limit:** 3 requests/minute

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response: 200 OK**

```json
{
  "message": "If that email address exists in our system, we've sent a password reset link to it."
}
```

---

### Reset Password

Reset password using a valid reset token.

```
POST /api/v1/auth/reset-password
```

**Rate Limit:** 5 requests/minute

**Request Body:**

```json
{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePassword123!"
}
```

**Response: 200 OK**

```json
{
  "message": "Password reset successfully. You can now log in with your new password."
}
```

**Errors:**

| Status | Description |
|--------|-------------|
| 400 | Invalid or expired reset token |

---

## Using Tokens

### Authorization Header

Include the access token in all authenticated requests:

```bash
curl -X GET "https://api.batchivo.app/api/v1/spools" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### Token Structure

JWT tokens contain the following claims:

```json
{
  "user_id": "uuid",
  "email": "user@example.com",
  "tenant_id": "uuid",
  "type": "access",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### Token Expiration

| Token Type | Expiration |
|------------|------------|
| Access Token | 24 hours |
| Refresh Token | 7 days |

## Code Examples

### Python (httpx)

```python
import httpx

class BatchivoClient:
    def __init__(self, base_url: str = "https://api.batchivo.app/api/v1"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None

    async def login(self, email: str, password: str):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/login",
                json={"email": email, "password": password}
            )
            response.raise_for_status()
            tokens = response.json()
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]

    async def refresh_tokens(self):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/refresh",
                json={"refresh_token": self.refresh_token}
            )
            response.raise_for_status()
            tokens = response.json()
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]

    def get_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}
```

### JavaScript (fetch)

```javascript
class BatchivoClient {
  constructor(baseUrl = "https://api.batchivo.app/api/v1") {
    this.baseUrl = baseUrl;
    this.accessToken = null;
    this.refreshToken = null;
  }

  async login(email, password) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    if (!response.ok) throw new Error("Login failed");

    const tokens = await response.json();
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
  }

  async refreshTokens() {
    const response = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: this.refreshToken })
    });

    if (!response.ok) throw new Error("Token refresh failed");

    const tokens = await response.json();
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
  }

  getHeaders() {
    return { Authorization: `Bearer ${this.accessToken}` };
  }
}
```

### cURL

```bash
# Login
TOKEN_RESPONSE=$(curl -s -X POST "https://api.batchivo.app/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}')

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')
REFRESH_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.refresh_token')

# Use access token
curl -X GET "https://api.batchivo.app/api/v1/spools" \
  -H "Authorization: Bearer $ACCESS_TOKEN"

# Refresh token
curl -X POST "https://api.batchivo.app/api/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d "{\"refresh_token\": \"$REFRESH_TOKEN\"}"
```

## Security Best Practices

1. **Store tokens securely** - Use secure storage (Keychain, encrypted storage) on mobile. Avoid localStorage for sensitive tokens.

2. **Implement token refresh** - Automatically refresh tokens before expiration to avoid interrupting user sessions.

3. **Handle 401 errors** - Implement automatic retry with token refresh when receiving 401 responses.

4. **Logout properly** - Discard both tokens on logout. Consider implementing a token blacklist for enhanced security.

5. **Use HTTPS** - Always use HTTPS in production to protect tokens in transit.
