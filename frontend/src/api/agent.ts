import request from './index'
import type {
  AgentTool,
  ToolCreate,
  ToolUpdate,
  TaskExecuteRequest,
  ExecutionResponse,
  ExecutionListItem,
  AgentStreamEvent,
  PaginatedList
} from '@/types'
import { storage } from '@/utils/storage'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

export const agentApi = {
  // 工具管理
  getTools(params?: { skip?: number, limit?: number, tool_type?: string, is_enabled?: boolean }): Promise<PaginatedList<AgentTool>> {
    return request.get('/agent/tools', { params })
  },

  getTool(id: number): Promise<AgentTool> {
    return request.get(`/agent/tools/${id}`)
  },

  createTool(data: ToolCreate): Promise<AgentTool> {
    return request.post('/agent/tools', data)
  },

  updateTool(id: number, data: ToolUpdate): Promise<AgentTool> {
    return request.put(`/agent/tools/${id}`, data)
  },

  deleteTool(id: number): Promise<{ message: string }> {
    return request.delete(`/agent/tools/${id}`)
  },

  // 任务执行
  executeTask(data: TaskExecuteRequest): Promise<ExecutionResponse> {
    return request.post('/agent/execute', data)
  },

  // 流式执行任务
  streamExecuteTask(
    data: TaskExecuteRequest,
    onMessage: (event: AgentStreamEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): () => void {
    const controller = new AbortController()
    const authStore = useAuthStore()
    
    const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1'
    const url = `${baseURL}/agent/execute/stream`

    async function doFetch(): Promise<Response> {
      const token = storage.getToken()
      const headers = new Headers()
      headers.set('Content-Type', 'application/json')
      if (token) {
        headers.set('Authorization', `Bearer ${token}`)
      }
      return fetch(url, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
        signal: controller.signal
      })
    }

    async function fetchWithRefresh(): Promise<Response> {
      let response = await doFetch()
      if (response.status !== 401) return response

      const ok = await authStore.refreshTokenAction()
      if (!ok) {
        authStore.clearAuth()
        router.push('/login')
        return response
      }
      response = await doFetch()
      return response
    }

    fetchWithRefresh().then(async response => {
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }))
        throw new Error(errorData.detail || `请求失败: ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()

      if (!reader) {
        throw new Error('无法读取响应流')
      }

      let buffer = ''
      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() ?? ''

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue
            const payload = line.slice(6).trim()
            if (!payload) continue
            if (payload === '[DONE]') {
              onComplete?.()
              return
            }
            try {
              const event = JSON.parse(payload) as AgentStreamEvent
              onMessage(event)
            } catch {
              continue
            }
          }
        }
        onComplete?.()
      } finally {
        reader.releaseLock()
      }
    }).catch(error => {
      if (error?.name !== 'AbortError') {
        onError?.(error)
      } else {
        onComplete?.()
      }
    })
    
    return () => controller.abort()
  },

  // 执行历史
  getExecutions(params?: { skip?: number, limit?: number, status?: string }): Promise<PaginatedList<ExecutionListItem>> {
    return request.get('/agent/executions', { params })
  },

  getExecution(id: number): Promise<ExecutionResponse> {
    return request.get(`/agent/executions/${id}`)
  }
}
