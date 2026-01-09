/**
 * HelpGuide Page
 *
 * Renders a single guide from markdown content.
 * Public page accessible without authentication.
 */

import { useParams, Link } from '@tanstack/react-router'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  ArrowLeft,
  ArrowRight,
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
  Home,
  Menu,
} from 'lucide-react'
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from '@/components/ui/sheet'
import { guides, getGuideBySlug } from '@/content/guides'

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

function Sidebar({ currentSlug }: { currentSlug: string }) {
  return (
    <nav className="space-y-1">
      {guides.map((guide) => {
        const Icon = guideIcons[guide.slug] || Book
        const isActive = guide.slug === currentSlug

        return (
          <Link
            key={guide.slug}
            to={`/help/${guide.slug}`}
            className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'hover:bg-muted text-muted-foreground hover:text-foreground'
            }`}
          >
            <Icon className="h-4 w-4" />
            {guide.title}
          </Link>
        )
      })}
    </nav>
  )
}

export function HelpGuide() {
  const { slug } = useParams({ from: '/help/$slug' })
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const guide = getGuideBySlug(slug)
  const currentIndex = guides.findIndex((g) => g.slug === slug)
  const prevGuide = currentIndex > 0 ? guides[currentIndex - 1] : null
  const nextGuide = currentIndex < guides.length - 1 ? guides[currentIndex + 1] : null

  if (!guide) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <Card className="p-8 text-center">
          <h1 className="text-2xl font-bold mb-4">Guide Not Found</h1>
          <p className="text-muted-foreground mb-4">
            The guide you're looking for doesn't exist.
          </p>
          <Button asChild>
            <Link to="/help">Back to Help Center</Link>
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card sticky top-0 z-50">
        <div className="container mx-auto px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Mobile menu */}
              <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="sm" className="lg:hidden">
                    <Menu className="h-5 w-5" />
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="w-72">
                  <SheetHeader>
                    <SheetTitle>Guides</SheetTitle>
                  </SheetHeader>
                  <div className="mt-4" onClick={() => setMobileMenuOpen(false)}>
                    <Sidebar currentSlug={slug} />
                  </div>
                </SheetContent>
              </Sheet>

              <Link to="/help" className="flex items-center gap-2">
                <img src="/logo.png?v=8" alt="Nozzly" className="h-8 w-auto" />
                <span className="text-lg font-semibold hidden sm:inline">Help Center</span>
              </Link>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" asChild>
                <Link to="/">
                  <Home className="h-4 w-4 sm:mr-2" />
                  <span className="hidden sm:inline">Home</span>
                </Link>
              </Button>
              <Button variant="default" size="sm" asChild>
                <Link to="/login">Sign In</Link>
              </Button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-4 py-6">
        <div className="flex gap-8">
          {/* Sidebar - Desktop */}
          <aside className="hidden lg:block w-64 flex-shrink-0">
            <div className="sticky top-20">
              <h3 className="font-semibold mb-3 text-sm text-muted-foreground uppercase tracking-wide">
                Guides
              </h3>
              <Sidebar currentSlug={slug} />
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 min-w-0 max-w-4xl">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-2 text-sm text-muted-foreground mb-6">
              <Link to="/help" className="hover:text-foreground">
                Help Center
              </Link>
              <span>/</span>
              <span className="text-foreground">{guide.title}</span>
            </nav>

            {/* Markdown content */}
            <article className="prose prose-neutral dark:prose-invert max-w-none prose-headings:scroll-mt-20 prose-h1:text-3xl prose-h2:text-2xl prose-h2:border-b prose-h2:pb-2 prose-h2:mt-10 prose-h3:text-xl prose-table:text-sm prose-th:bg-muted prose-th:px-4 prose-th:py-2 prose-td:px-4 prose-td:py-2 prose-code:bg-muted prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:before:content-none prose-code:after:content-none prose-pre:bg-muted">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{guide.content}</ReactMarkdown>
            </article>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-12 pt-6 border-t">
              {prevGuide ? (
                <Button variant="ghost" asChild>
                  <Link to={`/help/${prevGuide.slug}`} className="flex items-center gap-2">
                    <ArrowLeft className="h-4 w-4" />
                    <span className="hidden sm:inline">{prevGuide.title}</span>
                    <span className="sm:hidden">Previous</span>
                  </Link>
                </Button>
              ) : (
                <div />
              )}

              {nextGuide ? (
                <Button variant="ghost" asChild>
                  <Link to={`/help/${nextGuide.slug}`} className="flex items-center gap-2">
                    <span className="hidden sm:inline">{nextGuide.title}</span>
                    <span className="sm:hidden">Next</span>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </Button>
              ) : (
                <div />
              )}
            </div>
          </main>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t bg-card mt-16">
        <div className="container mx-auto px-4 py-6 text-center text-sm text-muted-foreground">
          <p>Nozzly - 3D Print Business Management Platform</p>
        </div>
      </footer>
    </div>
  )
}
