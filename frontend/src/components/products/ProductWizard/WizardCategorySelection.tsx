/**
 * WizardCategorySelection Component
 *
 * Step 3: Category selection for the product wizard.
 * Multi-select categories with search.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, Check, Loader2, Tags } from 'lucide-react'

import { listCategories } from '@/lib/api/categories'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Checkbox } from '@/components/ui/checkbox'
import { cn } from '@/lib/utils'

import type { SelectedCategory } from './index'

interface WizardCategorySelectionProps {
  selectedCategories: SelectedCategory[]
  onCategoriesChange: (categories: SelectedCategory[]) => void
}

export function WizardCategorySelection({
  selectedCategories,
  onCategoriesChange,
}: WizardCategorySelectionProps) {
  const [searchQuery, setSearchQuery] = useState('')

  // Fetch categories
  const { data: categoriesData, isLoading } = useQuery({
    queryKey: ['categories', { is_active: true, limit: 100 }],
    queryFn: () => listCategories({ is_active: true, limit: 100 }),
  })

  const categories = categoriesData?.categories || []

  // Filter categories by search
  const filteredCategories = searchQuery
    ? categories.filter((c) =>
        c.name.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : categories

  // Check if a category is selected
  const isSelected = (categoryId: string) =>
    selectedCategories.some((c) => c.id === categoryId)

  // Toggle category selection
  const toggleCategory = (category: { id: string; name: string }) => {
    if (isSelected(category.id)) {
      onCategoriesChange(selectedCategories.filter((c) => c.id !== category.id))
    } else {
      onCategoriesChange([...selectedCategories, { id: category.id, name: category.name }])
    }
  }

  return (
    <div className="space-y-4">
      {/* Selected Categories Summary */}
      {selectedCategories.length > 0 && (
        <Card className="bg-primary/5 border-primary/20">
          <CardContent className="py-3">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium">
                Selected Categories ({selectedCategories.length})
              </span>
              <button
                onClick={() => onCategoriesChange([])}
                className="text-sm text-muted-foreground hover:text-destructive"
              >
                Clear all
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {selectedCategories.map((category) => (
                <Badge
                  key={category.id}
                  variant="secondary"
                  className="cursor-pointer hover:bg-secondary/80"
                  onClick={() => toggleCategory(category)}
                >
                  {category.name}
                  <span className="ml-1 text-muted-foreground">×</span>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search categories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Categories List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredCategories.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <Tags className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>No categories found</p>
          {searchQuery && (
            <p className="text-sm mt-1">Try a different search term</p>
          )}
        </div>
      ) : (
        <ScrollArea className="h-[350px]">
          <div className="space-y-2 pr-4">
            {filteredCategories.map((category) => {
              const selected = isSelected(category.id)

              return (
                <Card
                  key={category.id}
                  className={cn(
                    'cursor-pointer transition-all hover:shadow-sm',
                    selected && 'ring-2 ring-primary bg-primary/5'
                  )}
                  onClick={() => toggleCategory(category)}
                >
                  <CardContent className="p-3">
                    <div className="flex items-center gap-3">
                      <Checkbox
                        checked={selected}
                        onCheckedChange={() => toggleCategory(category)}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-sm">{category.name}</h4>
                          {selected && (
                            <Check className="h-4 w-4 text-primary flex-shrink-0" />
                          )}
                        </div>
                        {category.description && (
                          <p className="text-xs text-muted-foreground truncate mt-0.5">
                            {category.description}
                          </p>
                        )}
                      </div>
                      {category.product_count !== undefined && (
                        <Badge variant="outline" className="flex-shrink-0">
                          {category.product_count} products
                        </Badge>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </ScrollArea>
      )}

      {/* Help text */}
      <p className="text-sm text-muted-foreground text-center">
        Categories help organize your products in the shop. This step is optional.
      </p>
    </div>
  )
}
