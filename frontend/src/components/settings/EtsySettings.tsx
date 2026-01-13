/**
 * EtsySettings Component
 *
 * Manages Etsy marketplace integration configuration including API credentials and shop ID.
 */

import { useState, useEffect } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, Eye, EyeOff, Loader2, TestTube2, Store } from 'lucide-react'

import {
  getEtsySettings,
  updateEtsySettings,
  testEtsyConnection,
  type EtsySettingsUpdate,
} from '@/lib/api/settings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

const etsySettingsSchema = z.object({
  enabled: z.boolean(),
  api_key: z.string().optional(),
  shared_secret: z.string().optional(),
  access_token: z.string().optional(),
  refresh_token: z.string().optional(),
  shop_id: z.string().optional(),
})

type EtsySettingsFormValues = z.infer<typeof etsySettingsSchema>

export function EtsySettings() {
  const queryClient = useQueryClient()
  const [showCredentials, setShowCredentials] = useState(false)
  const [credentialsOpen, setCredentialsOpen] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; shop_name?: string | null; shop_url?: string | null } | null>(null)

  const { data: settings, isLoading, error } = useQuery({
    queryKey: ['etsy-settings'],
    queryFn: getEtsySettings,
  })

  const form = useForm<EtsySettingsFormValues>({
    resolver: zodResolver(etsySettingsSchema),
    defaultValues: {
      enabled: settings?.enabled ?? false,
      api_key: '',
      shared_secret: '',
      access_token: '',
      refresh_token: '',
      shop_id: settings?.shop_id ?? '',
    },
  })

  // Update form when settings load
  useEffect(() => {
    if (settings && !form.formState.isDirty) {
      form.reset({
        enabled: settings.enabled,
        api_key: '',
        shared_secret: '',
        access_token: '',
        refresh_token: '',
        shop_id: settings.shop_id ?? '',
      })
    }
  }, [settings, form])

  const updateMutation = useMutation({
    mutationFn: (data: EtsySettingsUpdate) => updateEtsySettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['etsy-settings'] })
      setCredentialsOpen(false)
      setTestResult(null)
    },
  })

  const testMutation = useMutation({
    mutationFn: testEtsyConnection,
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

  const onSubmit = (data: EtsySettingsFormValues) => {
    const update: EtsySettingsUpdate = {
      enabled: data.enabled,
    }

    // Only include credentials if they're being updated
    if (data.api_key) update.api_key = data.api_key
    if (data.shared_secret) update.shared_secret = data.shared_secret
    if (data.access_token) update.access_token = data.access_token
    if (data.refresh_token) update.refresh_token = data.refresh_token
    if (data.shop_id) update.shop_id = data.shop_id

    updateMutation.mutate(update)
  }

  const handleEnableToggle = (enabled: boolean) => {
    updateMutation.mutate({ enabled })
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
        <AlertDescription>Failed to load Etsy settings</AlertDescription>
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
              <Store className="h-5 w-5" />
              <CardTitle>Etsy Marketplace</CardTitle>
            </div>
            <Switch
              checked={settings?.enabled ?? false}
              onCheckedChange={handleEnableToggle}
              disabled={updateMutation.isPending}
            />
          </div>
          <CardDescription>
            Sync your products to Etsy marketplace
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

          {/* Shop Info */}
          {settings?.shop_name && (
            <div className="flex items-center gap-2 text-sm">
              <Store className="h-4 w-4 text-muted-foreground" />
              <span>Connected to: <strong>{settings.shop_name}</strong></span>
            </div>
          )}

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
                  <span className="text-muted-foreground">API Key:</span>
                  <code>{showCredentials ? settings.api_key_masked : '••••••••'}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Shared Secret:</span>
                  <code>{showCredentials ? settings.shared_secret_masked : '••••••••'}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Access Token:</span>
                  <code>{showCredentials ? settings.access_token_masked : '••••••••'}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Refresh Token:</span>
                  <code>{settings.refresh_token_set ? 'Set' : 'Not set'}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Shop ID:</span>
                  <code>{settings.shop_id ?? 'Not set'}</code>
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
                  <AlertDescription>
                    {testResult.message}
                    {testResult.shop_url && (
                      <a
                        href={testResult.shop_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ml-2 text-primary underline"
                      >
                        View Shop
                      </a>
                    )}
                  </AlertDescription>
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
                  ? 'Enter new credentials to update your Etsy configuration'
                  : 'Enter your Etsy API credentials to enable marketplace sync'}
              </CardDescription>
            </CardHeader>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <CardContent>
              <Form {...form}>
                <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
                  <FormField
                    control={form.control}
                    name="api_key"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>API Key (Keystring)</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="Enter your Etsy API key"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Found in your Etsy Developer Dashboard under API Keys
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="shared_secret"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Shared Secret</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="Enter your Etsy shared secret"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Your Etsy API shared secret
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="access_token"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Access Token</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="Enter your OAuth access token"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          OAuth access token from the Etsy authorization flow
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="refresh_token"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Refresh Token (Optional)</FormLabel>
                        <FormControl>
                          <Input
                            type="password"
                            placeholder="Enter your OAuth refresh token"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Used to automatically refresh access tokens
                        </FormDescription>
                        <FormMessage />
                      </FormItem>
                    )}
                  />

                  <FormField
                    control={form.control}
                    name="shop_id"
                    render={({ field }) => (
                      <FormItem>
                        <FormLabel>Shop ID</FormLabel>
                        <FormControl>
                          <Input
                            placeholder="Enter your Etsy shop ID"
                            {...field}
                          />
                        </FormControl>
                        <FormDescription>
                          Your numeric Etsy shop ID (found in your shop URL)
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
