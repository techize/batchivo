/**
 * CategoryList Component
 *
 * Displays a list of categories with inline editing, reordering, and management.
 * Used on the Categories page for managing shop categories.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowDown,
  ArrowUp,
  FolderOpen,
  Loader2,
  Pencil,
  Plus,
  Search,
  Trash2,
} from 'lucide-react'

import {
  listCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  type Category,
  type CategoryCreateRequest,
  type CategoryUpdateRequest,
} from '@/lib/api/categories'
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

interface EditingCategory {
  id: string
  name: string
  slug: string
  description: string
}

export function CategoryList() {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [showInactive, setShowInactive] = useState(false)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [editingCategory, setEditingCategory] = useState<EditingCategory | null>(null)
  const [deletingCategory, setDeletingCategory] = useState<Category | null>(null)

  // Form state for create dialog
  const [newCategory, setNewCategory] = useState<CategoryCreateRequest>({
    name: '',
    slug: '',
    description: '',
  })

  // Fetch categories
  const { data, isLoading, error } = useQuery({
    queryKey: ['categories', { search, showInactive }],
    queryFn: () =>
      listCategories({
        search: search || undefined,
        is_active: showInactive ? undefined : true,
        limit: 100,
      }),
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setIsCreateDialogOpen(false)
      setNewCategory({ name: '', slug: '', description: '' })
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: CategoryUpdateRequest }) =>
      updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setEditingCategory(null)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['categories'] })
      setDeletingCategory(null)
    },
  })

  // Toggle active status
  const handleToggleActive = (category: Category) => {
    updateMutation.mutate({
      id: category.id,
      data: { is_active: !category.is_active },
    })
  }

  // Move category up/down in display order
  const handleMove = (category: Category, direction: 'up' | 'down') => {
    const categories = sortedCategories
    const currentIndex = categories.findIndex((c) => c.id === category.id)
    const targetIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1

    if (targetIndex < 0 || targetIndex >= categories.length) return

    const targetCategory = categories[targetIndex]

    // Swap display orders
    updateMutation.mutate({
      id: category.id,
      data: { display_order: targetCategory.display_order },
    })
    updateMutation.mutate({
      id: targetCategory.id,
      data: { display_order: category.display_order },
    })
  }

  // Generate slug from name
  const generateSlug = (name: string): string => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')
  }

  // Handle create form submit
  const handleCreate = () => {
    const slug = newCategory.slug || generateSlug(newCategory.name)
    createMutation.mutate({
      ...newCategory,
      slug,
    })
  }

  // Handle edit save
  const handleEditSave = () => {
    if (!editingCategory) return
    updateMutation.mutate({
      id: editingCategory.id,
      data: {
        name: editingCategory.name,
        slug: editingCategory.slug,
        description: editingCategory.description || null,
      },
    })
  }

  // Start editing a category
  const startEdit = (category: Category) => {
    setEditingCategory({
      id: category.id,
      name: category.name,
      slug: category.slug,
      description: category.description || '',
    })
  }

  const categories = data?.categories || []
  const sortedCategories = [...categories].sort((a, b) => a.display_order - b.display_order)
  const activeCount = categories.filter((c) => c.is_active).length

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">Error loading categories</p>
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
          <h2 className="text-2xl font-bold tracking-tight">Categories</h2>
          <p className="text-muted-foreground">
            {data?.total || 0} categories &bull; {activeCount} active &bull; Organize your shop
            products
          </p>
        </div>
        <Button onClick={() => setIsCreateDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          New Category
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
              Show All ({categories.length})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Results Card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <FolderOpen className="h-4 w-4" />
            Categories
            {data && (
              <Badge variant="secondary" className="ml-2">
                {data.total}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Drag to reorder or use arrows. Categories appear in this order on the shop.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* Loading State */}
          {isLoading && (
            <div className="flex h-[200px] items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-primary" />
              <span className="ml-3">Loading categories...</span>
            </div>
          )}

          {/* Empty State */}
          {!isLoading && sortedCategories.length === 0 && (
            <div className="flex h-[200px] items-center justify-center">
              <div className="text-center">
                <FolderOpen className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <p className="mt-4 text-muted-foreground">
                  {search
                    ? 'No categories match your search'
                    : 'No categories yet. Create your first category to organize products.'}
                </p>
                {!search && (
                  <Button onClick={() => setIsCreateDialogOpen(true)} className="mt-4">
                    <Plus className="mr-2 h-4 w-4" />
                    Create Category
                  </Button>
                )}
              </div>
            </div>
          )}

          {/* Card View - Mobile */}
          {!isLoading && sortedCategories.length > 0 && (
            <div className="lg:hidden space-y-3">
              {sortedCategories.map((category, index) => (
                <div
                  key={category.id}
                  className={cn(
                    'rounded-lg border p-4 space-y-3',
                    !category.is_active && 'opacity-60'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="font-medium">{category.name}</div>
                      <div className="text-sm text-muted-foreground">{category.slug}</div>
                    </div>
                    <div className="flex items-center gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleMove(category, 'up')}
                        disabled={index === 0}
                      >
                        <ArrowUp className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-8 w-8"
                        onClick={() => handleMove(category, 'down')}
                        disabled={index === sortedCategories.length - 1}
                      >
                        <ArrowDown className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {category.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {category.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between pt-2 border-t">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={category.is_active}
                        onCheckedChange={() => handleToggleActive(category)}
                      />
                      <span className="text-sm">
                        {category.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => startEdit(category)}>
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeletingCategory(category)}
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
          {!isLoading && sortedCategories.length > 0 && (
            <div className="hidden lg:block">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[60px]">Order</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Slug</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead className="w-[80px]">Products</TableHead>
                    <TableHead className="w-[100px]">Status</TableHead>
                    <TableHead className="w-[120px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedCategories.map((category, index) => (
                    <TableRow
                      key={category.id}
                      className={cn('group', !category.is_active && 'opacity-60')}
                    >
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => handleMove(category, 'up')}
                            disabled={index === 0}
                          >
                            <ArrowUp className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-6 w-6"
                            onClick={() => handleMove(category, 'down')}
                            disabled={index === sortedCategories.length - 1}
                          >
                            <ArrowDown className="h-3 w-3" />
                          </Button>
                        </div>
                      </TableCell>
                      <TableCell className="font-medium">{category.name}</TableCell>
                      <TableCell className="text-muted-foreground">{category.slug}</TableCell>
                      <TableCell className="max-w-[200px] truncate text-muted-foreground">
                        {category.description || '—'}
                      </TableCell>
                      <TableCell className="text-center tabular-nums">
                        {category.product_count ?? '—'}
                      </TableCell>
                      <TableCell>
                        <Switch
                          checked={category.is_active}
                          onCheckedChange={() => handleToggleActive(category)}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Button variant="ghost" size="sm" onClick={() => startEdit(category)}>
                            <Pencil className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setDeletingCategory(category)}
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

      {/* Create Category Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Category</DialogTitle>
            <DialogDescription>
              Add a new category to organize your shop products.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                placeholder="e.g., Dragons"
                value={newCategory.name}
                onChange={(e) =>
                  setNewCategory({
                    ...newCategory,
                    name: e.target.value,
                    slug: generateSlug(e.target.value),
                  })
                }
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="slug">Slug</Label>
              <Input
                id="slug"
                placeholder="e.g., dragons"
                value={newCategory.slug}
                onChange={(e) => setNewCategory({ ...newCategory, slug: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                URL-friendly identifier. Auto-generated from name.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                placeholder="Describe this category..."
                value={newCategory.description}
                onChange={(e) => setNewCategory({ ...newCategory, description: e.target.value })}
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
              disabled={!newCategory.name || createMutation.isPending}
            >
              {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Category
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Category Dialog */}
      <Dialog open={!!editingCategory} onOpenChange={(open) => !open && setEditingCategory(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Category</DialogTitle>
            <DialogDescription>Update the category details.</DialogDescription>
          </DialogHeader>
          {editingCategory && (
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Name</Label>
                <Input
                  id="edit-name"
                  value={editingCategory.name}
                  onChange={(e) =>
                    setEditingCategory({ ...editingCategory, name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-slug">Slug</Label>
                <Input
                  id="edit-slug"
                  value={editingCategory.slug}
                  onChange={(e) =>
                    setEditingCategory({ ...editingCategory, slug: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-description">Description</Label>
                <Textarea
                  id="edit-description"
                  value={editingCategory.description}
                  onChange={(e) =>
                    setEditingCategory({ ...editingCategory, description: e.target.value })
                  }
                  rows={3}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingCategory(null)}>
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
        open={!!deletingCategory}
        onOpenChange={(open) => !open && setDeletingCategory(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Category</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &ldquo;{deletingCategory?.name}&rdquo;? This action
              cannot be undone. Products in this category will be unassigned.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deletingCategory && deleteMutation.mutate(deletingCategory.id)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
