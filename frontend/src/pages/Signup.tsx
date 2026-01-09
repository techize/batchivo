/**
 * Signup page - Tenant registration with email verification
 */

import { useState, useMemo } from 'react'
import { Link } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Check, X, Mail } from 'lucide-react'
import { registerTenant, resendVerification } from '@/lib/api/onboarding'

// Password validation rules
const PASSWORD_RULES = {
  minLength: 8,
  hasUppercase: /[A-Z]/,
  hasLowercase: /[a-z]/,
  hasDigit: /\d/,
}

interface PasswordStrength {
  score: number
  checks: {
    minLength: boolean
    hasUppercase: boolean
    hasLowercase: boolean
    hasDigit: boolean
  }
}

function validatePassword(password: string): PasswordStrength {
  const checks = {
    minLength: password.length >= PASSWORD_RULES.minLength,
    hasUppercase: PASSWORD_RULES.hasUppercase.test(password),
    hasLowercase: PASSWORD_RULES.hasLowercase.test(password),
    hasDigit: PASSWORD_RULES.hasDigit.test(password),
  }
  const score = Object.values(checks).filter(Boolean).length
  return { score, checks }
}

function PasswordStrengthIndicator({ password }: { password: string }) {
  const strength = useMemo(() => validatePassword(password), [password])

  if (!password) return null

  const getStrengthLabel = () => {
    if (strength.score <= 1) return { text: 'Weak', color: 'text-red-500' }
    if (strength.score <= 2) return { text: 'Fair', color: 'text-orange-500' }
    if (strength.score <= 3) return { text: 'Good', color: 'text-yellow-500' }
    return { text: 'Strong', color: 'text-green-500' }
  }

  const strengthInfo = getStrengthLabel()

  return (
    <div className="space-y-2 mt-2">
      {/* Strength bar */}
      <div className="flex gap-1">
        {[1, 2, 3, 4].map((level) => (
          <div
            key={level}
            className={`h-1 flex-1 rounded-full transition-colors ${
              strength.score >= level
                ? level <= 1
                  ? 'bg-red-500'
                  : level <= 2
                  ? 'bg-orange-500'
                  : level <= 3
                  ? 'bg-yellow-500'
                  : 'bg-green-500'
                : 'bg-muted'
            }`}
          />
        ))}
      </div>

      {/* Strength label */}
      <p className={`text-xs ${strengthInfo.color}`}>{strengthInfo.text}</p>

      {/* Requirements checklist */}
      <div className="grid grid-cols-2 gap-1 text-xs">
        <div className="flex items-center gap-1">
          {strength.checks.minLength ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <X className="h-3 w-3 text-muted-foreground" />
          )}
          <span className={strength.checks.minLength ? 'text-green-600' : 'text-muted-foreground'}>
            8+ characters
          </span>
        </div>
        <div className="flex items-center gap-1">
          {strength.checks.hasUppercase ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <X className="h-3 w-3 text-muted-foreground" />
          )}
          <span className={strength.checks.hasUppercase ? 'text-green-600' : 'text-muted-foreground'}>
            Uppercase letter
          </span>
        </div>
        <div className="flex items-center gap-1">
          {strength.checks.hasLowercase ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <X className="h-3 w-3 text-muted-foreground" />
          )}
          <span className={strength.checks.hasLowercase ? 'text-green-600' : 'text-muted-foreground'}>
            Lowercase letter
          </span>
        </div>
        <div className="flex items-center gap-1">
          {strength.checks.hasDigit ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <X className="h-3 w-3 text-muted-foreground" />
          )}
          <span className={strength.checks.hasDigit ? 'text-green-600' : 'text-muted-foreground'}>
            Number
          </span>
        </div>
      </div>
    </div>
  )
}

export function Signup() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [businessName, setBusinessName] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isResending, setIsResending] = useState(false)
  const [registrationComplete, setRegistrationComplete] = useState(false)
  const [registeredEmail, setRegisteredEmail] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')

    // Validate password strength
    const strength = validatePassword(password)
    if (strength.score < 4) {
      setError('Password must meet all requirements')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (!businessName.trim()) {
      setError('Business name is required')
      return
    }

    setIsLoading(true)

    try {
      await registerTenant({
        email,
        password,
        full_name: fullName.trim() || email.split('@')[0],
        business_name: businessName.trim(),
      })
      setRegisteredEmail(email)
      setRegistrationComplete(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create account')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleResendVerification() {
    setIsResending(true)
    try {
      await resendVerification(registeredEmail)
      // Show success feedback briefly
    } catch {
      // Silently fail - API always returns success for security
    } finally {
      setIsResending(false)
    }
  }

  // Show success state after registration
  if (registrationComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background p-4">
        <Card className="w-full max-w-md">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Mail className="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Check your email</CardTitle>
            <CardDescription>
              We've sent a verification link to <strong>{registeredEmail}</strong>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground text-center">
              Click the link in the email to verify your account and complete registration.
              The link will expire in 24 hours.
            </p>
            <div className="flex flex-col gap-2">
              <Button
                variant="outline"
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
          </CardContent>
          <CardFooter className="justify-center">
            <p className="text-sm text-muted-foreground">
              Already verified?{' '}
              <Link to="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </Card>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create an account</CardTitle>
          <CardDescription>Sign up for Nozzly to get started</CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <div className="space-y-2">
              <Label htmlFor="businessName">Business Name *</Label>
              <Input
                id="businessName"
                type="text"
                placeholder="My 3D Print Shop"
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                required
                disabled={isLoading}
              />
              <p className="text-xs text-muted-foreground">
                Your business or project name
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="fullName">Full Name</Label>
              <Input
                id="fullName"
                type="text"
                placeholder="John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                autoComplete="name"
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email *</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                autoComplete="new-password"
                disabled={isLoading}
              />
              <PasswordStrengthIndicator password={password} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">Confirm Password *</Label>
              <Input
                id="confirmPassword"
                type="password"
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                disabled={isLoading}
              />
              {confirmPassword && password !== confirmPassword && (
                <p className="text-xs text-red-500">Passwords do not match</p>
              )}
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating account...
                </>
              ) : (
                'Create account'
              )}
            </Button>
            <p className="text-sm text-muted-foreground text-center">
              Already have an account?{' '}
              <Link to="/login" className="text-primary hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
