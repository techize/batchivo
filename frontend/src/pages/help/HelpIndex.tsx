/**
 * HelpIndex Page
 *
 * Public landing page for help documentation.
 * Shows all available guides organized by category.
 */

import { Link } from '@tanstack/react-router'
import {
  Book,
  Box,
  Package,
  Play,
  ShoppingBag,
  Store,
  Printer,
  Wrench,
  Brush,
  FolderOpen,
  ArrowRight,
  Home,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { guidesByCategory, type Guide } from '@/content/guides'

const categoryInfo = {
  core: {
    title: 'Core Guides',
    description: 'Essential guides for getting started with Nozzly',
    icon: Book,
  },
  sales: {
    title: 'Sales & Orders',
    description: 'Managing orders and sales channels',
    icon: ShoppingBag,
  },
  resources: {
    title: 'Resources',
    description: 'Managing printers and consumables',
    icon: Wrench,
  },
  organization: {
    title: 'Organization',
    description: 'Organizing your catalog',
    icon: FolderOpen,
  },
}

const guideIcons: Record<string, React.ElementType> = {
  overview: Book,
  'filament-management': Box,
  products: Package,
  'production-runs': Play,
  orders: ShoppingBag,
  'sales-channels': Store,
  printers: Printer,
  consumables: Wrench,
  designers: Brush,
  categories: FolderOpen,
}

function GuideCard({ guide }: { guide: Guide }) {
  const Icon = guideIcons[guide.slug] || Book

  return (
    <Link to={`/help/${guide.slug}`} className="block">
      <Card className="h-full hover:border-primary hover:shadow-md transition-all">
        <CardHeader className="pb-2">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Icon className="h-5 w-5 text-primary" />
            </div>
            <CardTitle className="text-lg">{guide.title}</CardTitle>
          </div>
        </CardHeader>
        <CardContent>
          <CardDescription className="text-sm">{guide.description}</CardDescription>
        </CardContent>
      </Card>
    </Link>
  )
}

function CategorySection({
  categoryKey,
  guides,
}: {
  categoryKey: keyof typeof categoryInfo
  guides: Guide[]
}) {
  const info = categoryInfo[categoryKey]
  const Icon = info.icon

  return (
    <section className="mb-10">
      <div className="flex items-center gap-3 mb-4">
        <Icon className="h-6 w-6 text-muted-foreground" />
        <div>
          <h2 className="text-xl font-semibold">{info.title}</h2>
          <p className="text-sm text-muted-foreground">{info.description}</p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {guides.map((guide) => (
          <GuideCard key={guide.slug} guide={guide} />
        ))}
      </div>
    </section>
  )
}

export function HelpIndex() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center gap-2">
              <img src="/logo.png?v=8" alt="Nozzly" className="h-8 w-auto" />
              <span className="text-lg font-semibold">Help Center</span>
            </Link>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" asChild>
                <Link to="/">
                  <Home className="h-4 w-4 mr-2" />
                  Home
                </Link>
              </Button>
              <Button variant="default" size="sm" asChild>
                <Link to="/login">Sign In</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Hero */}
      <div className="bg-gradient-to-b from-primary/5 to-background border-b">
        <div className="container mx-auto px-4 py-12 text-center">
          <h1 className="text-3xl md:text-4xl font-bold mb-4">Nozzly User Guide</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-6">
            Learn how to use Nozzly to manage your 3D printing business - from inventory tracking
            to production runs and order fulfillment.
          </p>
          <Button asChild>
            <Link to="/help/overview">
              Get Started
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      {/* Content */}
      <main className="container mx-auto px-4 py-10">
        <CategorySection categoryKey="core" guides={guidesByCategory.core} />
        <CategorySection categoryKey="sales" guides={guidesByCategory.sales} />
        <CategorySection categoryKey="resources" guides={guidesByCategory.resources} />
        <CategorySection categoryKey="organization" guides={guidesByCategory.organization} />
      </main>

      {/* Footer */}
      <footer className="border-t bg-card mt-10">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>Nozzly - 3D Print Business Management Platform</p>
          <p className="mt-1">
            <Link to="/" className="hover:underline">
              Back to Home
            </Link>
            {' | '}
            <Link to="/login" className="hover:underline">
              Sign In
            </Link>
          </p>
        </div>
      </footer>
    </div>
  )
}
