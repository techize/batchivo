/**
 * Platform Admin Layout
 *
 * Layout wrapper for platform administration pages.
 * Includes platform-specific navigation and impersonation banner.
 */

import { ReactNode } from 'react'
import { Link, useRouter } from '@tanstack/react-router'
import { useAuth } from '@/contexts/AuthContext'
import { useImpersonation } from '@/hooks/useImpersonation'
import { Button } from '@/components/ui/button'
import {
  LogOut,
  User,
  Menu,
  Building2,
  ClipboardList,
  LayoutDashboard,
  ArrowLeft,
  Shield,
} from 'lucide-react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { useState } from 'react'
import { ImpersonationBanner } from './ImpersonationBanner'

interface PlatformLayoutProps {
  children: ReactNode
}

const platformNavItems = [
  { path: '/platform', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { path: '/platform/tenants', label: 'Tenants', icon: Building2 },
  { path: '/platform/audit', label: 'Audit Logs', icon: ClipboardList },
]

export function PlatformLayout({ children }: PlatformLayoutProps) {
  const { user, logout } = useAuth()
  const router = useRouter()
  const currentPath = router.state.location.pathname
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const { isImpersonating } = useImpersonation()

  const isActive = (path: string, exact?: boolean) => {
    if (exact) return currentPath === path
    return currentPath.startsWith(path)
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Impersonation Banner */}
      {isImpersonating && <ImpersonationBanner />}

      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between gap-2">
            {/* Logo and Platform Badge */}
            <div className="flex items-center gap-3">
              <Link to="/dashboard" className="flex flex-col items-center gap-0.5 flex-shrink-0">
                <img src="/logo.png?v=8" alt="Nozzly Logo" className="h-8 sm:h-10 md:h-12 w-auto object-contain" />
              </Link>
              <div className="hidden sm:flex items-center gap-2 px-2 py-1 bg-purple-100 dark:bg-purple-900 rounded-md">
                <Shield className="h-4 w-4 text-purple-600 dark:text-purple-300" />
                <span className="text-sm font-medium text-purple-600 dark:text-purple-300">Platform Admin</span>
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden lg:flex items-center gap-1">
              {platformNavItems.map((item) => {
                const Icon = item.icon
                return (
                  <Button
                    key={item.path}
                    variant={isActive(item.path, item.exact) ? 'default' : 'ghost'}
                    size="sm"
                    asChild
                  >
                    <Link to={item.path}>
                      <Icon className="w-4 h-4" />
                      <span className="ml-2">{item.label}</span>
                    </Link>
                  </Button>
                )
              })}
            </nav>

            {/* Desktop User Info */}
            <div className="hidden lg:flex items-center gap-2 flex-shrink-0">
              <Button variant="ghost" size="sm" asChild>
                <Link to="/dashboard">
                  <ArrowLeft className="w-4 h-4" />
                  <span className="ml-2">Back to App</span>
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

            {/* Mobile Menu Button */}
            <div className="lg:hidden flex items-center gap-2">
              <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                <SheetTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="right" className="w-[280px] sm:w-[320px]">
                  <SheetHeader>
                    <SheetTitle className="flex items-center gap-2">
                      <Shield className="h-5 w-5 text-purple-600" />
                      Platform Admin
                    </SheetTitle>
                  </SheetHeader>
                  <div className="flex flex-col gap-4 mt-6">
                    {/* Mobile Navigation */}
                    <nav className="flex flex-col gap-2">
                      {platformNavItems.map((item) => {
                        const Icon = item.icon
                        return (
                          <Button
                            key={item.path}
                            variant={isActive(item.path, item.exact) ? 'default' : 'ghost'}
                            className="justify-start"
                            asChild
                            onClick={() => setMobileMenuOpen(false)}
                          >
                            <Link to={item.path}>
                              <Icon className="w-4 h-4 mr-3" />
                              {item.label}
                            </Link>
                          </Button>
                        )
                      })}
                    </nav>

                    {/* Mobile User Section */}
                    <div className="border-t pt-4 mt-2">
                      <div className="flex items-center gap-2 text-sm mb-4 px-2">
                        <User className="w-4 h-4 flex-shrink-0" />
                        <span className="text-muted-foreground truncate">{user?.email}</span>
                      </div>
                      <Button
                        variant="ghost"
                        className="w-full justify-start mb-2"
                        asChild
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        <Link to="/dashboard">
                          <ArrowLeft className="w-4 h-4 mr-3" />
                          Back to App
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
          <p>Nozzly Platform Administration</p>
        </div>
      </footer>
    </div>
  )
}
