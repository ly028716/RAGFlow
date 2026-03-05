/**
 * Web Scraper 状态管理
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { webScraperApi } from '@/api/webScraper'
import type {
  Task,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskQueryParams,
  Log,
  LogQueryParams,
  TaskStatus,
  LogStatus
} from '@/types/webScraper'

export const useWebScraperStore = defineStore('webScraper', () => {
  // State
  const tasks = ref<Task[]>([])
  const currentTask = ref<Task | null>(null)
  const logs = ref<Log[]>([])
  const totalTasks = ref(0)
  const totalLogs = ref(0)
  const loading = ref(false)
  const logsLoading = ref(false)

  // Getters
  const taskCount = computed(() => tasks.value.length)
  const hasTasks = computed(() => taskCount.value > 0)
  const activeTasks = computed(() => tasks.value.filter(t => t.status === 'active'))
  const runningLogs = computed(() => logs.value.filter(l => l.status === 'running'))

  // Actions

  /**
   * 加载任务列表
   */
  async function loadTasks(params?: TaskQueryParams) {
    loading.value = true
    try {
      const response = await webScraperApi.getTasks(params)
      tasks.value = response.items
      totalTasks.value = response.total
    } catch (error) {
      console.error('加载任务列表失败:', error)
      ElMessage.error('加载任务列表失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载任务详情
   */
  async function loadTask(taskId: number) {
    loading.value = true
    try {
      const task = await webScraperApi.getTask(taskId)
      currentTask.value = task
      return task
    } catch (error) {
      console.error('加载任务详情失败:', error)
      ElMessage.error('加载任务详情失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 创建任务
   */
  async function createTask(data: TaskCreateRequest) {
    loading.value = true
    try {
      const task = await webScraperApi.createTask(data)
      ElMessage.success('任务创建成功')
      return task
    } catch (error) {
      console.error('创建任务失败:', error)
      ElMessage.error('创建任务失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新任务
   */
  async function updateTask(taskId: number, data: TaskUpdateRequest) {
    loading.value = true
    try {
      const task = await webScraperApi.updateTask(taskId, data)
      const index = tasks.value.findIndex(t => t.id === taskId)
      if (index !== -1) {
        tasks.value[index] = task
      }
      if (currentTask.value?.id === taskId) {
        currentTask.value = task
      }
      ElMessage.success('任务更新成功')
      return task
    } catch (error) {
      console.error('更新任务失败:', error)
      ElMessage.error('更新任务失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 删除任务
   */
  async function deleteTask(taskId: number) {
    loading.value = true
    try {
      await webScraperApi.deleteTask(taskId)
      tasks.value = tasks.value.filter(t => t.id !== taskId)
      totalTasks.value--
      if (currentTask.value?.id === taskId) {
        currentTask.value = null
      }
      ElMessage.success('任务删除成功')
    } catch (error) {
      console.error('删除任务失败:', error)
      ElMessage.error('删除任务失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 启动任务
   */
  async function startTask(taskId: number) {
    loading.value = true
    try {
      const response = await webScraperApi.startTask(taskId)
      // 更新任务状态
      const index = tasks.value.findIndex(t => t.id === taskId)
      if (index !== -1) {
        tasks.value[index].status = 'active'
      }
      if (currentTask.value?.id === taskId) {
        currentTask.value.status = 'active'
      }
      ElMessage.success(response.message || '任务已启动')
      return response
    } catch (error) {
      console.error('启动任务失败:', error)
      ElMessage.error('启动任务失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 停止任务
   */
  async function stopTask(taskId: number) {
    loading.value = true
    try {
      const response = await webScraperApi.stopTask(taskId)
      // 更新任务状态
      const index = tasks.value.findIndex(t => t.id === taskId)
      if (index !== -1) {
        tasks.value[index].status = 'stopped'
      }
      if (currentTask.value?.id === taskId) {
        currentTask.value.status = 'stopped'
      }
      ElMessage.success(response.message || '任务已停止')
      return response
    } catch (error) {
      console.error('停止任务失败:', error)
      ElMessage.error('停止任务失败')
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 加载任务日志
   */
  async function loadLogs(taskId: number, params?: LogQueryParams) {
    logsLoading.value = true
    try {
      const response = await webScraperApi.getLogs(taskId, params)
      logs.value = response.items
      totalLogs.value = response.total
    } catch (error) {
      console.error('加载日志失败:', error)
      ElMessage.error('加载日志失败')
      throw error
    } finally {
      logsLoading.value = false
    }
  }

  /**
   * 刷新任务列表（静默）
   */
  async function refreshTasks(params?: TaskQueryParams) {
    try {
      const response = await webScraperApi.getTasks(params)
      tasks.value = response.items
      totalTasks.value = response.total
    } catch (error) {
      console.error('刷新任务列表失败:', error)
    }
  }

  /**
   * 刷新日志列表（静默）
   */
  async function refreshLogs(taskId: number, params?: LogQueryParams) {
    try {
      const response = await webScraperApi.getLogs(taskId, params)
      logs.value = response.items
      totalLogs.value = response.total
    } catch (error) {
      console.error('刷新日志失败:', error)
    }
  }

  /**
   * 清空当前任务
   */
  function clearCurrentTask() {
    currentTask.value = null
  }

  /**
   * 清空日志
   */
  function clearLogs() {
    logs.value = []
    totalLogs.value = 0
  }

  return {
    // State
    tasks,
    currentTask,
    logs,
    totalTasks,
    totalLogs,
    loading,
    logsLoading,
    // Getters
    taskCount,
    hasTasks,
    activeTasks,
    runningLogs,
    // Actions
    loadTasks,
    loadTask,
    createTask,
    updateTask,
    deleteTask,
    startTask,
    stopTask,
    loadLogs,
    refreshTasks,
    refreshLogs,
    clearCurrentTask,
    clearLogs
  }
})
