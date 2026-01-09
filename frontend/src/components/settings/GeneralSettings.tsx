/**
 * GeneralSettings Component
 *
 * Manages basic tenant/organization settings like name and description.
 */

import { useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, Building2, Loader2 } from 'lucide-react'

import { getTenant, updateTenant, type TenantUpdate } from '@/lib/api/settings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const tenantFormSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name must be 100 characters or less'),
  description: z.string().max(500, 'Description must be 500 characters or less').optional(),
})

type TenantFormValues = z.infer<typeof tenantFormSchema>

export function GeneralSettings() {
  const queryClient = useQueryClient()

  const { data: tenant, isLoading, error } = useQuery({
    queryKey: ['tenant'],
    queryFn: getTenant,
  })

  const form = useForm<TenantFormValues>({
    resolver: zodResolver(tenantFormSchema),
    defaultValues: {
      name: tenant?.name ?? '',
      description: tenant?.description ?? '',
    },
  })

  // Update form when tenant loads
  useEffect(() => {
    if (tenant && !form.formState.isDirty) {
      form.reset({
        name: tenant.name,
        description: tenant.description ?? '',
      })
    }
  }, [tenant, form])

  const updateMutation = useMutation({
    mutationFn: (data: TenantUpdate) => updateTenant(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tenant'] })
    },
  })

  const onSubmit = (data: TenantFormValues) => {
    updateMutation.mutate({
      name: data.name,
      description: data.description || undefined,
    })
  }

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin" />
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Failed to load organization settings</AlertDescription>
      </Alert>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Building2 className="h-5 w-5" />
          <CardTitle>Organization Details</CardTitle>
        </div>
        <CardDescription>
          Basic information about your organization
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="name"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Organization Name</FormLabel>
                  <FormControl>
                    <Input placeholder="My Business" {...field} />
                  </FormControl>
                  <FormDescription>
                    The name of your business or organization
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea
                      placeholder="A brief description of your organization..."
                      className="min-h-[100px]"
                      {...field}
                    />
                  </FormControl>
                  <FormDescription>
                    Optional description for your organization
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="flex items-center gap-4 pt-2">
              <Button
                type="submit"
                disabled={updateMutation.isPending || !form.formState.isDirty}
              >
                {updateMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Save Changes
              </Button>

              {updateMutation.isSuccess && (
                <span className="text-sm text-green-600">Changes saved</span>
              )}
            </div>

            {/* Read-only info */}
            <div className="mt-6 space-y-2 rounded-md bg-muted p-3">
              <p className="text-sm font-medium">Organization Info</p>
              <div className="grid gap-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Slug:</span>
                  <code>{tenant?.slug}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Created:</span>
                  <span>{tenant?.created_at ? new Date(tenant.created_at).toLocaleDateString() : '-'}</span>
                </div>
              </div>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  )
}
