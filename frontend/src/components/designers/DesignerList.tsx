/**
 * DesignerList Component
 *
 * Displays a list of licensed designers with management capabilities.
 * Used on the Designers page for managing designer relationships.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Brush,
  ExternalLink,
  Loader2,
  Pencil,
  Plus,
  Search,
  Trash2,
} from 'lucide-react'

import {
  listDesigners,
  createDesigner,
  updateDesigner,
  deleteDesigner,
  type Designer,
  type DesignerCreateRequest,
  type DesignerUpdateRequest,
} from '@/lib/api/designers'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

interface EditingDesigner {
  id: string
  name: string
  slug: string
  description: string
  logo_url: string
  website_url: string
  membership_cost: string
  membership_renewal_date: string
  notes: string
}

export function DesignerList() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editingDesigner, setEditingDesigner] = useState<EditingDesigner | null>(null)
  const [deletingDesigner, setDeletingDesigner] = useState<Designer | null>(null)

  // Form state for create dialog
  const [newDesigner, setNewDesigner] = useState<DesignerCreateRequest>({
    name: '',
    description: '',
    website_url: '',
  })

  // Fetch designers
  const { data, isLoading, error } = useQuery({
    queryKey: ['designers', { search, showInactive }],
    queryFn: () =>
      listDesigners({
        search: search || undefined,
        include_inactive: showInactive,
        limit: 100,
      }),
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createDesigner,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designers'] })
      setIsCreateDialogOpen(false)
      setNewDesigner({ name: '', description: '', website_url: '' })
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: DesignerUpdateRequest }) =>
      updateDesigner(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designers'] })
      setEditingDesigner(null)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteDesigner,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['designers'] })
      setDeletingDesigner(null)
    },
  })

  // Toggle active status
  const handleToggleActive = (designer: Designer) => {
    updateMutation.mutate({
      id: designer.id,
      data: { is_active: !designer.is_active },
    })
  }

  // Handle create form submit
  const handleCreate = () => {
    createMutation.mutate(newDesigner)
  }

  // Handle edit save
  const handleEditSave = () => {
    if (!editingDesigner) return
    updateMutation.mutate({
      id: editingDesigner.id,
      data: {
        name: editingDesigner.name,
        slug: editingDesigner.slug,
        description: editingDesigner.description || null,
        logo_url: editingDesigner.logo_url || null,
        website_url: editingDesigner.website_url || null,
        membership_cost: editingDesigner.membership_cost ? parseFloat(editingDesigner.membership_cost) : null,
        membership_renewal_date: editingDesigner.membership_renewal_date || null,
        notes: editingDesigner.notes || null,
      },
    })
  }

  // Start editing a designer
  const startEdit = (designer: Designer) => {
    setEditingDesigner({
      id: designer.id,
      name: designer.name,
      slug: designer.slug,
      description: designer.description || '',
      logo_url: designer.logo_url || '',
      website_url: designer.website_url || '',
      membership_cost: designer.membership_cost?.toString() || '',
      membership_renewal_date: designer.membership_renewal_date || '',
      notes: designer.notes || '',
    })
  }

  const designers = data?.designers || []
  const activeCount = designers.filter((d) => d.is_active).length

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading designers</p>
          <p className="text-sm text-muted-foreground">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Designers</h2>
          <p className="text-muted-foreground">
            {data?.total || 0} designers &bull; {activeCount} active &bull; Licensed design creators
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add Designer
        </Button>
      </div>

      {/* Filters Card */}
      <Card>
        <CardContent className="pt-6 space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by name..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>

          {/* Filters */}
          <div className="flex flex-wrap gap-2">
            <Button
              variant={!showInactive ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowInactive(false)}
              className="h-8"
            >
              <span className="mr-1.5 h-2 w-2 rounded-full bg-green-500" />
              Active ({activeCount})
            </Button>
            <Button
              variant={showInactive ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowInactive(true)}
              className="h-8"
            >
              Show All ({designers.length})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Brush className="h-4 w-4" />
            Licensed Designers
            {data && (
              <Badge variant="secondary" className="ml-2">
                {data.total}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Designers whose 3D models you are licensed to print and sell.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Loading State */}
          {isLoading && (
            <div className="flex h-[200px] items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-3">Loading designers...</span>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && designers.length === 0 && (
            <div className="flex h-[200px] items-center justify-center">
              <div className="text-center">
                <Brush className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">
                  {search
                    ? 'No designers match your search'
                    : 'No designers yet. Add your first licensed designer.'}
                </p>
                {!search && (
                  <Button onClick={() => setIsCreateDialogOpen(true)} className="mt-4">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Designer
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Card View - Mobile */}
          {!isLoading && designers.length > 0 && (
            <div className="lg:hidden space-y-3">
              {designers.map((designer) => (
                <div
                  key={designer.id}
                  className={cn(
                    'rounded-lg border p-4 space-y-3',
                    !designer.is_active && 'opacity-60'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="font-medium">{designer.name}</div>
                      <div className="text-sm text-muted-foreground">{designer.slug}</div>
                    </div>
                    {designer.website_url && (
                      <a
                        href={designer.website_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    )}
                  </div>

                  {designer.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {designer.description}
                    </p>
                  )}

                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{designer.product_count} products</span>
                    {designer.membership_renewal_date && (
                      <span>Renews: {new Date(designer.membership_renewal_date).toLocaleDateString()}</span>
                    )}
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={designer.is_active}
                        onCheckedChange={() => handleToggleActive(designer)}
                      />
                      <span className="text-sm">
                        {designer.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => startEdit(designer)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeletingDesigner(designer)}
                        disabled={designer.product_count > 0}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Table View - Desktop */}
          {!isLoading && designers.length > 0 && (
            <div className="hidden lg:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Website</TableHead>
                    <TableHead className="w-[80px]">Products</TableHead>
                    <TableHead>Membership</TableHead>
                    <TableHead>Renewal</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[120px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {designers.map((designer) => (
                    <TableRow
                      key={designer.id}
                      className={cn('group', !designer.is_active && 'opacity-60')}
                    >
                      <TableCell>
                        <div>
                          <div className="font-medium">{designer.name}</div>
                          <div className="text-sm text-muted-foreground">{designer.slug}</div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {designer.website_url ? (
                          <a
                            href={designer.website_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline flex items-center gap-1"
                          >
                            Visit <ExternalLink className="h-3 w-3" />
                          </a>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center tabular-nums">
                        {designer.product_count}
                      </TableCell>
                      <TableCell>
                        {designer.membership_cost ? (
                          <span className="tabular-nums">&pound;{designer.membership_cost.toFixed(2)}</span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {designer.membership_renewal_date ? (
                          <span className={cn(
                            new Date(designer.membership_renewal_date) < new Date() && 'text-destructive font-medium'
                          )}>
                            {new Date(designer.membership_renewal_date).toLocaleDateString()}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={designer.is_active}
                          onCheckedChange={() => handleToggleActive(designer)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button variant="ghost" size="sm" onClick={() => startEdit(designer)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeletingDesigner(designer)}
                            disabled={designer.product_count > 0}
                            title={designer.product_count > 0 ? 'Cannot delete designer with products' : undefined}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Designer Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Designer</DialogTitle>
            <DialogDescription>
              Add a new licensed designer whose designs you can print and sell.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="e.g., PrintyJay"
                value={newDesigner.name}
                onChange={(e) => setNewDesigner({ ...newDesigner, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="website">Website URL</Label>
              <Input
                id="website"
                placeholder="https://..."
                value={newDesigner.website_url}
                onChange={(e) => setNewDesigner({ ...newDesigner, website_url: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="About this designer..."
                value={newDesigner.description}
                onChange={(e) => setNewDesigner({ ...newDesigner, description: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleCreate}
              disabled={!newDesigner.name || createMutation.isPending}
            >
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Add Designer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Designer Dialog */}
      <Dialog open={!!editingDesigner} onOpenChange={(open) => !open && setEditingDesigner(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Designer</DialogTitle>
            <DialogDescription>Update designer details and membership info.</DialogDescription>
          </DialogHeader>
          {editingDesigner && (
            <div className="space-y-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-name">Name</Label>
                  <Input
                    id="edit-name"
                    value={editingDesigner.name}
                    onChange={(e) =>
                      setEditingDesigner({ ...editingDesigner, name: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-slug">Slug</Label>
                  <Input
                    id="edit-slug"
                    value={editingDesigner.slug}
                    onChange={(e) =>
                      setEditingDesigner({ ...editingDesigner, slug: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-logo">Logo URL</Label>
                <Input
                  id="edit-logo"
                  placeholder="/images/designers/designer-name.png"
                  value={editingDesigner.logo_url}
                  onChange={(e) =>
                    setEditingDesigner({ ...editingDesigner, logo_url: e.target.value })
                  }
                />
                <p className="text-xs text-muted-foreground">
                  Path to logo image (e.g., /images/designers/printyjay.png)
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-website">Website URL</Label>
                <Input
                  id="edit-website"
                  value={editingDesigner.website_url}
                  onChange={(e) =>
                    setEditingDesigner({ ...editingDesigner, website_url: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">Description</Label>
                <Textarea
                  id="edit-description"
                  value={editingDesigner.description}
                  onChange={(e) =>
                    setEditingDesigner({ ...editingDesigner, description: e.target.value })
                  }
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-cost">Membership Cost (&pound;)</Label>
                  <Input
                    id="edit-cost"
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={editingDesigner.membership_cost}
                    onChange={(e) =>
                      setEditingDesigner({ ...editingDesigner, membership_cost: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-renewal">Renewal Date</Label>
                  <Input
                    id="edit-renewal"
                    type="date"
                    value={editingDesigner.membership_renewal_date}
                    onChange={(e) =>
                      setEditingDesigner({ ...editingDesigner, membership_renewal_date: e.target.value })
                    }
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-notes">Internal Notes</Label>
                <Textarea
                  id="edit-notes"
                  placeholder="Notes about membership, login details, etc..."
                  value={editingDesigner.notes}
                  onChange={(e) =>
                    setEditingDesigner({ ...editingDesigner, notes: e.target.value })
                  }
                  rows={2}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingDesigner(null)}>
              Cancel
            </Button>
            <Button onClick={handleEditSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={!!deletingDesigner}
        onOpenChange={(open) => !open && setDeletingDesigner(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Designer</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &ldquo;{deletingDesigner?.name}&rdquo;? This action
              cannot be undone.
              {deletingDesigner && deletingDesigner.product_count > 0 && (
                <span className="block mt-2 text-destructive font-medium">
                  This designer has {deletingDesigner.product_count} products. Remove them first.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingDesigner && deleteMutation.mutate(deletingDesigner.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deletingDesigner ? deletingDesigner.product_count > 0 : false}
            >
              {deleteMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
