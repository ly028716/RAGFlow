import { storage } from '@/utils/storage'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'
import { ElMessage } from 'element-plus'

const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

export interface FetchStreamOptions extends RequestInit {
  onMessage?: (data: string) => void
  onError?: (error: Error) => void
  onDone?: () => void
  timeout?: number // 超时时间（毫秒），默认30秒
}

export async function fetchStream(url: string, options: FetchStreamOptions = {}) {
  const fullUrl = url.startsWith('http') ? url : `${baseURL}${url}`
  const token = storage.getToken()

  // 设置默认超时时间（30秒）
  const timeout = options.timeout || 30000
  const controller = new AbortController()
  let timedOut = false
  const timeoutId = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeout)

  const headers = new Headers(options.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  console.log(`[fetch-stream] 开始请求: ${fullUrl}, 超时设置: ${timeout}ms`)

  try {
    let response = await fetch(fullUrl, {
      ...options,
      headers,
      signal: options.signal || controller.signal
    })

    clearTimeout(timeoutId)

    // 处理 401 Token 过期
    if (response.status === 401) {
      const authStore = useAuthStore()
      const success = await authStore.refreshTokenAction()

      if (success) {
        // 重试请求
        const newToken = storage.getToken()
        if (newToken) {
          headers.set('Authorization', `Bearer ${newToken}`)

          // 重新设置超时
          const retryTimeoutId = setTimeout(() => {
            timedOut = true
            controller.abort()
          }, timeout)

          response = await fetch(fullUrl, {
            ...options,
            headers,
            signal: options.signal || controller.signal
          })

          clearTimeout(retryTimeoutId)
        }
      } else {
        // 刷新失败，跳转登录
        authStore.clearAuth()
        router.push('/login')
        throw new Error('认证失效，请重新登录')
      }
    }

    if (!response.ok) {
      const errorText = await response.text()
      let errorMessage = `HTTP error! status: ${response.status}`
      try {
        const errorJson = JSON.parse(errorText)
        errorMessage = errorJson.detail || errorJson.message || errorMessage
      } catch {
        // ignore
      }
      console.error(`[fetch-stream] HTTP错误: ${errorMessage}`)
      throw new Error(errorMessage)
    }

    if (!response.body) {
      console.error('[fetch-stream] 响应体为空')
      throw new Error('Response body is empty')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    console.log('[fetch-stream] 开始读取流式响应')

    while (true) {
      const { done, value } = await reader.read()
      if (done) {
        console.log('[fetch-stream] 流式响应完成')
        options.onDone?.()
        break
      }

      const text = decoder.decode(value, { stream: true })
      try {
        options.onMessage?.(text)
      } catch (e) {
        console.error('[fetch-stream] 处理消息时出错:', e)
        await reader.cancel()
        throw e
      }
    }
  } catch (error: any) {
    clearTimeout(timeoutId)

    // 处理超时错误
    if (error.name === 'AbortError') {
      if (!timedOut || options.signal?.aborted) {
        // 用户主动取消
        console.log('[fetch-stream] 请求被用户取消')
        options.onDone?.()
        return
      } else {
        // 超时
        const timeoutError = new Error(`请求超时（${timeout}ms），请检查网络连接或稍后重试`)
        console.error('[fetch-stream] 请求超时:', timeout, 'ms')
        options.onError?.(timeoutError)
        throw timeoutError
      }
    }

    console.error('[fetch-stream] 请求失败:', {
      name: error?.name,
      message: error?.message,
      url: fullUrl
    })
    options.onError?.(error)
    throw error
  }
}
