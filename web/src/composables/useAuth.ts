import { computed, reactive, readonly, ref } from 'vue'
import { message } from 'ant-design-vue'
import { fetchSession, loginUser, logoutUser, registerUser } from '@/services/api/auth'
import { clearCsrfToken, ensureCsrfToken } from '@/services/api/client'
import type { SessionMembership, SessionResponse, SessionUser } from '@/services/api/types'

interface AuthState {
  user: SessionUser | null
  memberships: SessionMembership[]
  loading: boolean
  ready: boolean
  error: string | null
}

const state = reactive<AuthState>({
  user: null,
  memberships: [],
  loading: false,
  ready: false,
  error: null,
})

let bootstrapPromise: Promise<void> | null = null

const setSession = (session: SessionResponse | null) => {
  state.user = session?.user ?? null
  state.memberships = session?.memberships ?? []
}

export const useAuth = () => {
  const isAuthenticated = computed(() => !!state.user)

  const bootstrap = async () => {
    if (state.ready && bootstrapPromise === null) return
    if (!bootstrapPromise) {
      bootstrapPromise = (async () => {
        try {
          await ensureCsrfToken()
          const session = await fetchSession()
          setSession(session)
        } catch (err) {
          setSession(null)
        } finally {
          state.ready = true
          bootstrapPromise = null
        }
      })()
    }
    return bootstrapPromise
  }

const handleAuthError = (err: unknown) => {
  const msg = err instanceof Error ? err.message : '请求失败，请稍后重试'
  state.error = msg
  console.error('Auth request failed:', err)
  message.error(msg)
}

  const withLoading = async <T>(fn: () => Promise<T>): Promise<T> => {
    state.loading = true
    state.error = null
    try {
      return await fn()
    } finally {
      state.loading = false
    }
  }

  const login = async (email: string, password: string) => {
    return withLoading(async () => {
      try {
        await ensureCsrfToken(true)
        const session = await loginUser({ email, password })
        setSession(session)
        clearCsrfToken()
        await ensureCsrfToken(true)
      } catch (err) {
        handleAuthError(err)
        throw err
      }
    })
  }

  const register = async (payload: { email: string; password: string; name?: string }) => {
    return withLoading(async () => {
      try {
        await ensureCsrfToken(true)
        const session = await registerUser(payload)
        setSession(session)
        clearCsrfToken()
        await ensureCsrfToken(true)
      } catch (err) {
        handleAuthError(err)
        throw err
      }
    })
  }

  const logout = async () => {
    return withLoading(async () => {
      try {
        await ensureCsrfToken(true)
        await logoutUser()
        setSession(null)
        clearCsrfToken()
      } catch (err) {
        handleAuthError(err)
        throw err
      }
    })
  }

  return {
    state: readonly(state),
    isAuthenticated,
    bootstrap,
    login,
    register,
    logout,
  }
}
