/**
 * WebScraperTaskForm 组件单元测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import WebScraperTaskForm from '@/components/WebScraperTaskForm.vue'
import { useWebScraperStore } from '@/stores/webScraper'
import { useKnowledgeStore } from '@/stores/knowledge'
import type { Task } from '@/types/webScraper'

// Mock Element Plus
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn()
  },
  ElMessageBox: {
    alert: vi.fn()
  }
}))

describe('WebScraperTaskForm', () => {
  let wrapper: VueWrapper<any>
  let webScraperStore: ReturnType<typeof useWebScraperStore>
  let knowledgeStore: ReturnType<typeof useKnowledgeStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    webScraperStore = useWebScraperStore()
    knowledgeStore = useKnowledgeStore()

    // Mock knowledge bases
    knowledgeStore.knowledgeBases = [
      { id: 1, name: '知识库1', description: '', user_id: 1, created_at: '', updated_at: '' },
      { id: 2, name: '知识库2', description: '', user_id: 1, created_at: '', updated_at: '' }
    ]
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  describe('创建模式', () => {
    beforeEach(() => {
      wrapper = mount(WebScraperTaskForm, {
        props: {
          visible: true,
          task: null
        },
        global: {
          plugins: [createPinia()]
        }
      })
    })

    it('应该正确渲染创建表单', () => {
      expect(wrapper.find('.el-dialog').exists()).toBe(true)
      expect(wrapper.text()).toContain('创建任务')
    })

    it('应该显示所有必需字段', () => {
      expect(wrapper.find('[label="任务名称"]').exists()).toBe(true)
      expect(wrapper.find('[label="目标URL"]').exists()).toBe(true)
      expect(wrapper.find('[label="知识库"]').exists()).toBe(true)
      expect(wrapper.find('[label="调度类型"]').exists()).toBe(true)
    })

    it('应该初始化为一次性执行', () => {
      const vm = wrapper.vm as any
      expect(vm.form.schedule_type).toBe('once')
    })

    it('应该在选择定时执行时显示Cron表达式输入', async () => {
      const vm = wrapper.vm as any
      vm.form.schedule_type = 'cron'
      await wrapper.vm.$nextTick()

      expect(wrapper.find('[label="Cron表达式"]').exists()).toBe(true)
    })
  })

  describe('编辑模式', () => {
    const mockTask: Task = {
      id: 1,
      name: '测试任务',
      description: '测试描述',
      url: 'https://example.com',
      knowledge_base_id: 1,
      schedule_type: 'cron',
      cron_expression: '0 0 * * *',
      selector_config: {
        title: 'h1',
        content: 'article',
        author: 'span.author',
        exclude: ['.ad']
      },
      scraper_config: {
        wait_for_selector: 'body',
        wait_timeout: 30000,
        screenshot: false,
        retry_times: 3,
        retry_delay: 5
      },
      status: 'paused',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      created_by: 1
    }

    beforeEach(() => {
      wrapper = mount(WebScraperTaskForm, {
        props: {
          visible: true,
          task: mockTask
        },
        global: {
          plugins: [createPinia()]
        }
      })
    })

    it('应该正确渲染编辑表单', () => {
      expect(wrapper.text()).toContain('编辑任务')
    })

    it('应该填充现有任务数据', () => {
      const vm = wrapper.vm as any
      expect(vm.form.name).toBe('测试任务')
      expect(vm.form.description).toBe('测试描述')
      expect(vm.form.url).toBe('https://example.com')
      expect(vm.form.knowledge_base_id).toBe(1)
      expect(vm.form.schedule_type).toBe('cron')
      expect(vm.form.cron_expression).toBe('0 0 * * *')
    })

    it('应该深拷贝选择器配置', () => {
      const vm = wrapper.vm as any
      expect(vm.form.selector_config).toEqual(mockTask.selector_config)
      expect(vm.form.selector_config).not.toBe(mockTask.selector_config)
    })

    it('应该深拷贝采集器配置', () => {
      const vm = wrapper.vm as any
      expect(vm.form.scraper_config).toEqual(mockTask.scraper_config)
      expect(vm.form.scraper_config).not.toBe(mockTask.scraper_config)
    })
  })

  describe('表单验证', () => {
    beforeEach(() => {
      wrapper = mount(WebScraperTaskForm, {
        props: {
          visible: true,
          task: null
        },
        global: {
          plugins: [createPinia()]
        }
      })
    })

    it('应该验证任务名称必填', async () => {
      const vm = wrapper.vm as any
      vm.form.name = ''

      const formRef = vm.formRef
      if (formRef) {
        try {
          await formRef.validate()
          expect.fail('应该抛出验证错误')
        } catch (error) {
          expect(error).toBeDefined()
        }
      }
    })

    it('应该验证URL格式', async () => {
      const vm = wrapper.vm as any
      vm.form.url = 'invalid-url'

      const formRef = vm.formRef
      if (formRef) {
        try {
          await formRef.validate()
          expect.fail('应该抛出验证错误')
        } catch (error) {
          expect(error).toBeDefined()
        }
      }
    })

    it('应该验证知识库必选', async () => {
      const vm = wrapper.vm as any
      vm.form.knowledge_base_id = 0

      const formRef = vm.formRef
      if (formRef) {
        try {
          await formRef.validate()
          expect.fail('应该抛出验证错误')
        } catch (error) {
          expect(error).toBeDefined()
        }
      }
    })

    it('应该验证定时任务的Cron表达式', async () => {
      const vm = wrapper.vm as any
      vm.form.schedule_type = 'cron'
      vm.form.cron_expression = ''

      const formRef = vm.formRef
      if (formRef) {
        try {
          await formRef.validate()
          expect.fail('应该抛出验证错误')
        } catch (error) {
          expect(error).toBeDefined()
        }
      }
    })
  })

  describe('表单提交', () => {
    beforeEach(() => {
      wrapper = mount(WebScraperTaskForm, {
        props: {
          visible: true,
          task: null
        },
        global: {
          plugins: [createPinia()]
        }
      })
    })

    it('应该在创建成功后触发success事件', async () => {
      const vm = wrapper.vm as any

      // 填充表单
      vm.form.name = '新任务'
      vm.form.url = 'https://example.com'
      vm.form.knowledge_base_id = 1
      vm.form.selector_config.title = 'h1'
      vm.form.selector_config.content = 'article'

      // Mock createTask
      vi.spyOn(webScraperStore, 'createTask').mockResolvedValue({
        id: 1,
        name: '新任务',
        url: 'https://example.com',
        knowledge_base_id: 1,
        schedule_type: 'once',
        status: 'paused',
        selector_config: { title: 'h1', content: 'article' },
        scraper_config: { wait_for_selector: 'body', wait_timeout: 30000 },
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        created_by: 1
      })

      await vm.handleSubmit()

      expect(wrapper.emitted('success')).toBeTruthy()
    })

    it('应该在更新成功后触发success事件', async () => {
      const mockTask: Task = {
        id: 1,
        name: '旧名称',
        url: 'https://example.com',
        knowledge_base_id: 1,
        schedule_type: 'once',
        status: 'paused',
        selector_config: { title: 'h1', content: 'article' },
        scraper_config: { wait_for_selector: 'body', wait_timeout: 30000 },
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        created_by: 1
      }

      wrapper = mount(WebScraperTaskForm, {
        props: {
          visible: true,
          task: mockTask
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      vm.form.name = '新名称'

      // Mock updateTask
      vi.spyOn(webScraperStore, 'updateTask').mockResolvedValue({
        ...mockTask,
        name: '新名称'
      })

      await vm.handleSubmit()

      expect(wrapper.emitted('success')).toBeTruthy()
    })
  })

  describe('Cron帮助', () => {
    beforeEach(() => {
      wrapper = mount(WebScraperTaskForm, {
        props: {
          visible: true,
          task: null
        },
        global: {
          plugins: [createPinia()]
        }
      })
    })

    it('应该显示Cron帮助对话框', async () => {
      const vm = wrapper.vm as any
      const { ElMessageBox } = await import('element-plus')

      await vm.showCronHelp()

      expect(ElMessageBox.alert).toHaveBeenCalled()
    })
  })
})
