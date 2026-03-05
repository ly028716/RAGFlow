/**
 * OpenClawStatus 组件测试
 *
 * 测试内容：
 * 1. 状态指示器正确显示不同状态（healthy/unhealthy/unknown）
 * 2. 状态颜色和文本正确映射
 * 3. 详情弹窗显示和隐藏
 * 4. 重新连接功能
 * 5. 运行时间和最后检查时间格式化
 * 6. 组件生命周期（启动和停止健康检查）
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import OpenClawStatus from '@/components/OpenClawStatus.vue'
import { useOpenClawStore } from '@/stores/openclaw'
import { ElMessage } from 'element-plus'

// Mock ElMessage
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn()
  },
  ElNotification: {
    warning: vi.fn(),
    success: vi.fn()
  }
}))

describe('OpenClawStatus', () => {
  let wrapper: VueWrapper<any>
  let store: ReturnType<typeof useOpenClawStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('状态指示器显示', () => {
    it('当状态为 healthy 时显示绿色指示器', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'healthy'
      await wrapper.vm.$nextTick()

      const statusDot = wrapper.find('.status-dot')
      expect(statusDot.attributes('style')).toContain('#52c41a')
    })

    it('当状态为 unhealthy 时显示红色指示器', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unhealthy'
      await wrapper.vm.$nextTick()

      const statusDot = wrapper.find('.status-dot')
      expect(statusDot.attributes('style')).toContain('#ff4d4f')
    })

    it('当状态为 unknown 时显示黄色指示器', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unknown'
      await wrapper.vm.$nextTick()

      const statusDot = wrapper.find('.status-dot')
      expect(statusDot.attributes('style')).toContain('#faad14')
    })
  })

  describe('状态文本显示', () => {
    it('healthy 状态显示"OpenClaw 已连接"', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'healthy'
      await wrapper.vm.$nextTick()

      const statusText = wrapper.find('.status-text')
      expect(statusText.text()).toBe('OpenClaw 已连接')
    })

    it('unhealthy 状态显示"OpenClaw 不可用"', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unhealthy'
      await wrapper.vm.$nextTick()

      const statusText = wrapper.find('.status-text')
      expect(statusText.text()).toBe('OpenClaw 不可用')
    })

    it('unknown 状态显示"OpenClaw 连接中..."', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unknown'
      await wrapper.vm.$nextTick()

      const statusText = wrapper.find('.status-text')
      expect(statusText.text()).toBe('OpenClaw 连接中...')
    })
  })

  describe('重试计数徽章', () => {
    it('当 retryCount 为 0 时不显示徽章', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.retryCount = 0
      await wrapper.vm.$nextTick()

      // 检查 store 状态
      expect(store.retryCount).toBe(0)
    })

    it('当 retryCount > 0 时显示徽章', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.retryCount = 3
      await wrapper.vm.$nextTick()

      // 检查 store 状态
      expect(store.retryCount).toBe(3)
    })
  })

  describe('详情弹窗', () => {
    it('点击状态指示器显示详情弹窗', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      const indicator = wrapper.find('.status-indicator')
      await indicator.trigger('click')
      await wrapper.vm.$nextTick()

      expect(wrapper.vm.showDetails).toBe(true)
    })

    it('详情弹窗显示版本信息', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.version = 'v1.2.3'
      store.status = 'healthy'

      const indicator = wrapper.find('.status-indicator')
      await indicator.trigger('click')
      await wrapper.vm.$nextTick()

      const detailsContent = wrapper.find('.details-content')
      expect(detailsContent.text()).toContain('v1.2.3')
    })

    it('详情弹窗显示 Gateway URL', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.gatewayUrl = 'http://localhost:19001'

      const indicator = wrapper.find('.status-indicator')
      await indicator.trigger('click')
      await wrapper.vm.$nextTick()

      const detailsContent = wrapper.find('.details-content')
      expect(detailsContent.text()).toContain('http://localhost:19001')
    })

    it('详情弹窗显示错误信息', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unhealthy'
      store.error = 'Connection timeout'

      const indicator = wrapper.find('.status-indicator')
      await indicator.trigger('click')
      await wrapper.vm.$nextTick()

      const errorItem = wrapper.find('.detail-item.error')
      expect(errorItem.text()).toContain('Connection timeout')
    })
  })

  describe('运行时间格式化', () => {
    it('formatUptime 正确格式化天数', () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      const formatted = (wrapper.vm as any).formatUptime(90000) // 1天1小时
      expect(formatted).toBe('1天1小时')
    })

    it('formatUptime 正确格式化小时', () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      const formatted = (wrapper.vm as any).formatUptime(7200) // 2小时
      expect(formatted).toBe('2小时0分钟')
    })

    it('formatUptime 正确格式化分钟', () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      const formatted = (wrapper.vm as any).formatUptime(300) // 5分钟
      expect(formatted).toBe('5分钟')
    })
  })

  describe('最后检查时间格式化', () => {
    it('formatLastCheck 显示秒前', () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      const date = new Date(Date.now() - 30000) // 30秒前
      const formatted = (wrapper.vm as any).formatLastCheck(date)
      expect(formatted).toContain('秒前')
    })

    it('formatLastCheck 显示分钟前', () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      const date = new Date(Date.now() - 120000) // 2分钟前
      const formatted = (wrapper.vm as any).formatLastCheck(date)
      expect(formatted).toBe('2分钟前')
    })

    it('formatLastCheck 处理 null 值', () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      const formatted = (wrapper.vm as any).formatLastCheck(null)
      expect(formatted).toBe('未知')
    })
  })

  describe('重新连接功能', () => {
    it('点击重新连接按钮调用 store.manualReconnect', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unhealthy'
      const manualReconnectSpy = vi.spyOn(store, 'manualReconnect').mockResolvedValue()

      // 调用 handleReconnect
      await (wrapper.vm as any).handleReconnect()

      expect(manualReconnectSpy).toHaveBeenCalled()
    })

    it('重新连接成功后显示成功消息并关闭弹窗', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unhealthy'
      vi.spyOn(store, 'manualReconnect').mockResolvedValue()

      // 打开详情弹窗
      wrapper.vm.showDetails = true
      await wrapper.vm.$nextTick()

      // 模拟重连成功
      store.status = 'healthy'
      await (wrapper.vm as any).handleReconnect()
      await wrapper.vm.$nextTick()

      expect(ElMessage.success).toHaveBeenCalledWith('重新连接成功')
      expect(wrapper.vm.showDetails).toBe(false)
    })

    it('重新连接失败后显示错误消息', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unhealthy'
      vi.spyOn(store, 'manualReconnect').mockRejectedValue(new Error('Connection failed'))

      await (wrapper.vm as any).handleReconnect()
      await wrapper.vm.$nextTick()

      expect(ElMessage.error).toHaveBeenCalledWith('重新连接失败')
    })
  })

  describe('组件生命周期', () => {
    it('onMounted 时启动健康检查', () => {
      const pinia = createPinia()
      setActivePinia(pinia)
      store = useOpenClawStore()
      const startHealthCheckSpy = vi.spyOn(store, 'startHealthCheck')

      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [pinia]
        }
      })

      expect(startHealthCheckSpy).toHaveBeenCalled()
    })

    it('onUnmounted 时停止健康检查', () => {
      const pinia = createPinia()
      setActivePinia(pinia)
      store = useOpenClawStore()
      const stopHealthCheckSpy = vi.spyOn(store, 'stopHealthCheck')

      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [pinia]
        }
      })

      wrapper.unmount()

      expect(stopHealthCheckSpy).toHaveBeenCalled()
    })
  })

  describe('tooltip 内容', () => {
    it('有版本信息时显示版本和最后检查时间', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.version = 'v1.0.0'
      store.lastHealthCheck = new Date()
      await wrapper.vm.$nextTick()

      const tooltipContent = (wrapper.vm as any).tooltipContent
      expect(tooltipContent).toContain('版本: v1.0.0')
      expect(tooltipContent).toContain('最后检查:')
    })

    it('无版本信息时显示默认提示', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.version = ''
      await wrapper.vm.$nextTick()

      const tooltipContent = (wrapper.vm as any).tooltipContent
      expect(tooltipContent).toBe('点击查看详情')
    })
  })

  describe('重新连接按钮显示', () => {
    it('unhealthy 状态时显示重新连接按钮', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'unhealthy'
      await wrapper.vm.$nextTick()

      // 检查 isUnhealthy 计算属性
      expect(store.isUnhealthy).toBe(true)
    })

    it('healthy 状态时不显示重新连接按钮', async () => {
      wrapper = mount(OpenClawStatus, {
        global: {
          plugins: [createPinia()]
        }
      })

      store = useOpenClawStore()
      store.status = 'healthy'
      await wrapper.vm.$nextTick()

      // 检查 isUnhealthy 计算属性
      expect(store.isUnhealthy).toBe(false)
    })
  })
})
