/**
 * OpenClaw Store 测试
 *
 * 测试内容：
 * 1. 配置管理（加载、保存、更新）
 * 2. 健康检查功能
 * 3. 降级处理逻辑
 * 4. 恢复处理逻辑
 * 5. 计算属性（状态、颜色、文本）
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useOpenClawStore } from '@/stores/openclaw'
import { ElNotification } from 'element-plus'
import * as openclawApi from '@/api/openclaw'

// Mock ElNotification
vi.mock('element-plus', () => ({
  ElNotification: {
    warning: vi.fn(),
    success: vi.fn(),
    error: vi.fn()
  }
}))

// Mock openclaw API
vi.mock('@/api/openclaw', () => ({
  checkOpenClawHealth: vi.fn()
}))

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {}
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value
    },
    removeItem: (key: string) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    }
  }
})()

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock
})

describe('OpenClaw Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorageMock.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('初始状态', () => {
    it('应该有正确的初始状态', () => {
      const store = useOpenClawStore()

      expect(store.status).toBe('unknown')
      expect(store.version).toBe('')
      expect(store.uptime).toBe(0)
      expect(store.gatewayUrl).toBe('')
      expect(store.error).toBe('')
      expect(store.degraded).toBe(false)
      expect(store.degradedSince).toBeNull()
      expect(store.lastHealthCheck).toBeNull()
      expect(store.retryCount).toBe(0)
      expect(store.loading).toBe(false)
    })

    it('应该加载默认配置', () => {
      const store = useOpenClawStore()

      expect(store.config.showNotifications).toBe(true)
      expect(store.config.notificationDuration).toBe(3000)
      expect(store.config.autoRetry).toBe(true)
      expect(store.config.healthCheckInterval).toBe(30)
    })
  })

  describe('计算属性', () => {
    it('isHealthy 应该正确计算', () => {
      const store = useOpenClawStore()

      store.status = 'healthy'
      expect(store.isHealthy).toBe(true)

      store.status = 'unhealthy'
      expect(store.isHealthy).toBe(false)
    })

    it('isUnhealthy 应该正确计算', () => {
      const store = useOpenClawStore()

      store.status = 'unhealthy'
      expect(store.isUnhealthy).toBe(true)

      store.status = 'healthy'
      expect(store.isUnhealthy).toBe(false)
    })

    it('isUnknown 应该正确计算', () => {
      const store = useOpenClawStore()

      store.status = 'unknown'
      expect(store.isUnknown).toBe(true)

      store.status = 'healthy'
      expect(store.isUnknown).toBe(false)
    })

    it('statusColor 应该返回正确的颜色', () => {
      const store = useOpenClawStore()

      store.status = 'healthy'
      expect(store.statusColor).toBe('#52c41a')

      store.status = 'unhealthy'
      expect(store.statusColor).toBe('#ff4d4f')

      store.status = 'unknown'
      expect(store.statusColor).toBe('#faad14')
    })

    it('statusText 应该返回正确的文本', () => {
      const store = useOpenClawStore()

      store.status = 'healthy'
      expect(store.statusText).toBe('OpenClaw 已连接')

      store.status = 'unhealthy'
      expect(store.statusText).toBe('OpenClaw 不可用')

      store.status = 'unknown'
      expect(store.statusText).toBe('OpenClaw 连接中...')
    })
  })

  describe('配置管理', () => {
    it('应该从 localStorage 加载配置', () => {
      const savedConfig = {
        showNotifications: false,
        notificationDuration: 5000,
        autoRetry: false,
        healthCheckInterval: 60
      }
      localStorageMock.setItem('openclaw_config', JSON.stringify(savedConfig))

      const store = useOpenClawStore()

      expect(store.config.showNotifications).toBe(false)
      expect(store.config.notificationDuration).toBe(5000)
      expect(store.config.autoRetry).toBe(false)
      expect(store.config.healthCheckInterval).toBe(60)
    })

    it('应该保存配置到 localStorage', () => {
      const store = useOpenClawStore()

      store.updateConfig({
        showNotifications: false,
        healthCheckInterval: 60
      })

      const saved = localStorageMock.getItem('openclaw_config')
      expect(saved).toBeTruthy()

      const parsed = JSON.parse(saved!)
      expect(parsed.showNotifications).toBe(false)
      expect(parsed.healthCheckInterval).toBe(60)
    })

    it('updateConfig 应该合并配置', () => {
      const store = useOpenClawStore()

      store.updateConfig({
        showNotifications: false
      })

      expect(store.config.showNotifications).toBe(false)
      expect(store.config.autoRetry).toBe(true) // 保持默认值
    })

    it('加载配置失败时应该使用默认配置', () => {
      localStorageMock.setItem('openclaw_config', 'invalid json')

      const store = useOpenClawStore()

      expect(store.config.showNotifications).toBe(true)
      expect(store.config.autoRetry).toBe(true)
    })
  })

  describe('健康检查', () => {
    it('健康检查成功时应该更新状态', async () => {
      const store = useOpenClawStore()
      const mockResponse = {
        status: 'healthy' as const,
        version: 'v1.0.0',
        uptime: 3600,
        gateway_url: 'http://localhost:19001',
        error: ''
      }

      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue(mockResponse)

      await store.checkHealth()

      expect(store.status).toBe('healthy')
      expect(store.version).toBe('v1.0.0')
      expect(store.uptime).toBe(3600)
      expect(store.gatewayUrl).toBe('http://localhost:19001')
      expect(store.error).toBe('')
      expect(store.lastHealthCheck).toBeInstanceOf(Date)
    })

    it('健康检查失败时应该处理降级', async () => {
      const store = useOpenClawStore()

      vi.mocked(openclawApi.checkOpenClawHealth).mockRejectedValue(
        new Error('Connection failed')
      )

      await store.checkHealth()

      expect(store.status).toBe('unhealthy')
      expect(store.degraded).toBe(true)
      expect(store.retryCount).toBe(1)
    })

    it('健康检查时应该设置 loading 状态', async () => {
      const store = useOpenClawStore()

      vi.mocked(openclawApi.checkOpenClawHealth).mockImplementation(
        () => new Promise(resolve => setTimeout(resolve, 100))
      )

      const promise = store.checkHealth()
      expect(store.loading).toBe(true)

      await promise
      expect(store.loading).toBe(false)
    })
  })

  describe('降级处理', () => {
    it('首次降级时应该显示通知', async () => {
      const store = useOpenClawStore()

      vi.mocked(openclawApi.checkOpenClawHealth).mockRejectedValue(
        new Error('Connection failed')
      )

      await store.checkHealth()

      expect(ElNotification.warning).toHaveBeenCalledWith({
        title: 'OpenClaw 暂时不可用',
        message: '已切换到知识库模式，功能不受影响',
        duration: 5000
      })
    })

    it('降级时不显示通知如果配置关闭', async () => {
      const store = useOpenClawStore()
      store.updateConfig({ showNotifications: false })

      vi.mocked(openclawApi.checkOpenClawHealth).mockRejectedValue(
        new Error('Connection failed')
      )

      await store.checkHealth()

      expect(ElNotification.warning).not.toHaveBeenCalled()
    })

    it('降级时应该增加重试计数', async () => {
      const store = useOpenClawStore()

      vi.mocked(openclawApi.checkOpenClawHealth).mockRejectedValue(
        new Error('Connection failed')
      )

      await store.checkHealth()
      expect(store.retryCount).toBe(1)

      await store.checkHealth()
      expect(store.retryCount).toBe(2)
    })
  })

  describe('恢复处理', () => {
    it('从降级状态恢复时应该显示通知', async () => {
      const store = useOpenClawStore()

      // 先进入降级状态
      vi.mocked(openclawApi.checkOpenClawHealth).mockRejectedValue(
        new Error('Connection failed')
      )
      await store.checkHealth()
      expect(store.degraded).toBe(true)

      // 然后恢复
      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue({
        status: 'healthy',
        version: 'v1.0.0',
        uptime: 3600,
        gateway_url: 'http://localhost:19001',
        error: ''
      })
      await store.checkHealth()

      expect(ElNotification.success).toHaveBeenCalledWith({
        title: 'OpenClaw 已恢复',
        message: '现在可以使用完整功能',
        duration: 3000
      })
    })

    it('恢复时应该重置降级状态', async () => {
      const store = useOpenClawStore()

      // 先进入降级状态
      vi.mocked(openclawApi.checkOpenClawHealth).mockRejectedValue(
        new Error('Connection failed')
      )
      await store.checkHealth()

      store.degraded = true
      store.retryCount = 3

      // 然后恢复
      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue({
        status: 'healthy',
        version: 'v1.0.0',
        uptime: 3600,
        gateway_url: 'http://localhost:19001',
        error: ''
      })
      await store.checkHealth()

      expect(store.degraded).toBe(false)
      expect(store.degradedSince).toBeNull()
      expect(store.retryCount).toBe(0)
    })
  })

  describe('手动重新连接', () => {
    it('manualReconnect 应该重置重试计数', async () => {
      const store = useOpenClawStore()
      store.retryCount = 3

      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue({
        status: 'healthy',
        version: 'v1.0.0',
        uptime: 3600,
        gateway_url: 'http://localhost:19001',
        error: ''
      })

      await store.manualReconnect()

      expect(store.retryCount).toBe(0)
    })

    it('manualReconnect 应该执行健康检查', async () => {
      const store = useOpenClawStore()

      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue({
        status: 'healthy',
        version: 'v1.0.0',
        uptime: 3600,
        gateway_url: 'http://localhost:19001',
        error: ''
      })

      await store.manualReconnect()

      expect(openclawApi.checkOpenClawHealth).toHaveBeenCalled()
    })
  })

  describe('边界情况', () => {
    it('应该处理 API 返回的空值', async () => {
      const store = useOpenClawStore()

      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue({
        status: 'healthy',
        version: undefined,
        uptime: undefined,
        gateway_url: 'http://localhost:19001',
        error: undefined
      } as any)

      await store.checkHealth()

      expect(store.version).toBe('')
      expect(store.uptime).toBe(0)
      expect(store.error).toBe('')
    })

    it('应该处理连续的状态变化', async () => {
      const store = useOpenClawStore()

      // 健康 -> 不健康
      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue({
        status: 'healthy',
        version: 'v1.0.0',
        uptime: 3600,
        gateway_url: 'http://localhost:19001',
        error: ''
      })
      await store.checkHealth()
      expect(store.status).toBe('healthy')

      // 不健康
      vi.mocked(openclawApi.checkOpenClawHealth).mockRejectedValue(
        new Error('Connection failed')
      )
      await store.checkHealth()
      expect(store.status).toBe('unhealthy')
      expect(store.degraded).toBe(true)

      // 恢复健康
      vi.mocked(openclawApi.checkOpenClawHealth).mockResolvedValue({
        status: 'healthy',
        version: 'v1.0.0',
        uptime: 3600,
        gateway_url: 'http://localhost:19001',
        error: ''
      })
      await store.checkHealth()
      expect(store.status).toBe('healthy')
      expect(store.degraded).toBe(false)
    })
  })
})
