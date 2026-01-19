/**
 * Main application with routing and authentication
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import {
  Router,
  Route,
  RootRoute,
  RouterProvider,
  Navigate,
  Outlet,
} from '@tanstack/react-router'
import { useEffect } from 'react'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { Landing } from '@/pages/Landing'
import { Login } from '@/pages/Login'
import { Signup } from '@/pages/Signup'
import { VerifyEmail } from '@/pages/VerifyEmail'
import { Onboarding } from '@/pages/Onboarding'
import { ForgotPassword } from '@/pages/ForgotPassword'
import { ResetPassword } from '@/pages/ResetPassword'
import { AuthCallback } from '@/pages/AuthCallback'
import { Dashboard } from '@/pages/Dashboard'
import { DashboardHome } from '@/pages/DashboardHome'
import { Models } from '@/pages/Models'
import { ModelDetailPage } from '@/pages/ModelDetailPage'
import { ModelCreatePage } from '@/pages/ModelCreatePage'
import { ModelEditPage } from '@/pages/ModelEditPage'
import { Products } from '@/pages/Products'
import { ProductDetailPage } from '@/pages/ProductDetailPage'
import { ProductCreatePage } from '@/pages/ProductCreatePage'
import { ProductEditPage } from '@/pages/ProductEditPage'
import { ProductionRuns } from '@/pages/ProductionRuns'
import { ProductionRunDetailPage } from '@/pages/ProductionRunDetailPage'
import { ProductionRunCreatePage } from '@/pages/ProductionRunCreatePage'
import { Consumables } from '@/pages/Consumables'
import { SalesChannels } from '@/pages/SalesChannels'
import { SalesChannelDetailPage } from '@/pages/SalesChannelDetailPage'
import { SalesChannelCreatePage } from '@/pages/SalesChannelCreatePage'
import { SalesChannelEditPage } from '@/pages/SalesChannelEditPage'
import { Categories } from '@/pages/Categories'
import { Designers } from '@/pages/Designers'
import { Printers } from '@/pages/Printers'
import { Orders } from '@/pages/Orders'
import { OrderDetailPage } from '@/pages/OrderDetailPage'
import { SpoolLabelPage } from '@/pages/SpoolLabelPage'
import { SpoolQuickUpdatePage } from '@/pages/SpoolQuickUpdatePage'
import { SpoolScanPage } from '@/pages/SpoolScanPage'
import { HelpIndex } from '@/pages/help/HelpIndex'
import { HelpGuide } from '@/pages/help/HelpGuide'
import { Settings } from '@/pages/Settings'
import { Loader2 } from 'lucide-react'

// Knitting module pages
import { KnittingDashboard } from '@/pages/knitting/KnittingDashboard'
import { YarnInventory } from '@/pages/knitting/YarnInventory'
import { NeedleCollection } from '@/pages/knitting/NeedleCollection'
import { Patterns } from '@/pages/knitting/Patterns'
import { Projects } from '@/pages/knitting/Projects'

// Platform admin pages
import { PlatformDashboard } from '@/pages/platform/PlatformDashboard'
import { TenantsPage } from '@/pages/platform/TenantsPage'
import { TenantDetailPage } from '@/pages/platform/TenantDetailPage'
import { TenantModulesPage } from '@/pages/platform/TenantModulesPage'
import { AuditLogsPage } from '@/pages/platform/AuditLogsPage'

// Guards
import { ModuleGuard } from '@/components/guards/ModuleGuard'
import { PlatformAdminGuard } from '@/components/guards/PlatformAdminGuard'

// Create a query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

// Root route
const rootRoute = new RootRoute({
  component: () => (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  ),
})

// Public routes
const landingRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/',
  component: Landing,
})

const loginRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/login',
  component: Login,
})

const signupRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/signup',
  component: Signup,
})

const verifyEmailRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/verify-email',
  component: VerifyEmail,
})

const onboardingRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/onboarding',
  component: () => (
    <ProtectedRoute>
      <Onboarding />
    </ProtectedRoute>
  ),
})

const authCallbackRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/auth/callback',
  component: AuthCallback,
})

const forgotPasswordRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/forgot-password',
  component: ForgotPassword,
})

const resetPasswordRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/reset-password',
  component: ResetPassword,
})

// Logout route - clears auth and redirects to login
function LogoutPage() {
  const { logout } = useAuth()

  useEffect(() => {
    logout()
  }, [logout])

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <Loader2 className="w-8 h-8 animate-spin text-primary" />
    </div>
  )
}

const logoutRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/logout',
  component: LogoutPage,
})

// Help routes (public)
const helpIndexRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/help',
  component: HelpIndex,
})

const helpGuideRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/help/$slug',
  component: HelpGuide,
})

// Protected route wrapper
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!isAuthenticated) {
    // Preserve the current URL so we can redirect back after login
    const currentPath = window.location.pathname + window.location.search
    if (currentPath !== '/') {
      // Use direct location change to ensure query params are preserved
      window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
      return null
    }
    return <Navigate to="/login" />
  }

  return <>{children}</>
}

// Protected routes
const dashboardRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/dashboard',
  component: () => (
    <ProtectedRoute>
      <DashboardHome />
    </ProtectedRoute>
  ),
})

// Inventory route (filament spools)
const inventoryRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/inventory',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Dashboard />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Filaments route (alias for inventory - spools management)
const filamentsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/filaments',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Dashboard />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const productsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/products',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Products />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Static routes must be defined with exact path matching
const productCreateRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/products/new',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ProductCreatePage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const productEditRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/products/$productId/edit',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ProductEditPage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Dynamic route must come after static routes
const productDetailRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/products/$productId',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ProductDetailPage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Consumables route
const consumablesRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/consumables',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Consumables />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Models routes (printed items with BOM)
const modelsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/models',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Models />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const modelCreateRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/models/new',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ModelCreatePage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const modelEditRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/models/$modelId/edit',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ModelEditPage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const modelDetailRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/models/$modelId',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ModelDetailPage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Production Runs routes
const productionRunsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/production-runs',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ProductionRuns />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const productionRunCreateRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/production-runs/new',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ProductionRunCreatePage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const productionRunDetailRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/production-runs/$runId',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <ProductionRunDetailPage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Orders routes
const ordersRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/orders',
  component: () => (
    <ProtectedRoute>
      <Orders />
    </ProtectedRoute>
  ),
})

const orderDetailRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/orders/$orderId',
  component: () => (
    <ProtectedRoute>
      <OrderDetailPage />
    </ProtectedRoute>
  ),
})

// Sales Channels routes
const salesChannelsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/sales-channels',
  component: () => (
    <ProtectedRoute>
      <SalesChannels />
    </ProtectedRoute>
  ),
})

const salesChannelCreateRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/sales-channels/new',
  component: () => (
    <ProtectedRoute>
      <SalesChannelCreatePage />
    </ProtectedRoute>
  ),
})

const salesChannelEditRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/sales-channels/$channelId/edit',
  component: () => (
    <ProtectedRoute>
      <SalesChannelEditPage />
    </ProtectedRoute>
  ),
})

const salesChannelDetailRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/sales-channels/$channelId',
  component: () => (
    <ProtectedRoute>
      <SalesChannelDetailPage />
    </ProtectedRoute>
  ),
})

// Categories route
const categoriesRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/categories',
  component: () => (
    <ProtectedRoute>
      <Categories />
    </ProtectedRoute>
  ),
})

// Designers route
const designersRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/designers',
  component: () => (
    <ProtectedRoute>
      <Designers />
    </ProtectedRoute>
  ),
})

// Printers routes
const printersRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/printers',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Printers />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Filament/Spool routes
const spoolLabelRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/filaments/$spoolId/label',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <SpoolLabelPage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const spoolQuickUpdateRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/filaments/$spoolId/update',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <SpoolQuickUpdatePage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

const spoolScanRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/filaments/scan',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <SpoolScanPage />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Settings route
const settingsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/settings',
  component: () => (
    <ProtectedRoute>
      <Settings />
    </ProtectedRoute>
  ),
})

// ==================== Knitting Module Routes ====================

// Knitting Dashboard (alternate dashboard for knitting tenants)
const knittingDashboardRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/knitting-dashboard',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <KnittingDashboard />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Yarn Inventory
const yarnRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/yarn',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <YarnInventory />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Needles & Hooks
const needlesRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/needles',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <NeedleCollection />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Patterns
const patternsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/patterns',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Patterns />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// Projects
const projectsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/projects',
  component: () => (
    <ProtectedRoute>
      <ModuleGuard>
        <Projects />
      </ModuleGuard>
    </ProtectedRoute>
  ),
})

// ==================== Platform Admin Routes ====================

// Platform Dashboard
const platformDashboardRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/platform',
  component: () => (
    <PlatformAdminGuard>
      <PlatformDashboard />
    </PlatformAdminGuard>
  ),
})

// Tenants List
const platformTenantsRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/platform/tenants',
  component: () => (
    <PlatformAdminGuard>
      <TenantsPage />
    </PlatformAdminGuard>
  ),
})

// Tenant Detail
const platformTenantDetailRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/platform/tenants/$tenantId',
  component: () => (
    <PlatformAdminGuard>
      <TenantDetailPage />
    </PlatformAdminGuard>
  ),
})

// Tenant Modules
const platformTenantModulesRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/platform/tenants/$tenantId/modules',
  component: () => (
    <PlatformAdminGuard>
      <TenantModulesPage />
    </PlatformAdminGuard>
  ),
})

// Audit Logs
const platformAuditRoute = new Route({
  getParentRoute: () => rootRoute,
  path: '/platform/audit',
  component: () => (
    <PlatformAdminGuard>
      <AuditLogsPage />
    </PlatformAdminGuard>
  ),
})

// Create route tree
// IMPORTANT: Static routes must come before dynamic routes
// /products/new must come before /products/$productId
const routeTree = rootRoute.addChildren([
  landingRoute,
  loginRoute,
  signupRoute,
  verifyEmailRoute,      // Email verification (from signup)
  onboardingRoute,       // Onboarding wizard (after verification)
  authCallbackRoute,
  forgotPasswordRoute,
  resetPasswordRoute,
  logoutRoute,           // Logout - clears auth and redirects
  helpIndexRoute,        // Help center index (public)
  helpGuideRoute,        // Individual guide pages (public)
  dashboardRoute,
  inventoryRoute,         // Inventory (filament spools)
  filamentsRoute,         // Filaments (alias for inventory)
  productsRoute,
  productCreateRoute,  // Static route first
  productEditRoute,    // /products/$productId/edit before /products/$productId
  productDetailRoute,  // Dynamic route last
  consumablesRoute,    // Consumables inventory
  modelsRoute,         // Models catalog (printed items with BOM)
  modelCreateRoute,    // Static route first
  modelEditRoute,      // /models/$modelId/edit before /models/$modelId
  modelDetailRoute,    // Dynamic route last
  productionRunsRoute,
  productionRunCreateRoute,  // Static route first
  productionRunDetailRoute,  // Dynamic route last
  ordersRoute,               // Orders list
  orderDetailRoute,          // Order detail view
  salesChannelsRoute,        // Sales channels list
  salesChannelCreateRoute,   // Static route first
  salesChannelEditRoute,     // /sales-channels/$channelId/edit before /sales-channels/$channelId
  salesChannelDetailRoute,   // Dynamic route last
  categoriesRoute,           // Categories list
  designersRoute,            // Designers list
  printersRoute,             // Printers list
  spoolLabelRoute,           // Spool label for printing
  spoolScanRoute,            // QR code scanner (static route first)
  spoolQuickUpdateRoute,     // Quick weight update (QR destination)
  settingsRoute,             // Settings page
  // Knitting module routes
  knittingDashboardRoute,    // Knitting-specific dashboard
  yarnRoute,                 // Yarn inventory
  needlesRoute,              // Needles & hooks collection
  patternsRoute,             // Pattern library
  projectsRoute,             // Knitting projects
  // Platform admin routes
  platformDashboardRoute,    // Platform admin dashboard
  platformTenantsRoute,      // Tenants list (static route first)
  platformTenantModulesRoute, // Tenant modules (specific route before generic)
  platformTenantDetailRoute, // Tenant detail (dynamic route last)
  platformAuditRoute,        // Audit logs
])

// Create router
const router = new Router({ routeTree })

// Register router for type safety
declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  )
}

export default App
