/**
 * Step 3: Shop Setup
 * Configure shop display name, currency, timezone, and branding
 */

import { useState, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Loader2, Upload, X, Image as ImageIcon } from 'lucide-react'
import { uploadLogo } from '@/lib/api/onboarding'

const step3Schema = z.object({
  shop_display_name: z.string().optional(),
  currency: z.string().default('GBP'),
  timezone: z.string().default('Europe/London'),
  primary_color: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Invalid color format').default('#6366f1'),
})

type Step3FormData = z.infer<typeof step3Schema>

const CURRENCIES = [
  { value: 'GBP', label: 'British Pound (GBP)' },
  { value: 'USD', label: 'US Dollar (USD)' },
  { value: 'EUR', label: 'Euro (EUR)' },
  { value: 'CAD', label: 'Canadian Dollar (CAD)' },
  { value: 'AUD', label: 'Australian Dollar (AUD)' },
]

const TIMEZONES = [
  { value: 'Europe/London', label: 'London (GMT/BST)' },
  { value: 'America/New_York', label: 'New York (EST/EDT)' },
  { value: 'America/Los_Angeles', label: 'Los Angeles (PST/PDT)' },
  { value: 'America/Chicago', label: 'Chicago (CST/CDT)' },
  { value: 'Europe/Paris', label: 'Paris (CET/CEST)' },
  { value: 'Europe/Berlin', label: 'Berlin (CET/CEST)' },
  { value: 'Australia/Sydney', label: 'Sydney (AEST/AEDT)' },
]

const BRAND_COLORS = [
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#ec4899', // Pink
  '#ef4444', // Red
  '#f97316', // Orange
  '#eab308', // Yellow
  '#22c55e', // Green
  '#14b8a6', // Teal
  '#06b6d4', // Cyan
  '#3b82f6', // Blue
]

interface Step3ShopSetupProps {
  initialData?: {
    shop_display_name?: string
    currency?: string
    timezone?: string
    primary_color?: string
    logo_url?: string
  }
  onSubmit: (data: Step3FormData) => void
  onBack: () => void
  isLoading?: boolean
}

