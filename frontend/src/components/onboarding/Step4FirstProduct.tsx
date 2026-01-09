/**
 * Step 4: First Product (Optional)
 * Create your first product or skip to finish onboarding
 */

import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Loader2, Package, ArrowRight } from 'lucide-react'

const step4Schema = z.object({
  skip: z.boolean().default(false),
  product_name: z.string().optional(),
  product_description: z.string().optional(),
  product_price: z.number().min(0).optional(),
})

type Step4FormData = z.infer<typeof step4Schema>

interface Step4FirstProductProps {
  initialData?: {
    product_name?: string
    product_description?: string
    product_price?: number
  }
  onSubmit: (data: Step4FormData) => void
  onBack: () => void
  isLoading?: boolean
  currency?: string
}

export function Step4FirstProduct({
  initialData,
  onSubmit,
  onBack,
  isLoading,
  currency = 'GBP',
}: Step4FirstProductProps) {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
  } = useForm<Step4FormData>({
    resolver: zodResolver(step4Schema),
    defaultValues: {
      skip: false,
      product_name: initialData?.product_name || '',
      product_description: initialData?.product_description || '',
      product_price: initialData?.product_price,
    },
  })

  const productName = watch('product_name')

  function handleSkip() {
    onSubmit({ skip: true })
  }

  function handleCreateProduct(data: Step4FormData) {
    if (!data.product_name) {
      return // Form validation should catch this, but just in case
    }
    onSubmit({ ...data, skip: false })
  }

  const currencySymbol = currency === 'GBP' ? '£' : currency === 'EUR' ? '€' : '$'

  return (
    <div className="space-y-6">
      <div className="text-center mb-6">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
          <Package className="h-6 w-6 text-primary" />
        </div>
        <p className="text-muted-foreground">
          Add your first product to get started, or skip this step and add products later.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Create Your First Product</CardTitle>
          <CardDescription>
            This is optional - you can add products anytime from your dashboard.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(handleCreateProduct)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="product_name">Product Name</Label>
              <Input
                id="product_name"
                placeholder="e.g., Custom Phone Case"
                {...register('product_name')}
                disabled={isLoading}
              />
              {errors.product_name && (
                <p className="text-sm text-destructive">{errors.product_name.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="product_description">Description</Label>
              <Textarea
                id="product_description"
                placeholder="Describe your product..."
                rows={3}
                {...register('product_description')}
                disabled={isLoading}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="product_price">Price ({currencySymbol})</Label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                  {currencySymbol}
                </span>
                <Input
                  id="product_price"
                  type="number"
                  step="0.01"
                  min="0"
                  placeholder="0.00"
                  className="pl-7"
                  {...register('product_price', { valueAsNumber: true })}
                  disabled={isLoading}
                />
              </div>
              {errors.product_price && (
                <p className="text-sm text-destructive">{errors.product_price.message}</p>
              )}
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={isLoading || !productName}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <Package className="mr-2 h-4 w-4" />
                  Create Product & Finish
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="relative">
        <div className="absolute inset-0 flex items-center">
          <span className="w-full border-t" />
        </div>
        <div className="relative flex justify-center text-xs uppercase">
          <span className="bg-background px-2 text-muted-foreground">or</span>
        </div>
      </div>

      <Button
        variant="outline"
        className="w-full"
        onClick={handleSkip}
        disabled={isLoading}
      >
        {isLoading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Finishing...
          </>
        ) : (
          <>
            Skip for now
            <ArrowRight className="ml-2 h-4 w-4" />
          </>
        )}
      </Button>

      <div className="flex justify-start pt-2">
        <Button type="button" variant="ghost" onClick={onBack} disabled={isLoading}>
          Back
        </Button>
      </div>
    </div>
  )
}
