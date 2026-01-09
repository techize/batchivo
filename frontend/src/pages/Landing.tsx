/**
 * Landing page with hero section and auth CTAs
 */

import { useNavigate } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Package, DollarSign, TrendingUp, BarChart3, HelpCircle } from 'lucide-react'

export function Landing() {
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      {/* Header */}
      <header className="border-b bg-card/50 backdrop-blur">
        <div className="container mx-auto px-4 py-3 md:py-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col items-center gap-1 flex-shrink-0">
              <img src="/logo.png?v=8" alt="Nozzly" className="h-10 md:h-12 w-auto object-contain" />
              <p className="text-xs text-muted-foreground whitespace-nowrap">
                3D Print Management
              </p>
            </div>
            <div className="flex gap-2 flex-shrink-0">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => navigate({ to: '/help' })}
              >
                <HelpCircle className="h-4 w-4 sm:mr-1" />
                <span className="hidden sm:inline">Help</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => navigate({ to: '/login' })}
              >
                <span className="hidden sm:inline">Login</span>
                <span className="sm:hidden">Sign In</span>
              </Button>
              <Button size="sm" onClick={() => navigate({ to: '/signup' })}>
                <span className="hidden sm:inline">Get Started</span>
                <span className="sm:hidden">Sign Up</span>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="container mx-auto px-4 py-8 md:py-16 lg:py-24">
        <div className="text-center max-w-3xl mx-auto">
          <h2 className="text-3xl md:text-4xl lg:text-6xl font-bold text-foreground mb-4 md:mb-6">
            Manage Your 3D Printing
          </h2>
          <p className="text-base md:text-lg lg:text-xl text-muted-foreground mb-6 md:mb-8">
            Track inventory, calculate costs, optimize pricing, and streamline your 3D
            printing workflow with ease.
          </p>
          <div className="flex flex-col sm:flex-row gap-3 md:gap-4 justify-center">
            <Button size="lg" onClick={() => navigate({ to: '/signup' })} className="w-full sm:w-auto">
              Sign Up
            </Button>
            <Button
              size="lg"
              variant="outline"
              onClick={() => navigate({ to: '/login' })}
              className="w-full sm:w-auto"
            >
              Sign In
            </Button>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="container mx-auto px-4 py-16">
        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Card>
            <CardHeader>
              <Package className="w-10 h-10 mb-2 text-primary" />
              <CardTitle>Inventory Management</CardTitle>
              <CardDescription>
                Track filament spools, materials, and components with real-time
                weight updates
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <DollarSign className="w-10 h-10 mb-2 text-primary" />
              <CardTitle>Cost Tracking</CardTitle>
              <CardDescription>
                Calculate accurate costs including materials, labor, and overhead
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <TrendingUp className="w-10 h-10 mb-2 text-primary" />
              <CardTitle>Smart Pricing</CardTitle>
              <CardDescription>
                Optimize prices across multiple marketplaces with automated fee
                calculations
              </CardDescription>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader>
              <BarChart3 className="w-10 h-10 mb-2 text-primary" />
              <CardTitle>Analytics</CardTitle>
              <CardDescription>
                Track sales, profit margins, and inventory turnover with detailed
                reports
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </section>

      {/* Benefits Section */}
      <section className="container mx-auto px-4 py-16 bg-muted/50 rounded-lg">
        <div className="max-w-3xl mx-auto text-center">
          <h3 className="text-3xl font-bold mb-6">Why Choose Nozzly?</h3>
          <div className="grid md:grid-cols-3 gap-6 text-left">
            <div>
              <h4 className="font-semibold mb-2">Made for Makers</h4>
              <p className="text-sm text-muted-foreground">
                Built by 3D printing enthusiasts who understand your workflow
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Multi-Tenant Support</h4>
              <p className="text-sm text-muted-foreground">
                Manage multiple projects or clients from one account
              </p>
            </div>
            <div>
              <h4 className="font-semibold mb-2">Open Source</h4>
              <p className="text-sm text-muted-foreground">
                Self-host or use our managed service. Your data, your choice.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t bg-card/50 backdrop-blur mt-16">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>Built with FastAPI, React, and shadcn/ui</p>
          <p className="mt-1">© 2025 Nozzly - Open Source 3D Print Management</p>
        </div>
      </footer>
    </div>
  )
}
