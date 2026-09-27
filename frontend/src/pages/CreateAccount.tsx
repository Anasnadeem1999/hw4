import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth'

const MIN_PASSWORD = 8

export default function CreateAccount() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    password: '',
  })
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  function update(field: keyof typeof form) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError(null)

    if (form.password.length < MIN_PASSWORD) {
      setError(`Please use at least ${MIN_PASSWORD} characters for your password.`)
      return
    }

    setBusy(true)
    try {
      // Registration signs the new shopper straight in.
      await register(form)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create your account.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="section">
      <div className="page auth">
        <h1 className="auth__title">Create account</h1>
        <p className="auth__sub">Save your size and pick up where you left off.</p>

        {error && (
          <p className="notice notice--error" role="alert">
            {error}
          </p>
        )}

        <form onSubmit={submit}>
          <div className="auth__row">
            <div className="auth__field">
              <label className="label" htmlFor="firstName">
                First name
              </label>
              <input
                id="firstName"
                className="input"
                autoComplete="given-name"
                required
                value={form.first_name}
                onChange={update('first_name')}
              />
            </div>
            <div className="auth__field">
              <label className="label" htmlFor="lastName">
                Last name
              </label>
              <input
                id="lastName"
                className="input"
                autoComplete="family-name"
                required
                value={form.last_name}
                onChange={update('last_name')}
              />
            </div>
          </div>

          <div className="auth__field">
            <label className="label" htmlFor="newEmail">
              Email
            </label>
            <input
              id="newEmail"
              className="input"
              type="email"
              autoComplete="email"
              required
              value={form.email}
              onChange={update('email')}
              placeholder="you@yale.edu"
            />
          </div>

          <div className="auth__field">
            <label className="label" htmlFor="newPassword">
              Password
            </label>
            <input
              id="newPassword"
              className="input"
              type="password"
              autoComplete="new-password"
              required
              minLength={MIN_PASSWORD}
              value={form.password}
              onChange={update('password')}
              placeholder={`At least ${MIN_PASSWORD} characters`}
            />
          </div>

          <button className="button button--primary button--block" type="submit" disabled={busy}>
            {busy ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <p className="auth__foot">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </div>
    </section>
  )
}
