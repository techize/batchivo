/**
 * AppLayout Component
 *
 * Shared layout for authenticated pages with navigation.
 * Responsive: hamburger menu on mobile, full nav on desktop.
 * Dynamically loads navigation based on tenant modules.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  LogOut,
  User,
  Package,
  Box,
  Play,
  Wrench,
  Menu,
  Layers,
  Store,
  LayoutDashboard,
  ShoppingBag,
  Printer,
  FolderOpen,
  Brush,
  HelpCircle,
  Settings,
  Palette,
  Pen,
  FileText,
  FolderKanban,
  Loader2,
  Shield,
  type LucideIcon,
} from 'lucide-react'
import { Link, useRouter } from '@tanstack/react-router'
import { ReactNode } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { getOrderCounts } from '@/lib/api/orders'
import { useNavigationItems } from '@/hooks/useModules'

// Icon mapping from backend icon names to Lucide components
const ICON_COMPONENTS: Record<string, LucideIcon> = {
  'layout-dashboard': LayoutDashboard,
  'package': Package,
  'layers': Layers,
  'box': Box,
  'play': Play,
  'printer': Printer,
  'wrench': Wrench,
  'store': Store,
  'shopping-bag': ShoppingBag,
  'folder-open': FolderOpen,
  'brush': Brush,
  'palette': Palette,      // Yarn icon
  'pen': Pen,              // Needle icon
  'file-text': FileText,   // Pattern icon
  'folder-kanban': FolderKanban, // Project icon
  'settings': Settings,
  'help-circle': HelpCircle,
}

// Get icon component by name, with fallback
function getIconComponent(iconName: string): LucideIcon {
  return ICON_COMPONENTS[iconName] || Package
}

interface AppLayoutProps {
  children: ReactNode
}

export function AppLayout({ children }: AppLayoutProps) {
  const { user, logout } = useAuth()
  const router = useRouter()
  const currentPath = router.state.location.pathname
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Fetch order counts for badge
  const { data: orderCounts } = useQuery({
    queryKey: ['orderCounts'],
    queryFn: getOrderCounts,
    staleTime: 30000, // Refresh every 30 seconds
    refetchInterval: 60000, // Auto-refresh every minute
  })

  const pendingOrderCount = (orderCounts?.pending || 0) + (orderCounts?.processing || 0)

  // Fetch dynamic navigation items based on tenant modules
  const { navItems: dynamicNavItems, isLoading: modulesLoading } = useNavigationItems()

  // Fallback navigation items (used while loading or if modules fail)
  const fallbackNavItems = [
    { path: '/dashboard', label: 'Dashboard', icon: 'layout-dashboard', exact: true },
    { path: '/products', label: 'Products', icon: 'package' },
    { path: '/models', label: 'Models', icon: 'layers' },
    { path: '/designers', label: 'Designers', icon: 'brush' },
    { path: '/categories', label: 'Categories', icon: 'folder-open' },
    { path: '/production-runs', label: 'Runs', icon: 'play' },
    { path: '/inventory', label: 'Inventory', icon: 'box', exact: true },
    { path: '/printers', label: 'Printers', icon: 'printer' },
    { path: '/consumables', label: 'Consumables', icon: 'wrench' },
    { path: '/sales-channels', label: 'Channels', icon: 'store' },
    { path: '/orders', label: 'Orders', icon: 'shopping-bag' },
  ]

  // Use dynamic nav items if loaded, otherwise fallback
  const navItems = dynamicNavItems.length > 0
    ? dynamicNavItems.map(item => ({
        ...item,
        // Add order badge to orders route
        badge: item.path === '/orders' && pendingOrderCount > 0 ? pendingOrderCount : item.badge,
      }))
    : fallbackNavItems.map(item => ({
        ...item,
        badge: item.path === '/orders' && pendingOrderCount > 0 ? pendingOrderCount : undefined,
      }))

  const isActive = (path: string, exact?: boolean) => {
    if (exact) return currentPath === path
    return currentPath.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            {/* Logo */}
            <Link to="/dashboard" className="flex flex-col items-center gap-0.5 flex-shrink-0">
              <img src="/logo.svg" alt="Batchivo Logo" className="h-8 sm:h-10 md:h-12 w-auto object-contain" />
              <p className="hidden sm:block text-[10px] md:text-xs text-muted-foreground whitespace-nowrap">
                Production Tracking for Makers
              </p>
            </Link>

            {/* Desktop Navigation - hidden on mobile */}
            <nav className="hidden lg:flex items-center gap-1">
              {modulesLoading ? (
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              ) : (
                navItems.map((item) => {
                  const IconComponent = getIconComponent(item.icon)
                  return (
                    <Button
                      key={item.path}
                      variant={isActive(item.path, item.exact) ? 'default' : 'ghost'}
                      size="sm"
                      asChild
                      className="relative"
                    >
                      <Link to={item.path}>
                        <IconComponent className="w-4 h-4" />
                        <span className="ml-2">{item.label}</span>
                        {item.badge && (
                          <Badge
                            variant="destructive"
                            className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
                          >
                            {item.badge > 9 ? '9+' : item.badge}
                          </Badge>
                        )}
                      </Link>
                    </Button>
                  )
                })
              )}
            </nav>

            {/* Desktop User Info - hidden on mobile */}
            <div className="hidden lg:flex items-center gap-2 flex-shrink-0">
              {user?.is_platform_admin && (
                <Button variant="ghost" size="sm" asChild className="text-purple-600 hover:text-purple-700 hover:bg-purple-100">
                  <Link to="/platform">
                    <Shield className="w-4 h-4" />
                    <span className="ml-2">Admin</span>
                  </Link>
                </Button>
              )}
              <Button variant="ghost" size="sm" asChild>
                <Link to="/settings">
                  <Settings className="w-4 h-4" />
                  <span className="ml-2">Settings</span>
                </Link>
              </Button>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/help">
                  <HelpCircle className="w-4 h-4" />
                  <span className="ml-2">Help</span>
                </Link>
              </Button>
              <div className="flex items-center gap-2 text-sm">
                <User className="w-4 h-4" />
                <span className="text-muted-foreground max-w-[200px] truncate">{user?.email}</span>
              </div>
              <Button variant="outline" size="sm" onClick={() => logout()}>
                <LogOut className="w-4 h-4" />
                <span className="ml-2">Logout</span>
              </Button>
            </div>

            {/* Mobile Menu Button - visible on mobile/tablet */}
            <div className="lg:hidden flex items-center gap-2">
              <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-[280px] sm:w-[320px]">
                  <SheetHeader>
                    <SheetTitle>Menu</SheetTitle>
                  </SheetHeader>
                  <div className="flex flex-col gap-4 mt-6">
                    {/* Mobile Navigation */}
                    <nav className="flex flex-col gap-2">
                      {modulesLoading ? (
                        <div className="flex items-center justify-center py-4">
                          <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                        </div>
                      ) : (
                        navItems.map((item) => {
                          const IconComponent = getIconComponent(item.icon)
                          return (
                            <Button
                              key={item.path}
                              variant={isActive(item.path, item.exact) ? 'default' : 'ghost'}
                              className="justify-start"
                              asChild
                              onClick={() => setMobileMenuOpen(false)}
                            >
                              <Link to={item.path} className="flex items-center justify-between w-full">
                                <span className="flex items-center">
                                  <IconComponent className="w-4 h-4 mr-3" />
                                  {item.label}
                                </span>
                                {item.badge && (
                                  <Badge variant="destructive" className="ml-auto">
                                    {item.badge > 9 ? '9+' : item.badge}
                                  </Badge>
                                )}
                              </Link>
                            </Button>
                          )
                        })
                      )}
                    </nav>

                    {/* Mobile User Section */}
                    <div className="border-t pt-4 mt-2">
                      <div className="flex items-center gap-2 text-sm mb-4 px-2">
                        <User className="w-4 h-4 flex-shrink-0" />
                        <span className="text-muted-foreground truncate">{user?.email}</span>
                      </div>
                      {user?.is_platform_admin && (
                        <Button
                          variant="ghost"
                          className="w-full justify-start mb-2 text-purple-600"
                          asChild
                          onClick={() => setMobileMenuOpen(false)}
                        >
                          <Link to="/platform">
                            <Shield className="w-4 h-4 mr-3" />
                            Platform Admin
                          </Link>
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        className="w-full justify-start mb-2"
                        asChild
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        <Link to="/settings">
                          <Settings className="w-4 h-4 mr-3" />
                          Settings
                        </Link>
                      </Button>
                      <Button
                        variant="ghost"
                        className="w-full justify-start mb-2"
                        asChild
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        <Link to="/help">
                          <HelpCircle className="w-4 h-4 mr-3" />
                          Help & Guides
                        </Link>
                      </Button>
                      <Button
                        variant="outline"
                        className="w-full justify-start"
                        onClick={() => {
                          setMobileMenuOpen(false)
                          logout()
                        }}
                      >
                        <LogOut className="w-4 h-4 mr-3" />
                        Logout
                      </Button>
                    </div>
                  </div>
                </SheetContent>
              </Sheet>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="container mx-auto px-4 py-6 sm:py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t bg-card mt-16">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>Batchivo - Production Tracking for Makers</p>
          <p className="mt-1 hidden sm:block">Built with FastAPI, React, and shadcn/ui</p>
        </div>
      </footer>
    </div>
  )
}
