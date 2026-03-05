/**
 * WebScraperLogs 组件单元测试
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import WebScraperLogs from '@/components/WebScraperLogs.vue'
import { useWebScraperStore } from '@/stores/webScraper'
import { webScraperApi } from '@/api/webScraper'
import type { Log, LogStatisticsResponse } from '@/types/webScraper'

// Mock API
vi.mock('@/api/webScraper', () => ({
  webScraperApi: {
    getLogs: vi.fn(),
    getLogStatistics: vi.fn()
  }
}))

describe('WebScraperLogs', () => {
  let wrapper: VueWrapper<any>
  let store: ReturnType<typeof useWebScraperStore>

  const mockLogs: Log[] = [
    {
      id: 1,
      task_id: 1,
      status: 'success',
      start_time: '2026-01-01T00:00:00Z',
      end_time: '2026-01-01T00:01:00Z',
      pages_scraped: 5,
      documents_created: 5,
      execution_details: {
        urls_processed: ['https://example.com/page1'],
        processing_time: {
          scraping: 10.5,
          processing: 5.2,
          storing: 2.3,
          total: 18.0
        },
        documents: [
          {
            title: '文档1',
            url: 'https://example.com/page1',
            document_id: 123
          }
        ],
        errors: []
      }
    },
    {
      id: 2,
      task_id: 1,
      status: 'running',
      start_time: '2026-01-01T01:00:00Z',
      pages_scraped: 2,
      documents_created: 2
    },
    {
      id: 3,
      task_id: 1,
      status: 'failed',
      start_time: '2026-01-01T02:00:00Z',
      end_time: '2026-01-01T02:00:30Z',
      pages_scraped: 0,
      documents_created: 0,
      error_message: '网络连接超时'
    }
  ]

  const mockStatistics: LogStatisticsResponse = {
    total: 10,
    success: 7,
    failed: 2,
    running: 1,
    success_rate: 70.0
  }

  beforeEach(() => {
    setActivePinia(createPinia())
    store = useWebScraperStore()

    // Mock API responses
    vi.mocked(webScraperApi.getLogs).mockResolvedValue({
      items: mockLogs,
      total: 3
    })
    vi.mocked(webScraperApi.getLogStatistics).mockResolvedValue(mockStatistics)
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
    vi.clearAllMocks()
  })

  describe('组件渲染', () => {
    it('应该正确渲染日志列表', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      await wrapper.vm.$nextTick()

      expect(wrapper.find('.web-scraper-logs').exists()).toBe(true)
      expect(wrapper.find('.el-table').exists()).toBe(true)
    })

    it('应该显示统计信息', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      await wrapper.vm.$nextTick()

      const vm = wrapper.vm as any
      expect(vm.statistics).toEqual(mockStatistics)
    })

    it('应该显示筛选栏', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      expect(wrapper.find('.filter-bar').exists()).toBe(true)
    })

    it('应该显示分页组件', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      expect(wrapper.find('.pagination').exists()).toBe(true)
    })
  })

  describe('数据加载', () => {
    it('应该在挂载时加载日志', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      await wrapper.vm.$nextTick()

      expect(webScraperApi.getLogs).toHaveBeenCalledWith(1, expect.any(Object))
      expect(webScraperApi.getLogStatistics).toHaveBeenCalledWith(1)
    })

    it('应该在挂载时启动自动刷新', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      await wrapper.vm.$nextTick()

      const vm = wrapper.vm as any
      expect(vm.refreshTimer).not.toBeNull()
    })

    it('应该在卸载时停止自动刷新', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      await wrapper.vm.$nextTick()

      const vm = wrapper.vm as any
      const timerId = vm.refreshTimer

      wrapper.unmount()

      // 验证定时器已清除
      expect(vm.refreshTimer).toBeNull()
    })
  })

  describe('状态显示', () => {
    it('应该正确显示成功状态', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      expect(vm.getStatusType('success')).toBe('success')
      expect(vm.getStatusText('success')).toBe('成功')
    })

    it('应该正确显示运行中状态', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      expect(vm.getStatusType('running')).toBe('warning')
      expect(vm.getStatusText('running')).toBe('运行中')
    })

    it('应该正确显示失败状态', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      expect(vm.getStatusType('failed')).toBe('danger')
      expect(vm.getStatusText('failed')).toBe('失败')
    })
  })

  describe('时间格式化', () => {
    it('应该正确格式化日期时间', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      const formatted = vm.formatDateTime('2026-01-01T00:00:00Z')

      expect(formatted).toContain('2026')
      expect(formatted).toContain('01')
    })

    it('应该正确计算执行时长', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      const log: Log = {
        id: 1,
        task_id: 1,
        status: 'success',
        start_time: '2026-01-01T00:00:00Z',
        end_time: '2026-01-01T00:01:00Z',
        pages_scraped: 5,
        documents_created: 5
      }

      const duration = vm.getDuration(log)
      expect(duration).toContain('秒')
    })

    it('应该处理未完成的日志', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      const log: Log = {
        id: 1,
        task_id: 1,
        status: 'running',
        start_time: '2026-01-01T00:00:00Z',
        pages_scraped: 2,
        documents_created: 2
      }

      const duration = vm.getDuration(log)
      expect(duration).toBe('-')
    })
  })

  describe('筛选功能', () => {
    it('应该支持按状态筛选', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      vm.filterStatus = 'success'

      await vm.handleFilter()

      expect(webScraperApi.getLogs).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          status: 'success'
        })
      )
    })

    it('应该在筛选时重置页码', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      vm.pagination.page = 3

      await vm.handleFilter()

      expect(vm.pagination.page).toBe(1)
    })
  })

  describe('分页功能', () => {
    it('应该支持页码变化', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      vm.pagination.page = 2

      await vm.handlePageChange()

      expect(webScraperApi.getLogs).toHaveBeenCalled()
    })

    it('应该支持页大小变化', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      const vm = wrapper.vm as any
      vm.pagination.pageSize = 50

      await vm.handleSizeChange()

      expect(vm.pagination.page).toBe(1)
      expect(webScraperApi.getLogs).toHaveBeenCalled()
    })
  })

  describe('刷新功能', () => {
    it('应该支持手动刷新', async () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      vi.clearAllMocks()

      const vm = wrapper.vm as any
      await vm.handleRefresh()

      expect(webScraperApi.getLogs).toHaveBeenCalled()
      expect(webScraperApi.getLogStatistics).toHaveBeenCalled()
    })

    it('应该在有运行中日志时自动刷新', async () => {
      store.logs = [
        {
          id: 1,
          task_id: 1,
          status: 'running',
          start_time: '2026-01-01T00:00:00Z',
          pages_scraped: 2,
          documents_created: 2
        }
      ]

      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      await wrapper.vm.$nextTick()

      const vm = wrapper.vm as any
      expect(vm.hasRunningLogs).toBe(true)
    })
  })

  describe('执行详情展示', () => {
    it('应该显示处理时间', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      store.logs = mockLogs

      const vm = wrapper.vm as any
      const log = vm.logs[0]

      expect(log.execution_details?.processing_time).toBeDefined()
      expect(log.execution_details?.processing_time?.scraping).toBe(10.5)
    })

    it('应该显示处理的URL列表', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      store.logs = mockLogs

      const vm = wrapper.vm as any
      const log = vm.logs[0]

      expect(log.execution_details?.urls_processed).toBeDefined()
      expect(log.execution_details?.urls_processed?.length).toBe(1)
    })

    it('应该显示创建的文档列表', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      store.logs = mockLogs

      const vm = wrapper.vm as any
      const log = vm.logs[0]

      expect(log.execution_details?.documents).toBeDefined()
      expect(log.execution_details?.documents?.length).toBe(1)
    })

    it('应该显示错误信息', () => {
      wrapper = mount(WebScraperLogs, {
        props: {
          taskId: 1
        },
        global: {
          plugins: [createPinia()]
        }
      })

      store.logs = mockLogs

      const vm = wrapper.vm as any
      const failedLog = vm.logs[2]

      expect(failedLog.error_message).toBe('网络连接超时')
    })
  })
})
