# Codebase Concerns

**Analysis Date:** 2026-05-19

---

## Tech Debt

**Knitting module placeholders (4 empty routers):**
- Issue: Four API files are complete stubs with only a router declaration and TODO comments — no endpoints implemented.
- Files: `backend/app/api/v1/needle.py`, `backend/app/api/v1/patterns.py`, `backend/app/api/v1/yarn.py`, `backend/app/api/v1/projects.py`
- Impact: The routers are imported in `backend/app/main.py` (line 427 comment: "TODO: Include feature routers in future phases") but not yet wired up. No user-visible breakage today, but the module system expects them to exist.
- Fix approach: Either implement or remove and clean up the `main.py` comment referencing them.

**Phase-gated cost tracking not yet completed:**
- Issue: `backend/app/services/costing.py` (lines 173, 192, 244, 266) and `backend/app/models/model.py` (line 156) contain "Phase 2/Phase 3" comments marking rolling-average production cost fields as unimplemented.
- Files: `backend/app/services/costing.py`, `backend/app/models/model.py`, `backend/app/schemas/model.py` (line 149), `backend/app/schemas/product.py` (line 123)
- Impact: Cost analysis features silently return incomplete data; actual production cost vs. estimated cost variance is always empty.
- Fix approach: Complete Phase 2 cost roll-up in `production_run.py` lines 1372–1383 where "Phase 2: Update model rolling average" comments exist but the implementation is incomplete.

**Production code uses `print()` instead of structured logging:**
- Issue: `backend/app/main.py` (lines 26, 32, 36, 46, 53, 58, 60) and `backend/app/core/security.py` (lines 89–93) use bare `print()` calls including token preview dumps.
- Files: `backend/app/main.py`, `backend/app/core/security.py`, `backend/app/observability/tracing.py`
- Impact: Token details can appear in stdout/container logs which are not structured and may surface in log aggregators without redaction. Security risk on `security.py:90` which prints `token[:50]`.
- Fix approach: Replace all `print()` in production paths with `logger.info/warning/error`. The `logger` is already imported in these files.

**Celery configured but not used:**
- Issue: `backend/app/config.py` configures `celery_broker_url` and `celery_result_backend`, `backend/app/observability/sentry.py` integrates `CeleryIntegration`, but no Celery tasks, workers, or beat scheduler are defined anywhere in the codebase.
- Files: `backend/app/config.py` (lines 74–75), `backend/app/observability/sentry.py` (line 95)
- Impact: Dead config clutters the settings object; Sentry CeleryIntegration loads unnecessarily; the `retry_failed_webhooks()` function in `backend/app/services/square_webhook_service.py` (line 665) is documented as requiring "a background task or cron job" but is never called.
- Fix approach: Either wire up a lightweight APScheduler/arq periodic task for webhook retries, or document that manual invocation is intentional and remove the Celery config.

**Etsy sync has placeholder listing cleanup logic:**
- Issue: `backend/app/services/etsy_sync.py` lines 137–138 contain a check for `external_id.startswith("placeholder_")` — a temporary pattern from "Phase 1" that was never cleaned up.
- Files: `backend/app/services/etsy_sync.py`
- Impact: Placeholder logic will silently treat real listings that happen to start with `placeholder_` as new and overwrite them.
- Fix approach: Audit all Etsy listings for the `placeholder_` prefix, migrate any remaining, then remove the conditional branch.

---

## Known Bugs

**Order number generation race condition:**
- Symptoms: Two concurrent checkouts can receive the same order number (e.g., `MYST-20260519-001`).
- Files: `backend/app/api/v1/shop.py` lines 1440–1448
- Trigger: Two simultaneous checkout completions for the same tenant on the same day. The sequence `SELECT COUNT(*) ... LIKE prefix-date-%` then `INSERT` is not atomic; both reads return the same count before either INSERT commits.
- Workaround: None currently. `order_number` column should have a `UNIQUE` constraint and be generated via a PostgreSQL sequence or advisory lock.

**Blocking `time.sleep()` inside async request handler:**
- Symptoms: During Square payment retries with backoff, the FastAPI worker thread is blocked for up to the `MAX_RETRY_DELAY` seconds.
- Files: `backend/app/services/square_payment.py` lines 218, 238; called from `backend/app/api/v1/shop.py` line 1406
- Trigger: Square returns a retriable error (network timeout, rate limit) during checkout.
- Workaround: None. Fix by converting `process_payment` to `async def` and replacing `time.sleep(delay)` with `await asyncio.sleep(delay)`.

