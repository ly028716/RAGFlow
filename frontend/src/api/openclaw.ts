/**
 * OpenClaw API 客户端
 */

import request from './index'

/**
 * OpenClaw 健康状态
 */
export interface OpenClawHealthResponse {
  status: 'healthy' | 'unhealthy' | 'unknown'
  version?: string
  uptime?: number
  gateway_url: string
  error?: string
}

/**
 * OpenClaw 消息请求
 */
export interface OpenClawMessageRequest {
  message: string
  agent_id?: string
  context?: Record<string, any>
  stream?: boolean
}

/**
 * Agent 执行步骤
 */
export interface AgentStep {
  type: string
  content: string
  timestamp?: string
}

/**
 * OpenClaw 消息响应
 */
export interface OpenClawMessageResponse {
  response: string
  agent_id: string
  execution_time: number
  steps?: AgentStep[]
}

/**
 * 检查 OpenClaw 健康状态
 */
export function checkOpenClawHealth() {
  return request<OpenClawHealthResponse>({
    url: '/openclaw/health',
    method: 'get'
  })
}

/**
 * 发送消息到 OpenClaw Agent
 */
export function sendMessageToOpenClaw(data: OpenClawMessageRequest) {
  return request<OpenClawMessageResponse>({
    url: '/openclaw/message',
    method: 'post',
    data
  })
}
