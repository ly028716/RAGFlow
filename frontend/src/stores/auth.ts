import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { storage } from '@/utils/storage'
import type { UserInfo, TokenResponse } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  // State
  const token = ref<string | null>(storage.getToken())
  const refreshToken = ref<string | null>(storage.getRefreshToken())
  const user = ref<UserInfo | null>(storage.getUser())

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const username = computed(() => user.value?.username || '')
  const avatar = computed(() => user.value?.avatar || '')

  // Actions
  async function login(username: string, password: string): Promise<boolean> {
    try {
      const response = await authApi.login({ username, password })
      setTokens(response)
      await fetchUserInfo()
      return true
    } catch (error) {
      throw error
    }
  }

  async function register(username: string, password: string): Promise<boolean> {
    try {
      await authApi.register({ username, password })
      return true
    } catch (error) {
      throw error
    }
  }

  async function fetchUserInfo(): Promise<void> {
    try {
      const userInfo = await authApi.getCurrentUser()
      user.value = userInfo
      storage.setUser(userInfo)
    } catch (error) {
      console.error('获取用户信息失败:', error)
    }
  }

  async function refreshTokenAction(): Promise<boolean> {
    if (!refreshToken.value) return false

    try {
      const response = await authApi.refreshToken(refreshToken.value)
      setTokens(response)
      return true
    } catch {
      clearAuth()
      return false
    }
  }

  function setTokens(tokens: TokenResponse) {
    token.value = tokens.access_token
    refreshToken.value = tokens.refresh_token
    storage.setToken(tokens.access_token)
    storage.setRefreshToken(tokens.refresh_token)
  }

  function clearAuth() {
    token.value = null
    refreshToken.value = null
    user.value = null
    storage.clearAuth()
  }

  function logout() {
    clearAuth()
  }

  return {
    token,
    refreshToken,
    user,
    isAuthenticated,
    username,
    avatar,
    login,
    register,
    logout,
    fetchUserInfo,
    refreshTokenAction,
    setTokens,
    clearAuth
  }
})
