# Product Requirements Document: Nozzly Platform Admin & White-Label Shop System

## Overview

Transform Nozzly from a single-tenant application into a full multi-tenant SaaS platform with platform administration capabilities and white-label shop functionality.

## Goals

1. Enable platform-wide administration for managing all tenants
2. Allow self-service tenant registration with automatic shop provisioning
3. Support both subdomain routing (tenant.nozzly.shop) and custom domains
4. Provide a themeable white-label shop template for all tenants
5. Maintain backwards compatibility with existing Mystmere Forge integration

## User Stories

### Platform Admin (jonathan@techize.co.uk)
- As a platform admin, I want to see a list of all tenants so I can monitor the platform
- As a platform admin, I want to view tenant details and statistics so I can support customers
- As a platform admin, I want to impersonate into any tenant so I can debug issues
- As a platform admin, I want to deactivate/reactivate tenants for account management
- As a platform admin, I want to search users across all tenants for support purposes
- As a platform admin, I want to configure platform-wide settings

### Tenant Owner (kay@techize.co.uk)
- As a new user, I want to register my business and get a shop automatically
- As a tenant owner, I want my shop available at myshop.nozzly.shop immediately
- As a tenant owner, I want to configure my shop's branding (logo, colors, fonts)
- As a tenant owner, I want to set up a custom domain for my shop
- As a tenant owner, I want to switch between tenants if I own multiple businesses

### Shop Customer
- As a customer, I want to browse products on a branded shop
- As a customer, I want the shop to look consistent with the business brand
- As a customer, I want to create an account to track my orders

## Technical Requirements

### Phase 1: Platform Admin Backend

#### 1.1 Database Schema Changes
- Add `is_platform_admin` boolean column to `users` table (default: false)
- Create `platform_admin_audit_logs` table for tracking admin actions
- Create `platform_settings` table for global configuration
- Create Alembic migration for all schema changes

#### 1.2 Platform Admin Authentication
- Update JWT token creation to include `is_platform_admin` claim
- Create `get_platform_admin` dependency that validates admin access
- Create `PlatformAdminDB` session that bypasses RLS for cross-tenant queries
- Update login endpoint to include admin flag in token

#### 1.3 Platform Admin API Endpoints
Create `/api/v1/platform/` router with endpoints:
- `GET /tenants` - List all tenants with pagination, search, filters
- `GET /tenants/{id}` - Get tenant details with user count, product count, order count, revenue
- `POST /tenants/{id}/impersonate` - Generate impersonation token for tenant
- `POST /tenants/{id}/deactivate` - Deactivate tenant (sets is_active=false)
- `POST /tenants/{id}/reactivate` - Reactivate tenant
- `GET /users` - Search users across all tenants
- `GET /users/{id}` - Get user details with tenant memberships
- `GET /settings` - List platform settings
- `PUT /settings/{key}` - Update platform setting
- `GET /audit` - List platform admin audit logs

#### 1.4 Platform Admin Service Layer
- Create `PlatformAdminService` class with business logic
- Implement tenant statistics aggregation
- Implement impersonation token generation with audit trail
- Implement platform admin action logging

#### 1.5 Platform Admin Tests
- Unit tests for platform admin dependencies
- Unit tests for platform admin service
- Integration tests for all platform admin endpoints
- Test RLS bypass for platform admin queries
- Test impersonation token flow

### Phase 2: White-Label Shop Backend

#### 2.1 Wire Up Shop Resolver
- Register `shop_resolver.router` in `main.py`
- Create `get_shop_tenant` dependency for public shop endpoints
- Create `get_shop_sales_channel` dependency for pricing lookups

#### 2.2 Multi-Tenant Shop Refactoring
- Replace all hardcoded "Mystmereforge" references in `shop.py` with dynamic tenant
- Update product endpoints to use `ShopTenant` dependency
- Update checkout to use `ShopChannel` dependency
- Implement tenant-specific order number generation using `tenant.settings.shop.order_prefix`
- Update email service to accept tenant branding parameters

#### 2.3 Shop Configuration Endpoints
Add to `/api/v1/settings/`:
- `GET /shop` - Get shop settings for tenant
- `PUT /shop` - Update shop settings (name, tagline, order prefix, etc.)
- `GET /branding` - Get branding settings
- `PUT /branding` - Update branding (logo, colors, fonts)
- `POST /custom-domain` - Initialize custom domain setup
- `GET /custom-domain/status` - Get domain verification status
- `POST /custom-domain/verify` - Trigger DNS verification
- `DELETE /custom-domain` - Remove custom domain

#### 2.4 DNS Verification Service
- Create `DomainVerificationService` class
- Implement CNAME verification (must point to shops.nozzly.app)
- Implement TXT record verification for domain ownership
- Generate unique verification tokens per tenant/domain
- Store verification status in tenant settings JSONB

#### 2.5 Mystmere Forge Migration
- Create migration script to populate proper shop settings for existing tenant
- Preserve existing order number prefix (MF-)
- Set custom_domain_verified=true for existing domain

#### 2.6 Multi-Tenant Shop Tests
- Test shop resolution by subdomain
- Test shop resolution by custom domain
- Test tenant-specific order numbers
- Test unknown hostname returns 404
- Test domain verification flow

