import { useState, useEffect, type FormEvent } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { loginUser } from '@/api/auth'
import { useAuthStore } from '@/store/auth'

export default function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { isAuthenticated, setAuthenticated } = useAuthStore()

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true })
    }
  }, [isAuthenticated, navigate])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    const result = await loginUser(username, password)
    setIsSubmitting(false)

    if (result.ok) {
      setAuthenticated(username)
      const from =
        (location.state as { from?: { pathname?: string } } | null)?.from
          ?.pathname ?? '/dashboard'
      navigate(from, { replace: true })
    } else {
      setError(result.error ?? 'Login failed')
    }
  }

  return (
    <div className="min-h-screen bg-[#111417] flex items-center justify-center px-4">
      <Card className="w-full max-w-md bg-[var(--kt-surface-container-low)] border-none">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl text-[var(--kt-on-surface)]">Kinetic Terminal</CardTitle>
          <p className="text-[var(--kt-on-surface-variant)] text-sm mt-1">
            Sign in to your account
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username" className="text-[var(--kt-on-surface)]">
                Username
              </Label>
              <Input
                id="username"
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                required
                className="bg-[var(--kt-surface-container-lowest)] border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] placeholder-[var(--kt-on-surface-variant)]"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-[var(--kt-on-surface)]">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="bg-[var(--kt-surface-container-lowest)] border-[rgba(66,70,84,0.15)] text-[var(--kt-on-surface)] placeholder-[var(--kt-on-surface-variant)]"
              />
            </div>

            {error && (
              <div className="bg-[var(--kt-tertiary-container)]/20 text-[var(--kt-tertiary)] text-sm rounded-md px-4 py-3">
                {error}
              </div>
            )}

            <Button
              type="submit"
              className="w-full bg-gradient-to-r from-[var(--kt-primary-container)] to-[var(--kt-secondary-container)] text-white hover:opacity-90"
              disabled={isSubmitting}
            >
              {isSubmitting ? 'Signing in...' : 'Sign in'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