export function Step3ShopSetup({ initialData, onSubmit, onBack, isLoading }: Step3ShopSetupProps) {
  const [logoPreview, setLogoPreview] = useState<string | null>(initialData?.logo_url || null)
  const [isUploadingLogo, setIsUploadingLogo] = useState(false)
  const [logoError, setLogoError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<Step3FormData>({
    resolver: zodResolver(step3Schema),
    defaultValues: {
      shop_display_name: initialData?.shop_display_name || '',
      currency: initialData?.currency || 'GBP',
      timezone: initialData?.timezone || 'Europe/London',
      primary_color: initialData?.primary_color || '#6366f1',
    },
  })

  const primaryColor = watch('primary_color')

  async function handleLogoUpload(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return

    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/svg+xml']
    if (!allowedTypes.includes(file.type)) {
      setLogoError('Please upload a PNG, JPG, or SVG file')
      return
    }

    // Validate file size (max 2MB)
    if (file.size > 2 * 1024 * 1024) {
      setLogoError('File size must be less than 2MB')
      return
    }

    setLogoError(null)
    setIsUploadingLogo(true)

    try {
      // Create local preview
      const reader = new FileReader()
      reader.onload = (e) => {
        setLogoPreview(e.target?.result as string)
      }
      reader.readAsDataURL(file)

      // Upload to server
      await uploadLogo(file)
    } catch (err) {
      setLogoError(err instanceof Error ? err.message : 'Failed to upload logo')
      setLogoPreview(null)
    } finally {
      setIsUploadingLogo(false)
    }
  }

  function removeLogo() {
    setLogoPreview(null)
    setLogoError(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-4">
        {/* Logo Upload */}
        <div className="space-y-2">
          <Label>Shop Logo</Label>
          <div className="flex items-start gap-4">
            <div className="relative">
              {logoPreview ? (
                <div className="relative h-24 w-24 rounded-lg border overflow-hidden">
                  <img
                    src={logoPreview}
                    alt="Logo preview"
                    className="h-full w-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={removeLogo}
                    className="absolute top-1 right-1 p-1 bg-background/80 rounded-full hover:bg-background"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              ) : (
                <div className="h-24 w-24 rounded-lg border-2 border-dashed flex items-center justify-center bg-muted/50">
                  <ImageIcon className="h-8 w-8 text-muted-foreground" />
                </div>
              )}
            </div>
            <div className="flex-1">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/svg+xml"
                onChange={handleLogoUpload}
                className="hidden"
                id="logo-upload"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploadingLogo}
              >
                {isUploadingLogo ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Logo
                  </>
                )}
              </Button>
              <p className="text-xs text-muted-foreground mt-1">
                PNG, JPG, or SVG. Max 2MB.
              </p>
              {logoError && <p className="text-xs text-destructive mt-1">{logoError}</p>}
            </div>
          </div>
        </div>

        {/* Shop Display Name */}
        <div className="space-y-2">
          <Label htmlFor="shop_display_name">Shop Display Name</Label>
          <Input
            id="shop_display_name"
            placeholder="My Awesome Shop"
            {...register('shop_display_name')}
            disabled={isLoading}
          />
          <p className="text-xs text-muted-foreground">
            Public name shown to customers. Leave blank to use your business name.
          </p>
        </div>

        {/* Currency */}
        <div className="space-y-2">
          <Label htmlFor="currency">Currency</Label>
          <Select
            value={watch('currency')}
            onValueChange={(value) => setValue('currency', value)}
            disabled={isLoading}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select currency" />
            </SelectTrigger>
            <SelectContent>
              {CURRENCIES.map((currency) => (
                <SelectItem key={currency.value} value={currency.value}>
                  {currency.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Timezone */}
        <div className="space-y-2">
          <Label htmlFor="timezone">Timezone</Label>
          <Select
            value={watch('timezone')}
            onValueChange={(value) => setValue('timezone', value)}
            disabled={isLoading}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select timezone" />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONES.map((tz) => (
                <SelectItem key={tz.value} value={tz.value}>
                  {tz.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Brand Color */}
        <div className="space-y-2">
          <Label>Brand Color</Label>
          <div className="flex flex-wrap gap-2">
            {BRAND_COLORS.map((color) => (
              <button
                key={color}
                type="button"
                onClick={() => setValue('primary_color', color)}
                className={`h-8 w-8 rounded-full border-2 transition-all ${
                  primaryColor === color
                    ? 'border-foreground scale-110'
                    : 'border-transparent hover:scale-105'
                }`}
                style={{ backgroundColor: color }}
              />
            ))}
          </div>
          <div className="flex items-center gap-2 mt-2">
            <Label htmlFor="custom_color" className="text-xs">
              Custom:
            </Label>
            <Input
              id="custom_color"
              type="color"
              className="h-8 w-12 p-0 border-none cursor-pointer"
              value={primaryColor}
              onChange={(e) => setValue('primary_color', e.target.value)}
              disabled={isLoading}
            />
            <Input
              type="text"
              className="w-24 h-8 text-xs"
              value={primaryColor}
              onChange={(e) => {
                if (/^#[0-9A-Fa-f]{0,6}$/.test(e.target.value)) {
                  setValue('primary_color', e.target.value)
                }
              }}
              disabled={isLoading}
            />
          </div>
          {errors.primary_color && (
            <p className="text-sm text-destructive">{errors.primary_color.message}</p>
          )}
        </div>
      </div>

      <div className="flex justify-between pt-4">
        <Button type="button" variant="outline" onClick={onBack} disabled={isLoading}>
          Back
        </Button>
        <Button type="submit" disabled={isLoading || isUploadingLogo}>
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