### Phase 3: Admin Frontend Enhancement

#### 3.1 Platform Admin Pages
- Create `PlatformDashboard.tsx` - Platform metrics overview
- Create `TenantsPage.tsx` - Tenant list with search/filter/pagination
- Create `TenantDetailPage.tsx` - Single tenant details and actions
- Create `PlatformSettingsPage.tsx` - Platform configuration

#### 3.2 Platform Admin Components
- Create `TenantTable.tsx` - Sortable, filterable tenant table
- Create `TenantStats.tsx` - Metrics display cards
- Create `ImpersonateBanner.tsx` - Warning banner when impersonating

#### 3.3 Tenant Switcher
- Create `TenantSwitcher.tsx` - Dropdown component for header
- Update `AuthContext.tsx` - Add tenants list and switchTenant function
- Update `AppLayout.tsx` - Include tenant switcher in header

#### 3.4 Platform Admin Hooks
- Create `usePlatformAdmin.ts` - Check if user is platform admin
- Create `useImpersonation.ts` - Manage impersonation state
- Create `useTenantSwitch.ts` - Handle tenant switching

#### 3.5 Route Updates
- Add `/platform` routes protected by platform admin check
- Add lazy loading for platform admin pages
- Update route guards to handle impersonation

### Phase 4: White-Label Shop Template

#### 4.1 Project Setup
- Create `/shop` directory with Vite + React + TailwindCSS
- Configure shadcn/ui components
- Set up TanStack Query for data fetching
- Set up React Router for navigation

#### 4.2 Shop Context System
- Create `ShopContext.tsx` - Tenant config, theming, labels
- Create `CartContext.tsx` - Cart state management (adapt from Mystmere)
- Create `CustomerContext.tsx` - Customer authentication

#### 4.3 Dynamic Theming
- Create CSS variable-based theming system
- Create `useTheme.ts` hook for runtime theme application
- Create `theme.ts` utilities for color manipulation
- Support dynamic favicon and logo loading

#### 4.4 Shop Layout Components
- Create `ShopLayout.tsx` - Themed page wrapper
- Create `Header.tsx` - Navigation, cart, account
- Create `Footer.tsx` - Links, social, contact
- Create `Navigation.tsx` - Category navigation

#### 4.5 Shop Product Components
- Create `ProductCard.tsx` - Grid/list item display
- Create `ProductGrid.tsx` - Responsive product grid
- Create `CategoryNav.tsx` - Category filter sidebar
- Create `SearchBar.tsx` - Product search with results

#### 4.6 Shop Pages
- Create `HomePage.tsx` - Hero, featured products, categories
- Create `ShopPage.tsx` - Product listing with filters
- Create `ProductPage.tsx` - Product detail, variants, add to cart
- Create `CartPage.tsx` - Cart review, quantity management
- Create `CheckoutPage.tsx` - Shipping, payment integration
- Create `OrderConfirmationPage.tsx` - Order success display

#### 4.7 Customer Account Pages
- Create `AccountPage.tsx` - Customer dashboard
- Create `LoginPage.tsx` - Customer login form
- Create `RegisterPage.tsx` - Customer registration
- Create `OrderHistoryPage.tsx` - Past orders list

#### 4.8 Shop API Integration
- Create `api.ts` - Shop API client with tenant context
- Create `useProducts.ts` - Product fetching hook
- Create `useCategories.ts` - Category fetching hook
- Create `useShopConfig.ts` - Tenant config fetching hook

### Phase 5: Deployment

#### 5.1 Shop Frontend Docker
- Create `Dockerfile` for shop frontend
- Configure nginx for SPA routing
- Set up build pipeline

#### 5.2 Kubernetes Manifests
- Create `shop/deployment.yaml` - Shop frontend deployment
- Create `shop/service.yaml` - ClusterIP service
- Create `shop/ingressroute.yaml` - Traefik routing rules

#### 5.3 Subdomain Routing
- Configure wildcard DNS for *.nozzly.shop
- Configure Traefik to route subdomains to shop frontend
- Shop frontend reads hostname and calls shop resolver

#### 5.4 Custom Domain Support
- Configure cert-manager for automatic SSL
- Update ingress to handle verified custom domains
- Document DNS setup requirements for customers

## Non-Functional Requirements

### Security
- Platform admin actions must be audit logged
- Impersonation must include original admin ID in token
- Custom domain verification prevents domain hijacking
- RLS must remain enforced for non-platform-admin users

### Performance
- Tenant list should paginate (max 50 per page)
- Shop config should be cached in frontend
- DNS verification should be rate-limited

### Backwards Compatibility
- Mystmere Forge must continue working unchanged
- Existing API endpoints must not break
- Existing order numbers must be preserved

## Out of Scope (Future)

- Billing and subscription management
- Usage-based pricing tiers
- White-label mobile app
- Multi-region deployment
- Advanced analytics dashboard

## Success Criteria

1. jonathan@techize.co.uk can log in and see ALL tenants
2. jonathan@ can impersonate into any tenant
3. kay@techize.co.uk can self-register a knitting tenant
4. Kay's tenant gets `kay.nozzly.shop` subdomain automatically
5. Kay can configure `kaysknitting.co.uk` custom domain
6. Shop template renders with Kay's branding
7. Mystmere Forge continues working unchanged
