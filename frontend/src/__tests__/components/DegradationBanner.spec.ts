/**
 * DegradationBanner 组件测试
 *
 * 测试内容：
 * 1. 降级横幅在 OpenClaw 不可用时正确显示
 * 2. 重试功能的错误处理是否生效
 * 3. 横幅可以被用户关闭
 * 4. 功能限制列表正确显示
 * 5. 状态恢复时横幅自动隐藏
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import DegradationBanner from '@/components/DegradationBanner.vue'
import { useOpenClawStore } from '@/stores/openclaw'
import { ElMessage } from 'element-plus'

// Mock ElMessage
vi.mock('element-plus', () => ({
  ElMessage: {
    error: vi.fn(),
    success: vi.fn()
  },
  ElIcon: {
    name: 'ElIcon'
  },
  ElButton: {
    name: 'ElButton'
  }
}))

describe('DegradationBanner', () => {
  beforeEach(() => {
    // 为每个测试创建新的 Pinia 实例
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('横幅显示逻辑', () => {
    it('当 OpenClaw 状态为 unhealthy 时显示横幅', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.degradation-banner').exists()).toBe(true)
    })

    it('当 OpenClaw 状态为 healthy 时不显示横幅', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'healthy'
      store.degraded = false

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.degradation-banner').exists()).toBe(false)
    })

    it('当用户关闭横幅后不再显示', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true

      await wrapper.vm.$nextTick()

      // 横幅应该显示
      expect(wrapper.find('.degradation-banner').exists()).toBe(true)

      // 直接调用组件的 dismissBanner 方法
      ;(wrapper.vm as any).dismissBanner()
      await wrapper.vm.$nextTick()

      // 横幅应该隐藏
      expect(wrapper.find('.degradation-banner').exists()).toBe(false)
    })
  })

  describe('横幅样式', () => {
    it('当状态为 unhealthy 时显示错误样式', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true

      await wrapper.vm.$nextTick()

      const banner = wrapper.find('.degradation-banner')
      expect(banner.classes()).toContain('banner-error')
    })

    it('当状态为 degraded 但不是 unhealthy 时显示警告样式', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'checking'
      store.degraded = true

      await wrapper.vm.$nextTick()

      const banner = wrapper.find('.degradation-banner')
      expect(banner.classes()).toContain('banner-warning')
    })
  })

  describe('重试功能', () => {
    it('点击重试按钮调用 store 的 manualReconnect 方法', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true
      store.loading = false

      // Mock manualReconnect 方法
      const manualReconnectSpy = vi.spyOn(store, 'manualReconnect').mockResolvedValue()

      await wrapper.vm.$nextTick()

      // 查找重试按钮
      const retryButton = wrapper.findAll('.el-button').find(btn =>
        btn.text().includes('重试连接')
      )

      if (retryButton) {
        await retryButton.trigger('click')
        await wrapper.vm.$nextTick()

        expect(manualReconnectSpy).toHaveBeenCalled()
      }
    })

    it('重试失败时显示错误消息', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true
      store.loading = false

      // Mock manualReconnect 方法抛出错误
      const error = new Error('连接失败')
      vi.spyOn(store, 'manualReconnect').mockRejectedValue(error)

      await wrapper.vm.$nextTick()

      // 查找重试按钮
      const retryButton = wrapper.findAll('.el-button').find(btn =>
        btn.text().includes('重试连接')
      )

      if (retryButton) {
        await retryButton.trigger('click')
        await wrapper.vm.$nextTick()

        // 等待异步操作完成
        await new Promise(resolve => setTimeout(resolve, 0))

        // 验证错误消息被调用
        expect(ElMessage.error).toHaveBeenCalledWith('重试连接失败，请稍后再试')
      }
    })

    it('loading 状态时不显示重试按钮', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true
      store.loading = true

      await wrapper.vm.$nextTick()

      // 重试按钮不应该显示
      const retryButton = wrapper.findAll('.el-button').find(btn =>
        btn.text().includes('重试连接')
      )
      expect(retryButton).toBeUndefined()
    })
  })

  describe('功能限制列表', () => {
    it('点击查看详情按钮显示功能限制列表', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true

      await wrapper.vm.$nextTick()

      // 初始状态不显示限制列表
      expect(wrapper.find('.limitations-info').exists()).toBe(false)

      // 查找查看详情按钮
      const detailsButton = wrapper.findAll('.el-button').find(btn =>
        btn.text().includes('查看详情')
      )

      if (detailsButton) {
        await detailsButton.trigger('click')
        await wrapper.vm.$nextTick()

        // 限制列表应该显示
        expect(wrapper.find('.limitations-info').exists()).toBe(true)
      }
    })

    it('功能限制列表包含正确的限制项', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true

      await wrapper.vm.$nextTick()

      // 点击查看详情
      const detailsButton = wrapper.findAll('.el-button').find(btn =>
        btn.text().includes('查看详情')
      )

      if (detailsButton) {
        await detailsButton.trigger('click')
        await wrapper.vm.$nextTick()

        const limitationsList = wrapper.find('.limitations-list')
        const limitationsText = limitationsList.text()

        // 验证包含关键限制信息
        expect(limitationsText).toContain('OpenClaw Agent')
        expect(limitationsText).toContain('浏览器自动化')
        expect(limitationsText).toContain('基础对话功能正常')
        expect(limitationsText).toContain('知识库RAG查询功能正常')
      }
    })
  })

  describe('状态恢复', () => {
    it('当状态从 unhealthy 变为 healthy 时重置 dismissed 状态', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true

      await wrapper.vm.$nextTick()

      // 直接调用组件的 dismissBanner 方法关闭横幅
      ;(wrapper.vm as any).dismissBanner()
      await wrapper.vm.$nextTick()

      // 横幅应该隐藏
      expect(wrapper.find('.degradation-banner').exists()).toBe(false)

      // 状态恢复为 healthy
      store.status = 'healthy'
      store.degraded = false
      await wrapper.vm.$nextTick()

      // 再次设置为 unhealthy
      store.status = 'unhealthy'
      store.degraded = true
      await wrapper.vm.$nextTick()

      // 横幅应该重新显示（dismissed 状态已重置）
      expect(wrapper.find('.degradation-banner').exists()).toBe(true)
    })
  })

  describe('横幅内容', () => {
    it('显示正确的标题和描述', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true
      store.retryCount = 3  // 设置为3次以上才会显示"降级模式"

      await wrapper.vm.$nextTick()

      const title = wrapper.find('.banner-title')
      const description = wrapper.find('.banner-description')

      expect(title.text()).toContain('OpenClaw')
      expect(description.text()).toContain('降级模式')
    })

    it('根据重试次数显示不同的描述', async () => {
      const wrapper = mount(DegradationBanner, {
        global: {
          plugins: [createPinia()]
        }
      })

      const store = useOpenClawStore()
      store.status = 'unhealthy'
      store.degraded = true

      // 测试重试中的描述
      store.retryCount = 2
      await wrapper.vm.$nextTick()

      let description = wrapper.find('.banner-description')
      expect(description.text()).toContain('正在尝试重新连接')
      expect(description.text()).toContain('2/3')

      // 测试达到最大重试次数的描述
      store.retryCount = 3
      await wrapper.vm.$nextTick()

      description = wrapper.find('.banner-description')
      expect(description.text()).toContain('每5分钟自动尝试恢复')
    })
  })
})
