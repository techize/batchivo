/**
 * Step 1: Business Information
 * Collects business name, URL slug, and description
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Loader2 } from 'lucide-react'

const step1Schema = z.object({
  business_name: z.string().min(2, 'Business name must be at least 2 characters'),
  slug: z
    .string()
    .min(2, 'URL slug must be at least 2 characters')
    .regex(/^[a-z0-9-]+$/, 'URL slug can only contain lowercase letters, numbers, and hyphens'),
  business_description: z.string().optional(),
})

type Step1FormData = z.infer<typeof step1Schema>

interface Step1BusinessInfoProps {
  initialData?: {
    business_name?: string
    slug?: string
    business_description?: string
  }
  onSubmit: (data: Step1FormData) => void
  isLoading?: boolean
}

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .substring(0, 50)
}

export function Step1BusinessInfo({ initialData, onSubmit, isLoading }: Step1BusinessInfoProps) {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<Step1FormData>({
    resolver: zodResolver(step1Schema),
    defaultValues: {
      business_name: initialData?.business_name || '',
      slug: initialData?.slug || '',
      business_description: initialData?.business_description || '',
    },
  })

  const businessName = watch('business_name')
  const slug = watch('slug')

  // Auto-generate slug from business name (only if slug hasn't been manually edited)
  useEffect(() => {
    if (businessName && !initialData?.slug) {
      const generatedSlug = generateSlug(businessName)
      if (generatedSlug !== slug) {
        setValue('slug', generatedSlug)
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [businessName, initialData?.slug, setValue])

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="business_name">Business Name *</Label>
          <Input
            id="business_name"
            placeholder="My Craft Shop"
            {...register('business_name')}
            disabled={isLoading}
          />
          {errors.business_name && (
            <p className="text-sm text-destructive">{errors.business_name.message}</p>
          )}
        </div>

        <div className="space-y-2">
          <Label htmlFor="slug">Shop URL *</Label>
          <div className="flex items-center">
            <span className="text-sm text-muted-foreground mr-2">batchivo.com/shop/</span>
            <Input
              id="slug"
              placeholder="my-craft-shop"
              className="flex-1"
              {...register('slug')}
              disabled={isLoading}
            />
          </div>
          {errors.slug && <p className="text-sm text-destructive">{errors.slug.message}</p>}
          <p className="text-xs text-muted-foreground">
            This will be your public shop URL. You can change it later.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="business_description">Business Description</Label>
          <Textarea
            id="business_description"
            placeholder="Tell customers what you make and sell..."
            rows={3}
            {...register('business_description')}
            disabled={isLoading}
          />
          <p className="text-xs text-muted-foreground">
            A brief description shown on your shop page.
          </p>
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="submit" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            'Continue'
          )}
        </Button>
      </div>
    </form>
  )
}
