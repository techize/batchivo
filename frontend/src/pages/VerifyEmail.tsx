/**
 * Email verification page - Handles token from verification link
 */

import { useEffect, useState } from 'react'
import { useNavigate, Link } from '@tanstack/react-router'
import { useAuth } from '@/contexts/AuthContext'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, CheckCircle, XCircle, Mail } from 'lucide-react'
import { verifyEmail, resendVerification } from '@/lib/api/onboarding'
import { setAuthTokens } from '@/lib/auth'

type VerificationState = 'verifying' | 'success' | 'error' | 'no-token'

export function VerifyEmail() {
  const [state, setState] = useState<VerificationState>('verifying')
  const [error, setError] = useState('')
  const [tenantName, setTenantName] = useState('')
  const [resendEmail, setResendEmail] = useState('')
  const [isResending, setIsResending] = useState(false)
  const [resendSuccess, setResendSuccess] = useState(false)
  const navigate = useNavigate()
  const { refreshUser } = useAuth()

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search)
    const token = urlParams.get('token')
    const email = urlParams.get('email')

    if (email) {
      setResendEmail(email)
    }

    if (!token) {
      setState('no-token')
      return
    }

    verifyEmailToken(token)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  async function verifyEmailToken(token: string) {
    try {
      const response = await verifyEmail(token)

      // Store the tokens from verification response
      setAuthTokens({
        accessToken: response.access_token,
        refreshToken: response.refresh_token,
        tokenType: response.token_type,
        expiresAt: Date.now() + 30 * 60 * 1000, // 30 minutes
      })

      setTenantName(response.tenant_name)
      setState('success')

      // Refresh user context
      await refreshUser()

      // Redirect to onboarding wizard after brief success message
      setTimeout(() => {
        navigate({ to: '/onboarding' })
      }, 2000)
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Verification failed')
    }
  }

  async function handleResendVerification() {
    if (!resendEmail) return

    setIsResending(true)
    setResendSuccess(false)
    try {
      await resendVerification(resendEmail)
      setResendSuccess(true)
    } catch {
      // API always returns success for security
    } finally {
      setIsResending(false)
    }
  }

  // No token provided
  if (state === 'no-token') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
              <Mail className="h-6 w-6 text-yellow-600" />
            </div>
            <CardTitle>Missing verification token</CardTitle>
            <CardDescription>
              Please click the link in your verification email
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center space-y-4">
            <p className="text-sm text-muted-foreground">
              If you didn't receive an email, you can request a new verification link.
            </p>
          </CardContent>
          <CardFooter className="flex flex-col gap-2">
            <Link to="/signup" className="w-full">
              <Button variant="outline" className="w-full">
                Back to sign up
              </Button>
            </Link>
            <Link to="/login" className="w-full">
              <Button variant="ghost" className="w-full">
                Sign in
              </Button>
            </Link>
          </CardFooter>
        </Card>
      </div>
    )
  }

  // Verifying...
  if (state === 'verifying') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
            <CardTitle>Verifying your email</CardTitle>
            <CardDescription>
              Please wait while we verify your account...
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  // Success
  if (state === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-green-100">
              <CheckCircle className="h-6 w-6 text-green-600" />
            </div>
            <CardTitle>Email verified!</CardTitle>
            <CardDescription>
              Welcome to {tenantName || 'Nozzly'}
            </CardDescription>
          </CardHeader>
          <CardContent className="text-center">
            <p className="text-sm text-muted-foreground">
              Your account is now active. Redirecting you to setup your shop...
            </p>
            <div className="mt-4 flex justify-center">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Error
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
            <XCircle className="h-6 w-6 text-red-600" />
          </div>
          <CardTitle>Verification failed</CardTitle>
          <CardDescription>
            We couldn't verify your email address
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
          <p className="text-sm text-muted-foreground text-center">
            This can happen if the link has expired or has already been used.
            You can request a new verification link below.
          </p>
          {resendEmail && (
            <div className="space-y-2">
              {resendSuccess && (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    A new verification link has been sent to {resendEmail}
                  </AlertDescription>
                </Alert>
              )}
              <Button
                variant="outline"
                className="w-full"
                onClick={handleResendVerification}
                disabled={isResending}
              >
                {isResending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  'Resend verification email'
                )}
              </Button>
            </div>
          )}
        </CardContent>
        <CardFooter className="flex flex-col gap-2">
          <Link to="/signup" className="w-full">
            <Button variant="ghost" className="w-full">
              Create new account
            </Button>
          </Link>
          <Link to="/login" className="w-full">
            <Button variant="ghost" className="w-full">
              Sign in
            </Button>
          </Link>
        </CardFooter>
      </Card>
    </div>
  )
}
