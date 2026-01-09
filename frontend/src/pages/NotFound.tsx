/**
 * Not Found Page (404)
 *
 * Displayed when accessing a route that doesn't exist or
 * a module the tenant doesn't have access to.
 */

import { Link } from '@tanstack/react-router'
import { AppLayout } from '@/components/layout/AppLayout'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Home, ArrowLeft, AlertCircle } from 'lucide-react'

interface NotFoundProps {
  title?: string
  message?: string
  showLayout?: boolean
}

export function NotFound({
  title = 'Page Not Found',
  message = "The page you're looking for doesn't exist or you don't have access to it.",
  showLayout = true,
}: NotFoundProps) {
  const content = (
    <div className="flex items-center justify-center min-h-[60vh]">
      <Card className="max-w-md w-full">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center text-center space-y-4">
            <div className="rounded-full bg-destructive/10 p-4">
              <AlertCircle className="w-12 h-12 text-destructive" />
            </div>
            <div className="space-y-2">
              <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
              <p className="text-muted-foreground">{message}</p>
            </div>
            <div className="flex gap-3 pt-4">
              <Button variant="outline" asChild>
                <Link to="/" onClick={() => window.history.back()}>
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Go Back
                </Link>
              </Button>
              <Button asChild>
                <Link to="/dashboard">
                  <Home className="w-4 h-4 mr-2" />
                  Dashboard
                </Link>
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )

  if (showLayout) {
    return <AppLayout>{content}</AppLayout>
  }

  return content
}
