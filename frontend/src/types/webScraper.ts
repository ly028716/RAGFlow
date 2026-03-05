/**
 * Web Scraper 类型定义
 */

// 调度类型
export type ScheduleType = 'once' | 'cron'

// 任务状态
export type TaskStatus = 'active' | 'paused' | 'stopped'

// 日志状态
export type LogStatus = 'running' | 'success' | 'failed'

// 选择器配置
export interface SelectorConfig {
  title: string
  content: string
  author?: string
  publish_date?: string
  exclude?: string[]
}

// 采集器配置
export interface ScraperConfig {
  wait_for_selector: string
  wait_timeout: number
  screenshot: boolean
  user_agent?: string
  headers?: Record<string, string>
  retry_times: number
  retry_delay: number
}

// 任务
export interface Task {
  id: number
  name: string
  description: string | null
  url: string
  url_pattern: string | null
  knowledge_base_id: number
  schedule_type: ScheduleType
  cron_expression: string | null
  selector_config: SelectorConfig
  scraper_config: ScraperConfig
  status: TaskStatus
  last_run_at: string | null
  next_run_at: string | null
  created_by: number
  created_at: string
  updated_at: string
}

// 创建任务请求
export interface TaskCreateRequest {
  name: string
  description?: string
  url: string
  url_pattern?: string
  knowledge_base_id: number
  schedule_type: ScheduleType
  cron_expression?: string
  selector_config: SelectorConfig
  scraper_config?: ScraperConfig
}

// 更新任务请求
export interface TaskUpdateRequest {
  name?: string
  description?: string
  url?: string
  url_pattern?: string
  schedule_type?: ScheduleType
  cron_expression?: string
  selector_config?: SelectorConfig
  scraper_config?: ScraperConfig
  status?: TaskStatus
}

// 任务列表响应
export interface TaskListResponse {
  total: number
  items: Task[]
}

// 执行详情
export interface ExecutionDetails {
  urls_processed: string[]
  processing_time: {
    scraping: number
    processing: number
    storing: number
    total?: number
  }
  documents: Array<{
    title: string
    url: string
    document_id: number
  }>
  errors: string[]
}

// 执行日志
export interface Log {
  id: number
  task_id: number
  status: LogStatus
  start_time: string
  end_time: string | null
  pages_scraped: number
  documents_created: number
  error_message: string | null
  execution_details: ExecutionDetails | null
  created_at: string
}

// 日志列表响应
export interface LogListResponse {
  total: number
  items: Log[]
}

// 日志统计响应
export interface LogStatisticsResponse {
  total: number
  success: number
  failed: number
  running: number
  success_rate: number
}

// 任务执行响应
export interface TaskExecuteResponse {
  task_id: number
  log_id: number
  status: string
  message: string
}

// 任务查询参数
export interface TaskQueryParams {
  status?: TaskStatus
  knowledge_base_id?: number
  schedule_type?: ScheduleType
  skip?: number
  limit?: number
}

// 日志查询参数
export interface LogQueryParams {
  status?: LogStatus
  start_date?: string
  end_date?: string
  skip?: number
  limit?: number
}
