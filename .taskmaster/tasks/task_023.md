# Task ID: 023
# Title: Square Credentials Management Page
# Status: pending
# Priority: high
# Dependencies: none
# Created: 2024-12-22

## Description
Add an admin page in Nozzly to manage Square payment credentials with the ability to switch between sandbox and production environments without requiring code deployment.

## Requirements

### Backend API
- `GET /api/v1/admin/settings/square` - Get current Square config (masked tokens)
- `PUT /api/v1/admin/settings/square` - Update Square credentials
- Store credentials securely (encrypted in DB or update k8s secrets)
- Add environment toggle (sandbox/production)
- Validate credentials before saving (test API call to Square)

### Frontend Admin UI
- Add "Payment Settings" page under Admin > Settings
- Form fields:
  - Environment toggle (Sandbox / Production)
  - App ID
  - Access Token (masked input)
  - Location ID
  - Webhook Signature Key (optional)
- Show current environment status prominently (banner)
- "Test Connection" button to validate credentials
- Warning banner when in sandbox mode

### Security Requirements
- Admin-only access (require authentication)
- Encrypt access tokens at rest
- Audit log for credential changes
- Never expose full tokens in API responses (mask all but last 4 chars)

## Acceptance Criteria
- [ ] Admin can view current Square environment (sandbox/production)
- [ ] Admin can update Square credentials via UI
- [ ] Credentials are validated before saving
- [ ] Environment can be switched without code deployment
- [ ] Audit trail for credential changes
- [ ] Frontend shop uses the configured credentials dynamically

## Technical Notes
- Current credentials stored in k8s secret `square-credentials` in `nozzly` namespace
- Frontend needs `VITE_SQUARE_APP_ID` and `VITE_SQUARE_LOCATION_ID`
- Consider serving frontend config via API endpoint instead of env vars
- May need to add `/api/v1/shop/config` endpoint for frontend to fetch Square app ID

## Test Strategy
- Test credential update with valid/invalid tokens
- Test environment switch from sandbox to production
- Verify credentials are masked in API responses
- Verify audit log entries are created
