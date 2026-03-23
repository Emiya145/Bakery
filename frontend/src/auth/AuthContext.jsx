import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  const loadMe = useCallback(async () => {
    const token = localStorage.getItem('auth_token')
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      const me = await authApi.getMe()
      setUser(me)
    } catch {
      localStorage.removeItem('auth_token')
      setUser(null)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMe()
  }, [loadMe])

  const login = useCallback(async (username, password) => {
    const data = await authApi.login(username, password)
    if (!data?.token) {
      throw new Error('Login failed')
    }
    localStorage.setItem('auth_token', data.token)
    const me = await authApi.getMe()
    setUser(me)
    return me
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token')
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, isLoading, login, logout, reloadMe: loadMe }),
    [user, isLoading, login, logout, loadMe],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return ctx
}
