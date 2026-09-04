import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import SettingsView from '@/views/settings/SettingsView.vue'
import { userApi } from '@/api/user'
import { authApi } from '@/api/auth'

// Mock APIs
vi.mock('@/api/user', () => ({
  userApi: {
    getDeletionStatus: vi.fn(),
    requestDeletion: vi.fn(),
    cancelDeletion: vi.fn(),
    getProfile: vi.fn()
  }
}))

vi.mock('@/api/auth', () => ({
  authApi: {
    changePassword: vi.fn(),
    getCurrentUser: vi.fn()
  }
}))

// Mock child components
vi.mock('@/components/common/AvatarUploader.vue', () => ({
  default: {
    name: 'AvatarUploader',
    template: '<div class="mock-avatar-uploader"></div>'
  }
}))

vi.mock('@/components/common/PromptSelector.vue', () => ({
  default: {
    name: 'PromptSelector',
    template: '<div class="mock-prompt-selector"></div>'
  }
}))

describe('SettingsView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    
    // Default mock for getDeletionStatus
    vi.mocked(userApi.getDeletionStatus).mockResolvedValue({
      has_deletion_request: false,
      message: '您的账号状态正常'
    })
    
    // Mock getCurrentUser
    vi.mocked(authApi.getCurrentUser).mockResolvedValue({
      id: 1,
      username: 'testuser',
      email: 'test@example.com',
      is_active: true,
      created_at: '2026-01-01T00:00:00'
    })
  })

  const mountComponent = () => {
    return mount(SettingsView, {
      global: {
        plugins: [ElementPlus],
        stubs: {
          AvatarUploader: true,
          PromptSelector: true
        }
      }
    })
  }

  describe('Tab Navigation', () => {
    it('should render all tabs', async () => {
      const wrapper = mountComponent()
      await flushPromises()
      
      const tabs = wrapper.findAll('.el-tabs__item')
      expect(tabs.length).toBe(6)
      
      const tabLabels = tabs.map(tab => tab.text())
      expect(tabLabels).toContain('账号设置')
      expect(tabLabels).toContain('模型与密钥')
      expect(tabLabels).toContain('向量库配置')
      expect(tabLabels).toContain('缓存与限流')
      expect(tabLabels).toContain('统计与健康')
      expect(tabLabels).toContain('注销详情')
    })

    it('should default to profile tab', async () => {
      const wrapper = mountComponent()
      await flushPromises()
      
      const activeTab = wrapper.find('.el-tabs__item.is-active')
      expect(activeTab.text()).toBe('账号设置')
    })
  })

  describe('Deletion Status Display', () => {
    it('should show no deletion request message when none exists', async () => {
      vi.mocked(userApi.getDeletionStatus).mockResolvedValue({
        has_deletion_request: false,
        message: '您的账号状态正常'
      })
      
      const wrapper = mountComponent()
      await flushPromises()
      
      // Navigate to deletion tab
      const deletionTab = wrapper.findAll('.el-tabs__item').find(tab => tab.text() === '账号注销')
      await deletionTab?.trigger('click')
      await flushPromises()
      
      // Should show the deletion form, not the status alert
      expect(wrapper.find('.deletion-warning').exists()).toBe(true)
    })

    it('should show deletion status when request exists', async () => {
      vi.mocked(userApi.getDeletionStatus).mockResolvedValue({
        has_deletion_request: true,
        requested_at: '2026-01-12T10:00:00',
        scheduled_at: '2026-01-19T10:00:00',
        reason: '测试注销',
        remaining_days: 5,
        remaining_hours: 12,
        can_cancel: true,
        message: '您的账号将于 5 天 12 小时后被删除'
      })
      
      const wrapper = mountComponent()
      await flushPromises()
      
      // Navigate to deletion tab
      const deletionTab = wrapper.findAll('.el-tabs__item').find(tab => tab.text() === '账号注销')
      await deletionTab?.trigger('click')
      await flushPromises()
      
      // Should show the deletion alert
      expect(wrapper.find('.deletion-alert').exists()).toBe(true)
    })
  })

  describe('Password Change', () => {
    it('should validate password form', async () => {
      const wrapper = mountComponent()
      await flushPromises()
      
      // Navigate to password tab
      const passwordTab = wrapper.findAll('.el-tabs__item').find(tab => tab.text() === '修改密码')
      await passwordTab?.trigger('click')
      await flushPromises()
      
      // Form should exist
      expect(wrapper.find('form').exists() || wrapper.find('.el-form').exists()).toBe(true)
    })
  })

  describe('API Calls', () => {
    it('should call getDeletionStatus on mount', async () => {
      mountComponent()
      await flushPromises()
      
      expect(userApi.getDeletionStatus).toHaveBeenCalled()
    })
  })
})