**Redis DB number mismatch between staging and production:**
- Symptoms: Staging environment uses Redis DB 1 (`redis://redis.batchivo.svc.cluster.local:6379/1`) while production backend configmap uses DB 0 (`redis://redis:6379/0`). Cart, checkout session, and stock reservation services all share the same `settings.redis_url` value.
- Files: `infrastructure/k8s/staging/configmap.yaml` (line 12), `infrastructure/k8s/backend/deployment.yaml` (line 12)
- Trigger: The mismatch means staging and production use different Redis databases, which is intentional — but the discrepancy makes it easy to accidentally configure them identically and cross-contaminate.
- Workaround: Ensure staging and production configmaps remain intentionally separated; add a comment explaining the DB number convention.

---

## Security Considerations

**RLS disabled in both production and staging:**
- Risk: PostgreSQL Row-Level Security policies exist in the schema but `RLS_ENABLED: "false"` is set in both `infrastructure/k8s/backend/deployment.yaml` (line 25) and `infrastructure/k8s/staging/configmap.yaml` (line 26). Tenant isolation relies entirely on application-layer `tenant_id` filters and the `get_current_tenant()` dependency.
- Files: `infrastructure/k8s/backend/deployment.yaml`, `infrastructure/k8s/staging/configmap.yaml`, `backend/app/auth/dependencies.py`
- Current mitigation: All queries in the application explicitly filter by `tenant_id`; SQLAlchemy ORM prevents raw SQL injection on parameterized queries.
- Recommendations: Enable RLS (`RLS_ENABLED: "true"`) and configure the `app_user` role password (currently `CHANGE_ME_SECURE_PASSWORD` in `infrastructure/k8s/backend/rls-secret.yaml`). This adds defense-in-depth against bugs in the ORM layer.

**`rls-secret.yaml` committed to repo with placeholder credentials:**
- Risk: `infrastructure/k8s/backend/rls-secret.yaml` is a Kubernetes Secret manifest committed to the git repository. Even with a `CHANGE_ME_SECURE_PASSWORD` placeholder, this is a pattern that encourages committing real secrets to git.
- Files: `infrastructure/k8s/backend/rls-secret.yaml`
- Current mitigation: Placeholder value; actual secret must be created imperatively per the inline instructions.
- Recommendations: Remove this file from the repo and reference it only in documentation. Use `kubectl create secret` imperatively or manage via Sealed Secrets / External Secrets Operator.

**Customer authentication endpoints have no rate limiting:**
- Risk: `backend/app/api/v1/customer_auth.py` has no `@limiter.limit()` decorators on any of its 7 endpoints (register, login, refresh, forgot-password, reset-password, verify-email, resend-verification). Admin auth in `backend/app/api/v1/auth.py` is rate-limited.
- Files: `backend/app/api/v1/customer_auth.py`, `backend/app/core/rate_limit.py`
- Current mitigation: None on the customer auth surface.
- Recommendations: Apply at minimum `AUTH_RATE_LIMIT = "5/minute"` to `/login`, `/register`, `/forgot-password`, and `/reset-password` endpoints.

**Refresh tokens are stateless and cannot be revoked:**
- Risk: Refresh tokens (7-day expiry) are pure JWTs with no server-side storage. There is no blacklist or revocation mechanism. A compromised refresh token remains valid for 7 days.
- Files: `backend/app/core/security.py` (line 19: `REFRESH_TOKEN_EXPIRE_DAYS = 7`), `backend/app/api/v1/auth.py` lines 148–192
- Current mitigation: Access tokens expire in 24 hours (configurable via `access_token_expire_minutes`).
- Recommendations: Store refresh token jti in Redis with TTL on issue; on refresh, verify jti is in the store and rotate it (delete old, insert new). This enables logout-everywhere and revocation.

**WebSocket token exposed in URL query parameter:**
- Risk: `backend/app/api/v1/printer_ws.py` (line 247) accepts the JWT via `token: str = Query(...)`. URL parameters appear in server access logs, browser history, and HTTP referrer headers.
- Files: `backend/app/api/v1/printer_ws.py`
- Current mitigation: Network-level protection via Cloudflare Tunnel.
- Recommendations: Accept the token in the first WebSocket message payload after upgrade, or use a short-lived single-use ticket exchanged via a standard HTTP endpoint immediately before the WebSocket connection.

**Redis deployed without authentication:**
- Risk: `infrastructure/k8s/redis/deployment.yaml` has no `--requirepass` argument or auth secret. Redis stores cart sessions, checkout sessions, and stock reservations containing order amounts and customer data.
- Files: `infrastructure/k8s/redis/deployment.yaml`
- Current mitigation: Network policy `infrastructure/k8s/network-policies/40-redis-policy.yaml` restricts access at the cluster network level.
- Recommendations: Add `--requirepass` with a secret, and propagate the password to `REDIS_URL` in all configmaps.

