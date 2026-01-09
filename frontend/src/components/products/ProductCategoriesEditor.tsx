/**
 * ProductCategoriesEditor Component
 *
 * Editor for managing product category assignments.
 * Allows adding/removing categories for a product.
 */

import { useState } from 'react'
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query'
import { Loader2, Plus, X, Tags } from 'lucide-react'

import { listCategories, assignProductToCategory, removeProductFromCategory } from '@/lib/api/categories'
import { type ProductCategoryBrief } from '@/lib/api/products'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

interface ProductCategoriesEditorProps {
  productId: string
  categories: ProductCategoryBrief[]
}

export function ProductCategoriesEditor({ productId, categories }: ProductCategoriesEditorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()

  // Fetch all available categories
  const { data: allCategories, isLoading: isLoadingCategories } = useQuery({
    queryKey: ['categories'],
    queryFn: () => listCategories({ is_active: true, limit: 100 }),
  })

  // Add category mutation
  const addMutation = useMutation({
    mutationFn: (categoryId: string) => assignProductToCategory(categoryId, productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
      setIsOpen(false)
    },
  })

  // Remove category mutation
  const removeMutation = useMutation({
    mutationFn: (categoryId: string) => removeProductFromCategory(categoryId, productId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['product', productId] })
    },
  })

  // Filter out already assigned categories
  const assignedIds = new Set(categories.map((c) => c.id))
  const availableCategories = allCategories?.categories.filter((c) => !assignedIds.has(c.id)) || []

  const handleAddCategory = (categoryId: string) => {
    addMutation.mutate(categoryId)
  }

  const handleRemoveCategory = (categoryId: string) => {
    removeMutation.mutate(categoryId)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Tags className="h-5 w-5" />
          Categories
        </CardTitle>
        <CardDescription>
          Assign this product to shop categories for organization and filtering
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Current Categories */}
        <div className="flex flex-wrap gap-2">
          {categories.length === 0 ? (
            <p className="text-sm text-muted-foreground">No categories assigned</p>
          ) : (
            categories.map((category) => (
              <Badge
                key={category.id}
                variant="secondary"
                className="flex items-center gap-1 pr-1"
              >
                {category.name}
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground rounded-full"
                  onClick={() => handleRemoveCategory(category.id)}
                  disabled={removeMutation.isPending}
                >
                  {removeMutation.isPending && removeMutation.variables === category.id ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <X className="h-3 w-3" />
                  )}
                </Button>
              </Badge>
            ))
          )}
        </div>

        {/* Add Category Button */}
        <Dialog open={isOpen} onOpenChange={setIsOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="gap-2">
              <Plus className="h-4 w-4" />
              Add Category
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-[425px]">
            <DialogHeader>
              <DialogTitle>Add to Category</DialogTitle>
              <DialogDescription>
                Select a category to add this product to
              </DialogDescription>
            </DialogHeader>
            {isLoadingCategories ? (
              <div className="flex justify-center p-4">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            ) : availableCategories.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                Product is already in all available categories
              </p>
            ) : (
              <Command>
                <CommandInput placeholder="Search categories..." />
                <CommandList>
                  <CommandEmpty>No categories found.</CommandEmpty>
                  <CommandGroup>
                    {availableCategories.map((category) => (
                      <CommandItem
                        key={category.id}
                        value={category.name}
                        onSelect={() => handleAddCategory(category.id)}
                        disabled={addMutation.isPending}
                      >
                        {addMutation.isPending && addMutation.variables === category.id ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : null}
                        {category.name}
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </CommandList>
              </Command>
            )}
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  )
}
