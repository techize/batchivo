/**
 * Categories Page
 *
 * List page for managing shop categories.
 */

import { AppLayout } from '@/components/layout/AppLayout'
import { CategoryList } from '@/components/categories/CategoryList'

export function Categories() {
  return (
    <AppLayout>
      <CategoryList />
    </AppLayout>
  )
}