**Redis has no persistent storage:**
- Risk: `infrastructure/k8s/redis/deployment.yaml` has no `volumeMounts` or PVC. A Redis pod restart loses all cart/session/stock reservation data mid-checkout.
- Files: `infrastructure/k8s/redis/deployment.yaml`
- Current mitigation: Sessions/carts expire via TTL so data loss is bounded.
- Recommendations: Add RDB persistence via a PVC, or at minimum an `appendonly yes` argument to the Redis container command.

---

## Performance Bottlenecks

**`lazy="select"` relationships in async SQLAlchemy context:**
- Problem: 26+ relationships across `backend/app/models/` use `lazy="select"`, which triggers implicit synchronous-style N+1 queries that are incompatible with async SQLAlchemy and require explicit `selectinload` or `joinedload` at query time.
- Files: `backend/app/models/model.py` (lines 195–223), `backend/app/models/printer.py` (lines 155–198), `backend/app/models/spool.py` (line 218), `backend/app/models/designer.py` (line 115), and others.
- Cause: Any endpoint that accesses a lazily-loaded relationship without an explicit `options(selectinload(...))` will either raise `MissingGreenlet` (if accessed outside a session) or silently degrade to per-row queries.
- Improvement path: Audit each model's relationship for access patterns; convert to `lazy="raise"` to surface issues in tests, then add explicit `selectinload`/`joinedload` in query sites.

**500MB file upload reads entirely into memory:**
- Problem: `backend/app/api/v1/model_files.py` (line 79) calls `content = await file.read()` on files up to 500MB. The entire file is held in-memory before being written to local storage or S3.
- Files: `backend/app/api/v1/model_files.py` (line 79), `backend/app/services/model_file_service.py` (line 211)
- Cause: FastAPI `UploadFile` is used with `.read()` rather than streaming chunks to storage.
- Improvement path: Stream the upload to MinIO/S3 using `aiobotocore` multipart upload, or use a presigned URL pattern where the client uploads directly to object storage.

**`shop.py` is a 2,246-line monolith:**
- Problem: `backend/app/api/v1/shop.py` contains the entire storefront — product listing, cart, checkout, order lookup, reviews, contact form, sitemap — in a single file.
- Files: `backend/app/api/v1/shop.py`
- Cause: Organic growth without splitting into sub-routers.
- Improvement path: Split into `shop_products.py`, `shop_checkout.py`, `shop_orders.py`, `shop_reviews.py` sub-modules, each with their own router, and compose them in `shop.py` or `main.py`.

**Search service re-checks PostgreSQL version per query:**
- Problem: `backend/app/services/search_service.py` (line 31) runs `SELECT version()` on every `search_products()` call to detect whether it's running on PostgreSQL or SQLite.
- Files: `backend/app/services/search_service.py` lines 28–35
- Cause: Designed for test/production database compatibility detection, but not cached.
- Improvement path: Cache the result at application startup or on first call using a module-level variable.

---

## Fragile Areas

**`CLAUDE.md` references Resend; code uses Brevo:**
- Files: `/CLAUDE.md` (Integrations section says "Resend"), `backend/app/services/email_service.py` (uses Brevo API at `https://api.brevo.com/v3/smtp/email`), `backend/app/config.py` (`brevo_api_key`)
- Why fragile: Documentation drift. Any developer following `CLAUDE.md` will look for `resend-credentials` Kubernetes secret (the secret name mentioned in CLAUDE.md) but the backend reads `BREVO_API_KEY`.
- Safe modification: Update `CLAUDE.md` to reference Brevo, or migrate the email service to Resend and update config.

**Webhook retry is never invoked:**
- Files: `backend/app/services/square_webhook_service.py` `retry_failed_webhooks()` (line 665), `backend/app/services/webhook_service.py` `_schedule_retry()` (line 376)
- Why fragile: Failed Square webhook events accumulate in the database with no automatic retry. The function exists and is correct but has no caller.
- Safe modification: Add a periodic task (e.g., APScheduler in-process or a Kubernetes CronJob) that calls `retry_failed_webhooks(db)` every few minutes.

**`lazy="select"` on `designer.products` relationship:**
- Files: `backend/app/models/designer.py` line 115
- Why fragile: The comment says "Use lazy load to avoid loading all products by default" which is correct intent, but in async SQLAlchemy `lazy="select"` raises `MissingGreenlet` if accessed without an explicit `await`. Any new endpoint that accesses `designer.products` without the right `selectinload` will crash at runtime, not at development/test time.
- Safe modification: Use `lazy="raise"` to force explicit eager loading at query time and expose the issue in tests.

