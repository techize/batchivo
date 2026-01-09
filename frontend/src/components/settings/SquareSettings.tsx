/**
 * SquareSettings Component
 *
 * Manages Square payment gateway configuration including credentials and environment.
 */

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, CreditCard, Eye, EyeOff, Loader2, TestTube2 } from 'lucide-react'

import {
  getSquareSettings,
  updateSquareSettings,
  testSquareConnection,
  type SquareSettingsUpdate,
} from '@/lib/api/settings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const squareSettingsSchema = z.object({
  enabled: z.boolean(),
  environment: z.enum(['sandbox', 'production']),
  access_token: z.string().optional(),
  app_id: z.string().optional(),
  location_id: z.string().optional(),
})

type SquareSettingsFormValues = z.infer<typeof squareSettingsSchema>

export function SquareSettings() {
  const queryClient = useQueryClient()
  const [showCredentials, setShowCredentials] = useState(false)
  const [credentialsOpen, setCredentialsOpen] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const { data: settings, isLoading, error } = useQuery({
    queryKey: ['square-settings'],
    queryFn: getSquareSettings,
  })

  const form = useForm<SquareSettingsFormValues>({
    resolver: zodResolver(squareSettingsSchema),
    defaultValues: {
      enabled: settings?.enabled ?? false,
      environment: settings?.environment ?? 'sandbox',
      access_token: '',
      app_id: settings?.app_id ?? '',
      location_id: '',
    },
  })

  // Update form when settings load
  useEffect(() => {
    if (settings && !form.formState.isDirty) {
      form.reset({
        enabled: settings.enabled,
        environment: settings.environment,
        access_token: '',
        app_id: settings.app_id ?? '',
        location_id: '',
      })
    }
  }, [settings, form])

  const updateMutation = useMutation({
    mutationFn: (data: SquareSettingsUpdate) => updateSquareSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['square-settings'] })
      setCredentialsOpen(false)
      setTestResult(null)
    },
  })

  const testMutation = useMutation({
    mutationFn: testSquareConnection,
    onSuccess: (result) => {
      setTestResult(result)
    },
    onError: (error) => {
      setTestResult({
        success: false,
        message: error instanceof Error ? error.message : 'Connection test failed',
      })
    },
  })

  const onSubmit = (data: SquareSettingsFormValues) => {
    const update: SquareSettingsUpdate = {
      enabled: data.enabled,
      environment: data.environment,
    }

    // Only include credentials if they're being updated
    if (data.access_token) update.access_token = data.access_token
    if (data.app_id) update.app_id = data.app_id
    if (data.location_id) update.location_id = data.location_id

    updateMutation.mutate(update)
  }

  const handleEnableToggle = (enabled: boolean) => {
    updateMutation.mutate({ enabled })
  }

  const handleEnvironmentChange = (environment: 'sandbox' | 'production') => {
    updateMutation.mutate({ environment })
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
        <AlertDescription>Failed to load Square settings</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* Status Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              <CardTitle>Square Payments</CardTitle>
            </div>
            <Switch
              checked={settings?.enabled ?? false}
              onCheckedChange={handleEnableToggle}
              disabled={updateMutation.isPending}
            />
          </div>
          <CardDescription>
            Accept payments through Square payment gateway
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Configuration Status */}
          <div className="flex items-center gap-2 text-sm">
            {settings?.is_configured ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span className="text-green-600">Credentials configured</span>
              </>
            ) : (
              <>
                <AlertCircle className="h-4 w-4 text-yellow-500" />
                <span className="text-yellow-600">Credentials not configured</span>
              </>
            )}
          </div>

          {/* Environment Selector */}
          <div className="flex items-center justify-between">
            <div>
              <Label>Environment</Label>
              <p className="text-sm text-muted-foreground">
                {settings?.environment === 'production'
                  ? 'Processing real payments'
                  : 'Test mode - no real charges'}
              </p>
            </div>
            <Select
              value={settings?.environment ?? 'sandbox'}
              onValueChange={(value) => handleEnvironmentChange(value as 'sandbox' | 'production')}
              disabled={updateMutation.isPending}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="sandbox">Sandbox (Test)</SelectItem>
                <SelectItem value="production">Production (Live)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Current Credentials (masked) */}
          {settings?.is_configured && (
            <div className="space-y-2 rounded-md bg-muted p-3">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Current Credentials</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCredentials(!showCredentials)}
                >
                  {showCredentials ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                </Button>
              </div>
              <div className="grid gap-1 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Access Token:</span>
                  <code>{showCredentials ? settings.access_token_masked : '••••••••'}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">App ID:</span>
                  <code>{settings.app_id ?? 'Not set'}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Location ID:</span>
                  <code>{showCredentials ? settings.location_id_masked : '••••••••'}</code>
                </div>
              </div>
            </div>
          )}

          {/* Test Connection Button */}
          {settings?.is_configured && (
            <div className="space-y-2">
              <Button
                variant="outline"
                onClick={() => testMutation.mutate()}
                disabled={testMutation.isPending}
              >
                {testMutation.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <TestTube2 className="mr-2 h-4 w-4" />
                )}
                Test Connection
              </Button>

              {testResult && (
                <Alert variant={testResult.success ? 'default' : 'destructive'}>
                  {testResult.success ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <AlertCircle className="h-4 w-4" />
                  )}
                  <AlertTitle>{testResult.success ? 'Success' : 'Failed'}</AlertTitle>
                  <AlertDescription>{testResult.message}</AlertDescription>
                </Alert>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Update Credentials Card */}
      <Card>
        <Collapsible open={credentialsOpen} onOpenChange={setCredentialsOpen}>
          <CollapsibleTrigger asChild>
            <CardHeader className="cursor-pointer hover:bg-muted/50">
              <CardTitle className="text-base">
                {settings?.is_configured ? 'Update Credentials' : 'Configure Credentials'}
              </CardTitle>
              <CardDescription>
                {settings?.is_configured
                  ? 'Enter new credentials to update your Square configuration'
                  : 'Enter your Square API credentials to enable payments'}
              </CardDescription>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="access_token"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Access Token</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="Enter your Square access token"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Found in your Square Developer Dashboard
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="app_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Application ID</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="sq0idp-..."
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Your Square application ID
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="location_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Location ID</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="Enter your Square location ID"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          The location ID for processing payments
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <div className="flex gap-2">
                    <Button
                      type="submit"
                      disabled={updateMutation.isPending}
                    >
                      {updateMutation.isPending && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      Save Credentials
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => setCredentialsOpen(false)}
                    >
                      Cancel
                    </Button>
                  </div>
                </form>
              </Form>
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>
    </div>
  )
}
