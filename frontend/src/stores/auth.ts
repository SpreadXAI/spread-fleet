import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { api, type User } from '@/api/client'

const TOKEN_KEY = 'spider_radar_token'
const USER_KEY = 'spider_radar_user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(
    localStorage.getItem(USER_KEY) ? JSON.parse(localStorage.getItem(USER_KEY)!) : null,
  )
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value && !!user.value)

  const displayLabel = computed(() => {
    if (!user.value) return ''
    return user.value.display_name || user.value.email
  })

  function persist(sessionToken: string, sessionUser: User) {
    token.value = sessionToken
    user.value = sessionUser
    localStorage.setItem(TOKEN_KEY, sessionToken)
    localStorage.setItem(USER_KEY, JSON.stringify(sessionUser))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  async function register(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.register({ email, password })
      persist(res.access_token, res.user)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '注册失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function login(email: string, password: string) {
    loading.value = true
    error.value = null
    try {
      const res = await api.login({ email, password })
      persist(res.access_token, res.user)
    } catch (e) {
      error.value = e instanceof Error ? e.message : '登录失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateProfile(displayName: string) {
    if (!token.value) return
    const updated = await api.updateProfile(token.value, { display_name: displayName })
    user.value = updated
    localStorage.setItem(USER_KEY, JSON.stringify(updated))
  }

  return {
    token,
    user,
    loading,
    error,
    isAuthenticated,
    displayLabel,
    register,
    login,
    logout,
    updateProfile,
  }
})