**`staging/frontend.yaml` uses `:latest` image tag:**
- Files: `infrastructure/k8s/staging/frontend.yaml` (line 51)
- Why fragile: Using `:latest` means a pod restart pulls whatever image is currently tagged latest in the registry, which may not match the version of the backend deployed alongside it.
- Safe modification: Pin the staging frontend image tag to a specific digest or build tag the same way production does.

**`harbor/values.yaml` has placeholder passwords committed to git:**
- Files: `infrastructure/harbor/values.yaml` (lines 44, 53, 60, 61)
- Why fragile: Placeholder strings `<CHANGE-ME-*>` in a committed Helm values file. Anyone setting up Harbor by running `helm install -f values.yaml` without reading carefully will deploy with these defaults.
- Safe modification: Move secrets to a separate `values-secrets.yaml` file in `.gitignore`, and document this clearly.

---

## Scaling Limits

**Redis is single-instance with no persistence:**
- Current capacity: One replica, 256Mi memory limit.
- Limit: Losing the Redis pod loses all active carts, checkout sessions, and stock reservations. At higher order volume, Redis memory becomes the cart/session store bottleneck.
- Scaling path: Add RDB/AOF persistence via PVC. Consider Redis Sentinel or a managed Redis service if uptime SLA increases.

**Database connection pool is fixed at 10+20 overflow:**
- Current capacity: `pool_size=10`, `max_overflow=20` (30 total) in `backend/app/database.py` lines 28–29.
- Limit: Under high concurrency (many tenants simultaneously), the pool may exhaust, causing request queuing.
- Scaling path: Introduce PgBouncer for connection multiplexing before increasing the pool size.

---

## Dependencies at Risk

**`etsyv3` library (Etsy integration):**
- Risk: The `etsyv3` library is a third-party wrapper around the Etsy v3 API. Etsy periodically deprecates API versions and breaks third-party wrappers.
- Impact: Etsy sync would silently fail or throw import errors.
- Migration plan: Monitor the library's maintenance status; consider wrapping Etsy API calls behind an interface layer so the HTTP client can be swapped.

---

## Missing Critical Features

**No periodic/background job runner:**
- Problem: Several features require periodic execution: Square webhook retries (`retry_failed_webhooks`), SpoolMan database sync, Etsy listing sync. None have a scheduler. There is Celery configuration but no Celery worker.
- Blocks: Automated webhook retries, automated external marketplace syncing.

**RLS not enabled in production:**
- Problem: PostgreSQL Row-Level Security is fully implemented in the schema but disabled in production. The `app_user` role password is a placeholder.
- Blocks: Database-level multi-tenant isolation guarantee; compliance posture for production data isolation.

---

## Test Coverage Gaps

**Printer WebSocket endpoint (`/ws/printers`) has no tests:**
- What's not tested: WebSocket lifecycle, token verification, connection/disconnection, message broadcast to tenants.
- Files: `backend/app/api/v1/printer_ws.py`
- Risk: Auth bypass or broadcast-to-wrong-tenant bugs could go undetected.
- Priority: Medium

**Customer authentication endpoints have no rate-limit tests:**
- What's not tested: That brute-force login attempts are blocked after threshold; no test verifies `429` responses on `customer_auth` endpoints.
- Files: `backend/app/api/v1/customer_auth.py`, `backend/tests/api/test_customer_auth.py`
- Risk: Rate limiting is absent (see Security section), so this is a double gap.
- Priority: High

**Order number uniqueness under concurrent load:**
- What's not tested: Concurrent checkout requests generating duplicate order numbers.
- Files: `backend/app/api/v1/shop.py` lines 1440–1448
- Risk: Duplicate order numbers in production; `ORDER_NUMBER` does not appear to have a database UNIQUE constraint enforced.
- Priority: High

**Knitting module routers are registered but have zero tests:**
- What's not tested: `needle`, `patterns`, `yarn`, `projects` routers return correct 404/405 or are completely absent from router list.
- Files: `backend/app/api/v1/needle.py`, `backend/app/api/v1/patterns.py`, `backend/app/api/v1/yarn.py`, `backend/app/api/v1/projects.py`
- Risk: Low — they are empty — but they are imported and could cause import errors if incorrectly changed.
- Priority: Low

**`retry_failed_webhooks` is never called — no integration test:**
- What's not tested: End-to-end retry flow from failed webhook delivery to eventual retry execution.
- Files: `backend/app/services/square_webhook_service.py` lines 665–711
- Risk: Retry logic could be silently broken; payments might never reconcile on Square webhook failure.
- Priority: Medium

---

*Concerns audit: 2026-05-19*
