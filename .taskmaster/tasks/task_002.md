# Task ID: 2

**Title:** Configure Authentik OAuth2 Application for Nozzly

**Status:** done

**Dependencies:** 1 ✓

**Priority:** high

**Description:** Set up OAuth2/OIDC application in Authentik admin interface with proper scopes and redirect URIs

**Details:**

Access Authentik admin at https://auth.nozzly.app/if/admin/ using default credentials. Create new OAuth2/OpenID provider application with: client type = 'Confidential', redirect URIs = 'https://nozzly.app/auth/callback', scopes = 'openid profile email', token validity = 24 hours. Configure user enrollment flow for signup and authentication flow for login. Generate and securely store client ID and client secret for backend configuration. Set up custom branding if needed.

**Test Strategy:**

Verify application appears in Authentik admin, test authorization URL generation, confirm redirect URIs are correctly configured, validate that required scopes (openid, profile, email) are available, test enrollment flow creates new users successfully
