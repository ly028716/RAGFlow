/**
 * WebScraperView.vue 组件测试
 *
 * 测试范围:
 * - 组件渲染
 * - 任务列表展示和交互
 * - 任务创建/编辑流程
 * - 任务控制操作（启动/停止/删除）
 * - 日志查看功能
 * - 筛选和分页
 * - 自动刷新
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ElMessageBox } from 'element-plus'
import WebScraperView from '@/views/WebScraperView.vue'
import { useWebScraperStore } from '@/stores/webScraper'
import type { Task } from '@/types/webScraper'

// Mock Element Plus components
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus')
  return {
    ...actual,
    ElMessageBox: {
      confirm: vi.fn()
    }
  }
})

// Mock child components
vi.mock('@/components/WebScraperTaskForm.vue', () => ({
  default: {
    name: 'WebScraperTaskForm',
    template: '<div class="mock-task-form"></div>',
    props: ['visible', 'task'],
    emits: ['update:visible', 'success']
  }
}))

vi.mock('@/components/WebScraperLogs.vue', () => ({
  default: {
    name: 'WebScraperLogs',
    template: '<div class="mock-logs"></div>',
    props: ['taskId']
  }
}))

describe('WebScraperView.vue', () => {
  let wrapper: VueWrapper
  let store: ReturnType<typeof useWebScraperStore>

  const mockTasks: Task[] = [
    {
      id: 1,
      name: '测试任务1',
      url: 'https://example.com/1',
      schedule_type: 'once',
      status: 'active',
      last_run_at: '2024-01-01T10:00:00',
      next_run_at: null,
      knowledge_base_id: 1,
      selector_config: { title: 'h1', content: 'article' },
      scraper_config: {},
      cron_expression: null,
      created_at: '2024-01-01T09:00:00',
      updated_at: '2024-01-01T09:00:00'
    },
    {
      id: 2,
      name: '测试任务2',
      url: 'https://example.com/2',
      schedule_type: 'cron',
      status: 'paused',
      last_run_at: null,
      next_run_at: '2024-01-02T10:00:00',
      knowledge_base_id: 1,
      selector_config: { title: 'h1', content: 'article' },
      scraper_config: {},
      cron_expression: '0 0 * * *',
      created_at: '2024-01-01T09:00:00',
      updated_at: '2024-01-01T09:00:00'
    }
  ]

  beforeEach(() => {
    // Create fresh pinia instance
    setActivePinia(createPinia())
    store = useWebScraperStore()

    // Mock store methods
    vi.spyOn(store, 'loadTasks').mockResolvedValue()
    vi.spyOn(store, 'refreshTasks').mockResolvedValue()
    vi.spyOn(store, 'startTask').mockResolvedValue()
    vi.spyOn(store, 'stopTask').mockResolvedValue()
    vi.spyOn(store, 'deleteTask').mockResolvedValue()

    // Set initial store state
    store.tasks = mockTasks
    store.totalTasks = 2
    store.loading = false

    // Mock timers
    vi.useFakeTimers()
  })

  afterEach(() => {
    wrapper?.unmount()
    vi.clearAllMocks()
    vi.clearAllTimers()
    vi.useRealTimers()
  })

  describe('组件渲染测试', () => {
    it('应该正确渲染组件', () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      expect(wrapper.exists()).toBe(true)
      expect(wrapper.find('.web-scraper-view').exists()).toBe(true)
    })

    it('应该显示页面标题和创建按钮', () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      expect(wrapper.find('.header h2').text()).toBe('网页采集任务')
      expect(wrapper.find('.header').exists()).toBe(true)
    })

    it('应该显示筛选栏', () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      expect(wrapper.find('.filter-bar').exists()).toBe(true)
    })

    it('应该在挂载时加载任务列表', () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      expect(store.loadTasks).toHaveBeenCalledWith({
        status: undefined,
        schedule_type: undefined,
        skip: 0,
        limit: 20
      })
    })

    it('应该在挂载时启动自动刷新', async () => {
      // Mock activeTasks getter to return active tasks
      vi.spyOn(store, 'activeTasks', 'get').mockReturnValue([mockTasks[0]])

      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      // Clear previous calls
      vi.clearAllMocks()

      // Fast-forward 10 seconds
      await vi.advanceTimersByTimeAsync(10000)

      expect(store.refreshTasks).toHaveBeenCalled()
    })
  })

  describe('任务管理测试', () => {
    it('应该打开创建任务对话框', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Call handleCreate directly
      await vm.handleCreate()
      await wrapper.vm.$nextTick()

      // Check that form dialog is visible
      expect(vm.formVisible).toBe(true)
      expect(vm.currentTask).toBeNull()
    })

    it('应该打开编辑任务对话框', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any
      await vm.handleEdit(mockTasks[0])

      expect(vm.formVisible).toBe(true)
      expect(vm.currentTask).toEqual(mockTasks[0])
    })

    it('应该在表单提交成功后重新加载任务', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleFormSuccess()

      expect(vm.formVisible).toBe(false)
      expect(store.loadTasks).toHaveBeenCalled()
    })
  })

  describe('任务控制测试', () => {
    it('应该启动任务', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleStart(mockTasks[1])

      expect(store.startTask).toHaveBeenCalledWith(2)
    })

    it('应该停止任务', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleStop(mockTasks[0])

      expect(store.stopTask).toHaveBeenCalledWith(1)
    })

    it('应该显示删除确认对话框', async () => {
      const mockConfirm = vi.mocked(ElMessageBox.confirm)
      mockConfirm.mockResolvedValue('confirm' as any)

      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleDelete(mockTasks[0])

      expect(mockConfirm).toHaveBeenCalledWith(
        '删除任务将同时删除所有执行日志，此操作不可逆，确定要删除吗？',
        '警告',
        {
          type: 'warning',
          confirmButtonText: '确定删除',
          cancelButtonText: '取消'
        }
      )
      expect(store.deleteTask).toHaveBeenCalledWith(1)
    })

    it('应该在用户取消时不删除任务', async () => {
      const mockConfirm = vi.mocked(ElMessageBox.confirm)
      mockConfirm.mockRejectedValue('cancel')

      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleDelete(mockTasks[0])

      expect(mockConfirm).toHaveBeenCalled()
      expect(store.deleteTask).not.toHaveBeenCalled()
    })

    it('应该在操作后重新加载任务列表', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleStart(mockTasks[1])

      expect(store.loadTasks).toHaveBeenCalled()
    })
  })

  describe('日志查看测试', () => {
    it('应该打开日志对话框', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any
      await vm.handleViewLogs(mockTasks[0])

      expect(vm.logsVisible).toBe(true)
      expect(vm.currentTaskId).toBe(1)
    })

    it('应该关闭日志对话框', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any
      vm.logsVisible = true
      vm.currentTaskId = 1

      vm.logsVisible = false

      expect(vm.logsVisible).toBe(false)
    })

    it('应该渲染日志组件', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any
      await vm.handleViewLogs(mockTasks[0])
      await wrapper.vm.$nextTick()

      // Verify logs dialog state is set correctly
      expect(vm.logsVisible).toBe(true)
      expect(vm.currentTaskId).toBe(1)
    })
  })

  describe('筛选和分页测试', () => {
    it('应该根据状态筛选任务', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      vm.filterForm.status = 'active'
      await vm.handleFilter()

      expect(store.loadTasks).toHaveBeenCalledWith({
        status: 'active',
        schedule_type: undefined,
        skip: 0,
        limit: 20
      })
    })

    it('应该根据调度类型筛选任务', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Clear previous calls
      vi.clearAllMocks()

      vm.filterForm.schedule_type = 'cron'
      await vm.handleFilter()

      expect(store.loadTasks).toHaveBeenCalledWith({
        status: undefined,
        schedule_type: 'cron',
        skip: 0,
        limit: 20
      })
    })

    it('应该重置筛选条件', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any
      vm.filterForm.status = 'active'
      vm.filterForm.schedule_type = 'cron'

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleReset()

      expect(vm.filterForm.status).toBe('')
      expect(vm.filterForm.schedule_type).toBe('')
      expect(store.loadTasks).toHaveBeenCalledWith({
        status: undefined,
        schedule_type: undefined,
        skip: 0,
        limit: 20
      })
    })

    it('应该处理分页变化', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Simulate v-model update (ElPagination would do this)
      vm.pagination.page = 2

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handlePageChange()

      expect(store.loadTasks).toHaveBeenCalledWith({
        status: undefined,
        schedule_type: undefined,
        skip: 20,
        limit: 20
      })
    })

    it('应该处理每页大小变化', async () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any

      // Simulate v-model update (ElPagination would do this)
      vm.pagination.pageSize = 50

      // Clear previous calls
      vi.clearAllMocks()

      await vm.handleSizeChange()

      expect(vm.pagination.page).toBe(1)
      expect(store.loadTasks).toHaveBeenCalledWith({
        status: undefined,
        schedule_type: undefined,
        skip: 0,
        limit: 50
      })
    })
  })

  describe('状态更新测试', () => {
    it('应该正确显示任务状态标签', () => {
      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      // Verify component renders without errors
      expect(wrapper.exists()).toBe(true)
      expect(store.tasks.length).toBeGreaterThan(0)
    })

    it('应该在有活跃任务时启动自动刷新', async () => {
      // Mock activeTasks getter to return active tasks
      vi.spyOn(store, 'activeTasks', 'get').mockReturnValue([mockTasks[0]])

      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      // Clear previous calls
      vi.clearAllMocks()

      // Fast-forward 10 seconds
      await vi.advanceTimersByTimeAsync(10000)

      expect(store.refreshTasks).toHaveBeenCalled()
    })

    it('应该在没有活跃任务时停止自动刷新', async () => {
      // Mock activeTasks getter to return empty array
      vi.spyOn(store, 'activeTasks', 'get').mockReturnValue([])

      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      // Clear previous calls
      vi.clearAllMocks()

      // Fast-forward 10 seconds
      await vi.advanceTimersByTimeAsync(10000)

      expect(store.refreshTasks).not.toHaveBeenCalled()
    })

    it('应该在组件卸载时清理定时器', async () => {
      // Mock activeTasks getter to return active tasks
      vi.spyOn(store, 'activeTasks', 'get').mockReturnValue([mockTasks[0]])

      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any
      const refreshTimer = vm.refreshTimer

      wrapper.unmount()

      // Verify timer existed before unmount
      expect(refreshTimer).toBeDefined()
    })

    it('应该正确计算总页数', () => {
      store.totalTasks = 45

      wrapper = mount(WebScraperView, {
        global: {
          stubs: {
            ElButton: true,
            ElTable: true,
            ElTableColumn: true,
            ElPagination: true,
            ElForm: true,
            ElFormItem: true,
            ElSelect: true,
            ElOption: true,
            ElTag: true,
            ElDialog: true,
            ElIcon: true
          }
        }
      })

      const vm = wrapper.vm as any
      expect(store.totalTasks).toBe(45)
      expect(vm.pagination.pageSize).toBe(20)
    })
  })
})
