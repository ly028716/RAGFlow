/**
 * Web Scraper Store 单元测试
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useWebScraperStore } from '@/stores/webScraper'
import { webScraperApi } from '@/api/webScraper'
import type { Task, TaskCreateRequest, TaskUpdateRequest } from '@/types/webScraper'

// Mock API
vi.mock('@/api/webScraper', () => ({
  webScraperApi: {
    getTasks: vi.fn(),
    getTask: vi.fn(),
    createTask: vi.fn(),
    updateTask: vi.fn(),
    deleteTask: vi.fn(),
    startTask: vi.fn(),
    stopTask: vi.fn(),
    getLogs: vi.fn(),
    getLogStatistics: vi.fn()
  }
}))

// Mock ElMessage
vi.mock('element-plus', () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn()
  }
}))

describe('useWebScraperStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('初始状态', () => {
    it('应该正确初始化状态', () => {
      const store = useWebScraperStore()

      expect(store.tasks).toEqual([])
      expect(store.currentTask).toBeNull()
      expect(store.logs).toEqual([])
      expect(store.totalTasks).toBe(0)
      expect(store.totalLogs).toBe(0)
      expect(store.loading).toBe(false)
      expect(store.logsLoading).toBe(false)
    })

    it('应该正确计算getters', () => {
      const store = useWebScraperStore()

      expect(store.taskCount).toBe(0)
      expect(store.hasTasks).toBe(false)
      expect(store.activeTasks).toEqual([])
      expect(store.runningLogs).toEqual([])
    })
  })

  describe('loadTasks', () => {
    it('应该成功加载任务列表', async () => {
      const store = useWebScraperStore()
      const mockTasks: Task[] = [
        {
          id: 1,
          name: '测试任务1',
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
      ]

      vi.mocked(webScraperApi.getTasks).mockResolvedValue({
        items: mockTasks,
        total: 1
      })

      await store.loadTasks()

      expect(store.tasks).toEqual(mockTasks)
      expect(store.totalTasks).toBe(1)
      expect(store.loading).toBe(false)
    })

    it('应该处理加载失败', async () => {
      const store = useWebScraperStore()
      const error = new Error('加载失败')

      vi.mocked(webScraperApi.getTasks).mockRejectedValue(error)

      await expect(store.loadTasks()).rejects.toThrow('加载失败')
      expect(store.loading).toBe(false)
    })
  })

  describe('loadTask', () => {
    it('应该成功加载任务详情', async () => {
      const store = useWebScraperStore()
      const mockTask: Task = {
        id: 1,
        name: '测试任务',
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

      vi.mocked(webScraperApi.getTask).mockResolvedValue(mockTask)

      const result = await store.loadTask(1)

      expect(result).toEqual(mockTask)
      expect(store.currentTask).toEqual(mockTask)
    })
  })

  describe('createTask', () => {
    it('应该成功创建任务', async () => {
      const store = useWebScraperStore()
      const taskData: TaskCreateRequest = {
        name: '新任务',
        url: 'https://example.com',
        knowledge_base_id: 1,
        schedule_type: 'once',
        selector_config: { title: 'h1', content: 'article' },
        scraper_config: { wait_for_selector: 'body', wait_timeout: 30000 }
      }

      const mockTask: Task = {
        id: 1,
        ...taskData,
        status: 'paused',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
        created_by: 1
      }

      vi.mocked(webScraperApi.createTask).mockResolvedValue(mockTask)

      const result = await store.createTask(taskData)

      expect(result).toEqual(mockTask)
      expect(webScraperApi.createTask).toHaveBeenCalledWith(taskData)
    })
  })

  describe('updateTask', () => {
    it('应该成功更新任务', async () => {
      const store = useWebScraperStore()
      store.tasks = [
        {
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
      ]

      const updateData: TaskUpdateRequest = {
        name: '新名称'
      }

      const updatedTask: Task = {
        ...store.tasks[0],
        name: '新名称'
      }

      vi.mocked(webScraperApi.updateTask).mockResolvedValue(updatedTask)

      const result = await store.updateTask(1, updateData)

      expect(result).toEqual(updatedTask)
      expect(store.tasks[0].name).toBe('新名称')
    })

    it('应该更新currentTask', async () => {
      const store = useWebScraperStore()
      const task: Task = {
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

      store.currentTask = task

      const updatedTask: Task = {
        ...task,
        name: '新名称'
      }

      vi.mocked(webScraperApi.updateTask).mockResolvedValue(updatedTask)

      await store.updateTask(1, { name: '新名称' })

      expect(store.currentTask?.name).toBe('新名称')
    })
  })

  describe('deleteTask', () => {
    it('应该成功删除任务', async () => {
      const store = useWebScraperStore()
      store.tasks = [
        {
          id: 1,
          name: '任务1',
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
      ]
      store.totalTasks = 1

      vi.mocked(webScraperApi.deleteTask).mockResolvedValue()

      await store.deleteTask(1)

      expect(store.tasks).toEqual([])
      expect(store.totalTasks).toBe(0)
    })

    it('应该清除currentTask', async () => {
      const store = useWebScraperStore()
      store.currentTask = {
        id: 1,
        name: '任务1',
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

      vi.mocked(webScraperApi.deleteTask).mockResolvedValue()

      await store.deleteTask(1)

      expect(store.currentTask).toBeNull()
    })
  })

  describe('startTask', () => {
    it('应该成功启动任务', async () => {
      const store = useWebScraperStore()
      store.tasks = [
        {
          id: 1,
          name: '任务1',
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
      ]

      vi.mocked(webScraperApi.startTask).mockResolvedValue({
        status: 'active',
        message: '任务已启动'
      })

      await store.startTask(1)

      expect(store.tasks[0].status).toBe('active')
    })
  })

  describe('stopTask', () => {
    it('应该成功停止任务', async () => {
      const store = useWebScraperStore()
      store.tasks = [
        {
          id: 1,
          name: '任务1',
          url: 'https://example.com',
          knowledge_base_id: 1,
          schedule_type: 'once',
          status: 'active',
          selector_config: { title: 'h1', content: 'article' },
          scraper_config: { wait_for_selector: 'body', wait_timeout: 30000 },
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          created_by: 1
        }
      ]

      vi.mocked(webScraperApi.stopTask).mockResolvedValue({
        status: 'stopped',
        message: '任务已停止'
      })

      await store.stopTask(1)

      expect(store.tasks[0].status).toBe('stopped')
    })
  })

  describe('loadLogs', () => {
    it('应该成功加载日志列表', async () => {
      const store = useWebScraperStore()
      const mockLogs = [
        {
          id: 1,
          task_id: 1,
          status: 'success' as const,
          start_time: '2026-01-01T00:00:00Z',
          end_time: '2026-01-01T00:01:00Z',
          pages_scraped: 5,
          documents_created: 5
        }
      ]

      vi.mocked(webScraperApi.getLogs).mockResolvedValue({
        items: mockLogs,
        total: 1
      })

      await store.loadLogs(1)

      expect(store.logs).toEqual(mockLogs)
      expect(store.totalLogs).toBe(1)
    })
  })

  describe('clearCurrentTask', () => {
    it('应该清空当前任务', () => {
      const store = useWebScraperStore()
      store.currentTask = {
        id: 1,
        name: '任务1',
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

      store.clearCurrentTask()

      expect(store.currentTask).toBeNull()
    })
  })

  describe('clearLogs', () => {
    it('应该清空日志', () => {
      const store = useWebScraperStore()
      store.logs = [
        {
          id: 1,
          task_id: 1,
          status: 'success',
          start_time: '2026-01-01T00:00:00Z',
          pages_scraped: 5,
          documents_created: 5
        }
      ]
      store.totalLogs = 1

      store.clearLogs()

      expect(store.logs).toEqual([])
      expect(store.totalLogs).toBe(0)
    })
  })
})
