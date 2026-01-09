# Task ID: 6

**Title:** Integrate End-to-End Authentication Flow and Route Protection

**Status:** done

**Dependencies:** 4 ✓, 5 ✓

**Priority:** high

**Description:** Wire up complete authentication flow from frontend to backend with route protection and token management

**Details:**

Modify frontend/src/App.tsx to wrap application in AuthProvider and implement route protection redirecting unauthenticated users to /landing. Configure public routes (/landing, /login, /signup, /auth/callback) and protected routes (/dashboard, /inventory). Update frontend/src/lib/api/client.ts to include Authorization: Bearer <token> header in all API requests and handle 401 responses by redirecting to login. Implement automatic token refresh before expiry. Add middleware to set tenant context in backend for each authenticated request. Test complete flow: landing → signup/login → Authentik → callback → dashboard → API calls → logout → landing.

**Test Strategy:**

Test complete user journey from landing page through authentication to dashboard access, verify protected routes redirect unauthenticated users to landing, confirm authenticated API calls include proper headers and return tenant-scoped data, test token refresh maintains session without user intervention, validate logout clears all authentication state and redirects appropriately, test multi-tenant scenarios with users belonging to multiple tenants
