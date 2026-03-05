/**
 * OpenClaw 状态管理 Store
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElNotification } from 'element-plus'
import { checkOpenClawHealth, type OpenClawHealthResponse } from '@/api/openclaw'

/**
 * OpenClaw UI 配置
 */
export interface OpenClawUIConfig {
  showNotifications: boolean // 是否显示状态变化通知
  notificationDuration: number // 通知显示时长（毫秒）
  autoRetry: boolean // 是否自动重试连接
  healthCheckInterval: number // 健康检查间隔（秒）
  retryBaseDelay: number // 重试基础延迟（毫秒）
  retryMaxDelay: number // 重试最大延迟（毫秒）
  retryJitterFactor: number // 抖动因子（0-1）
}

/**
 * 默认配置
 */
const DEFAULT_CONFIG: OpenClawUIConfig = {
  showNotifications: true,
  notificationDuration: 3000,
  autoRetry: true,
  healthCheckInterval: 30,
  retryBaseDelay: 5000, // 5秒基础延迟
  retryMaxDelay: 60000, // 60秒最大延迟
  retryJitterFactor: 0.3 // 30%抖动
}

export const useOpenClawStore = defineStore('openclaw', () => {
  // 状态
  const status = ref<'healthy' | 'unhealthy' | 'unknown'>('unknown')
  const version = ref<string>('')
  const uptime = ref<number>(0)
  const gatewayUrl = ref<string>('')
  const error = ref<string>('')
  const degraded = ref<boolean>(false)
  const degradedSince = ref<Date | null>(null)
  const lastHealthCheck = ref<Date | null>(null)
  const retryCount = ref<number>(0)
  const loading = ref<boolean>(false)

  // 配置（从 localStorage 加载）
  const config = ref<OpenClawUIConfig>(loadConfig())

  // 定时器
  let healthCheckTimer: number | null = null
  let recoveryCheckTimer: number | null = null

  // 计算属性
  const isHealthy = computed(() => status.value === 'healthy')
  const isUnhealthy = computed(() => status.value === 'unhealthy')
  const isUnknown = computed(() => status.value === 'unknown')

  const statusColor = computed(() => {
    switch (status.value) {
      case 'healthy':
        return '#52c41a'
      case 'unhealthy':
        return '#ff4d4f'
      default:
        return '#faad14'
    }
  })

  const statusText = computed(() => {
    switch (status.value) {
      case 'healthy':
        return 'OpenClaw 已连接'
      case 'unhealthy':
        return 'OpenClaw 不可用'
      default:
        return 'OpenClaw 连接中...'
    }
  })

  /**
   * 计算指数退避延迟（带抖动）
   *
   * @param retryCount 当前重试次数（从1开始）
   * @returns 延迟时间（毫秒）
   */
  function calculateBackoffDelay(retryCount: number): number {
    const { retryBaseDelay, retryMaxDelay, retryJitterFactor } = config.value

    // 指数退避：baseDelay * 2^(retryCount - 1)
    const exponentialDelay = retryBaseDelay * Math.pow(2, retryCount - 1)

    // 限制最大延迟
    const cappedDelay = Math.min(exponentialDelay, retryMaxDelay)

    // 添加抖动：delay * (1 ± jitterFactor)
    // 例如：jitterFactor=0.3 时，抖动范围为 [0.7 * delay, 1.3 * delay]
    const jitterRange = cappedDelay * retryJitterFactor
    const jitter = (Math.random() * 2 - 1) * jitterRange // -jitterRange 到 +jitterRange
    const finalDelay = Math.max(0, cappedDelay + jitter)

    return Math.round(finalDelay)
  }

  /**
   * 从 localStorage 加载配置
   */
  function loadConfig(): OpenClawUIConfig {
    try {
      const saved = localStorage.getItem('openclaw_config')
      if (saved) {
        return { ...DEFAULT_CONFIG, ...JSON.parse(saved) }
      }
    } catch (e) {
      console.error('加载 OpenClaw 配置失败:', e)
    }
    return { ...DEFAULT_CONFIG }
  }

  /**
   * 保存配置到 localStorage
   */
  function saveConfig() {
    try {
      localStorage.setItem('openclaw_config', JSON.stringify(config.value))
    } catch (e) {
      console.error('保存 OpenClaw 配置失败:', e)
    }
  }

  /**
   * 更新配置
   */
  function updateConfig(newConfig: Partial<OpenClawUIConfig>) {
    config.value = { ...config.value, ...newConfig }
    saveConfig()

    // 如果健康检查间隔改变，重启定时器
    if (newConfig.healthCheckInterval !== undefined) {
      startHealthCheck()
    }
  }

  /**
   * 检查健康状态
   */
  async function checkHealth() {
    try {
      loading.value = true
      const response = await checkOpenClawHealth()

      // 更新状态
      status.value = response.status
      version.value = response.version || ''
      uptime.value = response.uptime || 0
      gatewayUrl.value = response.gateway_url
      error.value = response.error || ''
      lastHealthCheck.value = new Date()

      // 如果之前是降级状态，现在恢复了
      if (degraded.value && response.status === 'healthy') {
        handleRecovery()
      } else if (response.status === 'unhealthy') {
        handleDegradation()
      } else if (response.status === 'healthy') {
        // 正常状态，重置重试计数
        retryCount.value = 0
        degraded.value = false
      }
    } catch (err) {
      console.error('健康检查失败:', err)
      handleDegradation()
    } finally {
      loading.value = false
    }
  }

  /**
   * 处理降级
   */
  function handleDegradation() {
    if (!degraded.value) {
      // 首次降级
      degraded.value = true
      degradedSince.value = new Date()

      if (config.value.showNotifications) {
        ElNotification.warning({
          title: 'OpenClaw 暂时不可用',
          message: '已切换到知识库模式，功能不受影响',
          duration: 5000
        })
      }
    }

    status.value = 'unhealthy'
    retryCount.value++

    // 如果启用自动重试且重试次数未超限
    if (config.value.autoRetry && retryCount.value < 3) {
      // 使用指数退避 + 抖动计算延迟
      const delay = calculateBackoffDelay(retryCount.value)
      console.log(`OpenClaw 重试 ${retryCount.value}/3，延迟 ${delay}ms`)
      setTimeout(() => checkHealth(), delay)
    } else if (retryCount.value >= 3) {
      // 重试失败，进入长期降级模式
      enterLongTermDegradation()
    }
  }

  /**
   * 进入长期降级模式
   */
  function enterLongTermDegradation() {
    // 每5分钟尝试恢复一次，添加抖动避免雷鸣群效应
    if (recoveryCheckTimer) {
      clearInterval(recoveryCheckTimer)
    }

    const baseInterval = 5 * 60 * 1000 // 5分钟
    const jitterRange = baseInterval * config.value.retryJitterFactor
    const jitter = (Math.random() * 2 - 1) * jitterRange
    const interval = Math.max(0, baseInterval + jitter)

    console.log(`OpenClaw 进入长期降级模式，恢复检查间隔 ${Math.round(interval / 1000)}s`)

    recoveryCheckTimer = window.setInterval(() => {
      retryCount.value = 0
      checkHealth()
    }, interval)
  }

  /**
   * 处理恢复
   */
  function handleRecovery() {
    if (config.value.showNotifications) {
      ElNotification.success({
        title: 'OpenClaw 已恢复',
        message: '现在可以使用完整功能',
        duration: 3000
      })
    }

    degraded.value = false
    degradedSince.value = null
    retryCount.value = 0

    // 清除恢复检查定时器
    if (recoveryCheckTimer) {
      clearInterval(recoveryCheckTimer)
      recoveryCheckTimer = null
    }
  }

  /**
   * 启动健康检查定时器
   */
  function startHealthCheck() {
    // 清除现有定时器
    if (healthCheckTimer) {
      clearInterval(healthCheckTimer)
    }

    // 立即执行一次
    checkHealth()

    // 设置定时器
    const interval = config.value.healthCheckInterval * 1000
    healthCheckTimer = window.setInterval(() => {
      checkHealth()
    }, interval)
  }

  /**
   * 停止健康检查定时器
   */
  function stopHealthCheck() {
    if (healthCheckTimer) {
      clearInterval(healthCheckTimer)
      healthCheckTimer = null
    }
    if (recoveryCheckTimer) {
      clearInterval(recoveryCheckTimer)
      recoveryCheckTimer = null
    }
  }

  /**
   * 手动重新连接
   */
  async function manualReconnect() {
    retryCount.value = 0
    await checkHealth()
  }

  return {
    // 状态
    status,
    version,
    uptime,
    gatewayUrl,
    error,
    degraded,
    degradedSince,
    lastHealthCheck,
    retryCount,
    loading,
    config,

    // 计算属性
    isHealthy,
    isUnhealthy,
    isUnknown,
    statusColor,
    statusText,

    // 方法
    checkHealth,
    startHealthCheck,
    stopHealthCheck,
    manualReconnect,
    updateConfig,
    calculateBackoffDelay // 导出用于测试
  }
})
