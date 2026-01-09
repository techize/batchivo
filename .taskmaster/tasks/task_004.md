# Task ID: 4

**Title:** Create Landing Page and Authentication UI Components

**Status:** done

**Dependencies:** None

**Priority:** medium

**Description:** Build React landing page, login/signup flows, and authentication provider using TanStack Router

**Details:**

Create frontend/src/pages/Landing.tsx with hero section showcasing Nozzly features (inventory, costing, pricing, analytics), call-to-action buttons for signup/login using shadcn/ui components. Build frontend/src/components/auth/AuthProvider.tsx React context for authentication state management, storing tokens in memory for security. Create frontend/src/pages/Login.tsx and Signup.tsx that redirect to Authentik with proper OIDC parameters. Implement frontend/src/pages/AuthCallback.tsx to handle OAuth2 callback, exchange authorization code for tokens via backend /auth/callback endpoint. Use TanStack Router for navigation and route protection.

**Test Strategy:**

Test landing page displays correctly on mobile and desktop, verify signup/login buttons redirect to correct Authentik URLs with proper parameters, test successful auth callback stores tokens and redirects to dashboard, verify auth context provides user state throughout app, test logout clears tokens and redirects to landing
