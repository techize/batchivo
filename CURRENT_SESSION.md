# Nozzly Current Session

**Last Updated**: 2025-11-17 22:10 GMT
**Project**: Nozzly (nozzly.app)
**Current Focus**: Authentication Issues & Production Runs Deployment

---

## Current Status

### ✅ Completed Today (2025-11-17)

1. **Production Runs Deployment**:
   - Deployed backend v1.15 with production runs API
   - Deployed frontend v1.10 with navigation
   - Fixed 7 major issues during deployment

2. **Issues Resolved**:
   - PostgreSQL uuid-ossp extension missing
   - API double prefix bug (404 errors)
   - Request body structure mismatch (422 errors)
   - Invalid tenant ID foreign key violations
   - Missing material types in database
   - Stale frontend pods
   - Missing navigation link

3. **Database Setup**:
   - Enabled uuid-ossp extension
   - Created 3 production run tables
   - Added 8 common material types

### 🔴 Blocking Issues

1. **Authentication - Frequent Logouts**:
   - **Problem**: Tokens stored in memory only, lost on page refresh
   - **Impact**: Users logged out on every page refresh
   - **Root Cause**: `authTokensCache` variable in `frontend/src/lib/auth.ts:68`
   - **Next Step**: Implement sessionStorage or secure cookie storage

2. **Authentication - Signup Button Broken**:
   - **Problem**: Signup button doesn't work
   - **Root Cause**: `getAuthUrl()` treats login/signup identically (both go to same endpoint)
   - **Location**: `frontend/src/lib/auth.ts:48-53`
   - **Next Step**: Configure Authentik enrollment flow, update function

3. **Data Loss Mystery**:
   - **Problem**: Previously entered material types and spools disappeared
   - **Impact**: User must re-enter all spool data
   - **Status**: Cause unknown, needs investigation
   - **Next Step**: Review PostgreSQL logs, implement backup solution

---

## Next Actions

### Priority 1 - Fix Authentication (Immediate)

1. **Token Persistence**:
   ```typescript
   // Update frontend/src/lib/auth.ts
   // Replace in-memory storage with sessionStorage
   // Add automatic token refresh mechanism
   ```

2. **Signup Flow**:
   ```typescript
   // Research Authentik enrollment endpoint
   // Update getAuthUrl() to use enrollment flow for signup
   // Test user registration
   ```

3. **Token Refresh**:
   ```typescript
   // Implement automatic refresh when token about to expire
   // Use /api/v1/auth/refresh endpoint
   // Handle refresh token expiration
   ```

### Priority 2 - Data Loss Investigation

1. Check PostgreSQL logs for DROP/TRUNCATE commands
2. Review all migration files for potential data deletion
3. Implement automated backup solution (pg_dump to MinIO/S3)

### Priority 3 - Production Readiness

1. Replace hardcoded tenant ID with JWT extraction
2. Add proper authentication middleware
3. Implement role-based access control

---

## Key Files

### Backend
- `app/api/v1/auth.py` - Authentication endpoints
- `app/api/v1/production_runs.py` - Production run API (v1.15)
- `app/schemas/production_run.py` - Request/response schemas
- `app/auth/dependencies.py` - Auth dependencies

### Frontend
- `src/contexts/AuthContext.tsx` - Auth state management
- `src/lib/auth.ts` - Auth utilities (NEEDS FIX)
- `src/components/layout/AppLayout.tsx` - Navigation

### Infrastructure
- `infrastructure/k8s/backend/deployment.yaml` - Backend deployment (v1.15)
- `infrastructure/k8s/frontend/deployment.yaml` - Frontend deployment (v1.10)

---

## Environment

- **Cluster**: k3s at 192.168.98.138
- **Registry**: 192.168.98.138:30500 (HTTP)
- **Domain**: nozzly.app (Cloudflare Tunnel)
- **Database**: PostgreSQL (postgres-0 pod, nozzly namespace)
- **Auth**: Authentik at auth.nozzly.app

---

## Session Notes

### Authentication Investigation Findings

1. **Token Storage Issue**:
   - Located in `frontend/src/lib/auth.ts:68`
   - `let authTokensCache: AuthTokens | null = null` (memory only)
   - Lost on page refresh/reload
   - Explains "keeps logging me out" complaint

2. **Signup Flow Issue**:
   - `getAuthUrl()` function at `frontend/src/lib/auth.ts:28`
   - Line 49-51 shows signup and login use identical endpoint
   - Need Authentik enrollment flow configuration
   - Enrollment endpoint not found at `/if/flow/enrollment/` (404)

3. **No Auto-Refresh**:
   - `isTokenExpired()` checks expiration (5-minute buffer)
   - No automatic refresh when token expires
   - `AuthContext.tsx:43` checks token but doesn't refresh
   - Backend has `/api/v1/auth/refresh` endpoint available

### Deployment Process

**Backend Build & Deploy**:
```bash
cd backend
docker buildx build --platform linux/amd64 -t nozzly-backend:vX.X --load .
docker tag nozzly-backend:vX.X 192.168.98.138:30500/nozzly-backend:vX.X
docker push 192.168.98.138:30500/nozzly-backend:vX.X
kubectl set image deployment/backend backend=192.168.98.138:30500/nozzly-backend:vX.X -n nozzly
kubectl rollout status deployment/backend -n nozzly --timeout=120s
```

**Frontend Build & Deploy**:
```bash
cd frontend
docker buildx build --platform linux/amd64 -t nozzly-frontend:vX.X --load .
docker tag nozzly-frontend:vX.X 192.168.98.138:30500/nozzly-frontend:vX.X
docker push 192.168.98.138:30500/nozzly-frontend:vX.X
kubectl set image deployment/frontend frontend=192.168.98.138:30500/nozzly-frontend:vX.X -n nozzly
kubectl rollout status deployment/frontend -n nozzly --timeout=120s
```

---

## RESUME TOMORROW

**Start with**: Fixing authentication token persistence
1. Read current implementation in `src/lib/auth.ts`
2. Implement sessionStorage with secure flags
3. Add automatic token refresh mechanism
4. Test page refresh doesn't log user out
5. Then move to signup button fix

**Full Session Log**: `/Users/jonathan/Repos/2ndBrain/Sessions/2025-11-17-nozzly-production-runs-deployment-and-fixes.md`
