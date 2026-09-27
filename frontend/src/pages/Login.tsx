import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const justRegistered = new URLSearchParams(location.search).get('new') === '1'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)
    setBusy(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not sign you in.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section">
      <div className="page auth">
        <h1 className="auth__title">Log in</h1>
        <p className="auth__sub">Welcome back to Campus Customs.</p>

        {justRegistered && (
          <p className="notice">Your account is ready — sign in to continue.</p>
        )}

        {error && (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )}

        <form onSubmit={submit}>
          <div className="auth__field">
            <label className="label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@yale.edu"
            />
          </div>

          <div className="auth__field">
            <label className="label" htmlFor="password">
              Password
            </label>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
            />
          </div>

          <button className="button button--primary button--block" type="submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Log in'}
          </button>
        </form>

        <p className="auth__foot">
          New here? <Link to="/create-account">Create an account</Link>
        </p>
      </div>
    </section>
  )
}
