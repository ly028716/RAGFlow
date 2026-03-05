/**
 * Web Scraper API 客户端
 */

import request from './index'
import type {
  Task,
  TaskCreateRequest,
  TaskUpdateRequest,
  TaskListResponse,
  TaskQueryParams,
  LogListResponse,
  LogQueryParams,
  LogStatisticsResponse,
  TaskExecuteResponse
} from '@/types/webScraper'

export const webScraperApi = {
  /**
   * 创建采集任务
   */
  createTask(data: TaskCreateRequest): Promise<Task> {
    return request.post('/web-scraper/tasks', data)
  },

  /**
   * 获取任务列表
   */
  getTasks(params?: TaskQueryParams): Promise<TaskListResponse> {
    return request.get('/web-scraper/tasks', { params })
  },

  /**
   * 获取任务详情
   */
  getTask(taskId: number): Promise<Task> {
    return request.get(`/web-scraper/tasks/${taskId}`)
  },

  /**
   * 更新任务
   */
  updateTask(taskId: number, data: TaskUpdateRequest): Promise<Task> {
    return request.put(`/web-scraper/tasks/${taskId}`, data)
  },

  /**
   * 删除任务
   */
  deleteTask(taskId: number): Promise<void> {
    return request.delete(`/web-scraper/tasks/${taskId}`)
  },

  /**
   * 启动任务
   */
  startTask(taskId: number): Promise<TaskExecuteResponse> {
    return request.post(`/web-scraper/tasks/${taskId}/start`)
  },

  /**
   * 停止任务
   */
  stopTask(taskId: number): Promise<TaskExecuteResponse> {
    return request.post(`/web-scraper/tasks/${taskId}/stop`)
  },

  /**
   * 获取任务执行日志
   */
  getLogs(taskId: number, params?: LogQueryParams): Promise<LogListResponse> {
    return request.get(`/web-scraper/tasks/${taskId}/logs`, { params })
  },

  /**
   * 获取任务日志统计
   */
  getLogStatistics(taskId: number): Promise<LogStatisticsResponse> {
    return request.get(`/web-scraper/tasks/${taskId}/statistics`)
  }
}
