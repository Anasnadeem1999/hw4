import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import type { User } from './types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => Promise<void>
}

export interface RegisterInput {
  first_name: string
  last_name: string
  email: string
  password: string
}

const AuthContext = createContext<AuthState | null>(null)

/** Turn a FastAPI error body into something worth showing a shopper. */
async function errorMessage(res: Response, fallback: string) {
  try {
    const body = await res.json()
    if (typeof body.detail === 'string') return body.detail
    // 422 from pydantic: detail is a list of field errors
    if (Array.isArray(body.detail) && body.detail[0]?.msg) {
      return String(body.detail[0].msg).replace(/^Value error,\s*/, '')
    }
  } catch {
    /* fall through */
  }
  return fallback
}

async function post(url: string, body?: unknown) {
  return fetch(url, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
  })
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // Ask the backend who the session cookie belongs to, if anyone.
  useEffect(() => {
    fetch('/api/auth/me', { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await post('/api/auth/login', { email, password })
    if (!res.ok) throw new Error(await errorMessage(res, 'Could not sign you in.'))
    setUser(await res.json())
  }, [])

  const register = useCallback(async (input: RegisterInput) => {
    const res = await post('/api/auth/register', input)
    if (!res.ok) throw new Error(await errorMessage(res, 'Could not create your account.'))
    setUser(await res.json())
  }, [])

  const logout = useCallback(async () => {
    await post('/api/auth/logout')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
