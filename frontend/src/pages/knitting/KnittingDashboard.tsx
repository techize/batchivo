/**
 * Knitting Dashboard Page
 *
 * Overview of knitting projects, yarn inventory, and analytics.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Plus, Palette, Pen, FileText, FolderKanban, TrendingUp, Clock, DollarSign } from 'lucide-react'
import { Link } from '@tanstack/react-router'

export function KnittingDashboard() {
  return (
    <AppLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knitting Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Overview of your yarn stash, projects, and crafting analytics
          </p>
        </div>

        {/* Quick Stats */}
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Yarn Skeins</CardTitle>
              <Palette className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-muted-foreground">in your stash</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Active Projects</CardTitle>
              <FolderKanban className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0</div>
              <p className="text-xs text-muted-foreground">works in progress</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Hours This Month</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">0h</div>
              <p className="text-xs text-muted-foreground">time logged</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Stash Value</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">$0</div>
              <p className="text-xs text-muted-foreground">total inventory</p>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="hover:bg-muted/50 transition-colors">
            <Link to="/yarn">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Palette className="w-5 h-5" />
                  Yarn Stash
                </CardTitle>
                <CardDescription>
                  Manage your yarn inventory
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" size="sm" className="w-full">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Yarn
                </Button>
              </CardContent>
            </Link>
          </Card>

          <Card className="hover:bg-muted/50 transition-colors">
            <Link to="/needles">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Pen className="w-5 h-5" />
                  Needles & Hooks
                </CardTitle>
                <CardDescription>
                  Track your tools collection
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" size="sm" className="w-full">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Needle
                </Button>
              </CardContent>
            </Link>
          </Card>

          <Card className="hover:bg-muted/50 transition-colors">
            <Link to="/patterns">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FileText className="w-5 h-5" />
                  Patterns
                </CardTitle>
                <CardDescription>
                  Browse your pattern library
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" size="sm" className="w-full">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Pattern
                </Button>
              </CardContent>
            </Link>
          </Card>

          <Card className="hover:bg-muted/50 transition-colors">
            <Link to="/projects">
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FolderKanban className="w-5 h-5" />
                  Projects
                </CardTitle>
                <CardDescription>
                  Track your work in progress
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button variant="outline" size="sm" className="w-full">
                  <Plus className="w-4 h-4 mr-2" />
                  Start Project
                </Button>
              </CardContent>
            </Link>
          </Card>
        </div>

        {/* Works in Progress */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Works in Progress
            </CardTitle>
            <CardDescription>
              Your current knitting and crochet projects
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <FolderKanban className="w-12 h-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No active projects</h3>
              <p className="text-muted-foreground mb-4 max-w-sm">
                Start a new project to track your progress, log time, and manage materials.
              </p>
              <Button asChild>
                <Link to="/projects">
                  <Plus className="w-4 h-4 mr-2" />
                  Start Your First Project
                </Link>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </AppLayout>
  )
}
