<template>
  <transition name="slide-down">
    <div v-if="showBanner" class="degradation-banner" :class="bannerClass">
      <div class="banner-content">
        <el-icon class="banner-icon" :size="20">
          <component :is="bannerIcon" />
        </el-icon>

        <div class="banner-message">
          <div class="banner-title">{{ bannerTitle }}</div>
          <div class="banner-description">{{ bannerDescription }}</div>

          <!-- 恢复倒计时进度条 -->
          <div v-if="retryCount >= 3 && nextRetryIn > 0 && !showRecoverySuccess" class="retry-progress">
            <div class="progress-bar">
              <div
                class="progress-fill"
                :style="{ width: `${(nextRetryIn / 300) * 100}%` }"
              ></div>
            </div>
            <div class="progress-text">
              下次自动重试: {{ Math.floor(nextRetryIn / 60) }}:{{ String(nextRetryIn % 60).padStart(2, '0') }}
            </div>
          </div>

          <!-- 详细状态信息 -->
          <div v-if="showLimitations && degradedSince" class="status-details">
            <div class="status-item">
              <span class="status-label">降级时长:</span>
              <span class="status-value">{{ degradedDuration }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">上次检查:</span>
              <span class="status-value">{{ lastCheckTime }}</span>
            </div>
            <div class="status-item">
              <span class="status-label">重试次数:</span>
              <span class="status-value">{{ retryCount }}/3</span>
            </div>
          </div>
        </div>

        <div class="banner-actions">
          <el-button
            v-if="showRetryButton"
            size="small"
            type="primary"
            :loading="loading"
            @click="handleRetry"
          >
            重试连接
          </el-button>

          <el-button
            v-if="!showRecoverySuccess"
            size="small"
            text
            @click="showDetails"
          >
            {{ showLimitations ? '收起详情' : '查看详情' }}
          </el-button>

          <el-button
            v-if="!showRecoverySuccess"
            size="small"
            text
            @click="toggleSettings"
            title="配置自动重试"
          >
            <el-icon><Setting /></el-icon>
          </el-button>

          <el-button
            size="small"
            text
            @click="dismissBanner"
          >
            <el-icon><Close /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 功能受限说明 -->
      <div v-if="showLimitations && !showRecoverySuccess" class="limitations-info">
        <div class="limitations-title">
          <el-icon><InfoFilled /></el-icon>
          当前功能限制：
        </div>
        <ul class="limitations-list">
          <li v-for="limitation in limitations" :key="limitation">{{ limitation }}</li>
        </ul>
      </div>

      <!-- 配置面板 -->
      <div v-if="showSettings && !showRecoverySuccess" class="settings-panel">
        <div class="settings-title">
          <el-icon><Setting /></el-icon>
          自动重试配置
        </div>
        <div class="settings-content">
          <el-form label-width="120px" size="small">
            <el-form-item label="启用自动重试">
              <el-switch
                :model-value="openclawStore.config.autoRetry"
                @change="(val) => openclawStore.updateConfig({ autoRetry: val })"
              />
            </el-form-item>
            <el-form-item label="健康检查间隔">
              <el-input-number
                :model-value="openclawStore.config.healthCheckInterval"
                @change="(val) => openclawStore.updateConfig({ healthCheckInterval: val })"
                :min="10"
                :max="300"
                :step="10"
              />
              <span class="input-suffix">秒</span>
            </el-form-item>
            <el-form-item label="显示通知">
              <el-switch
                :model-value="openclawStore.config.showNotifications"
                @change="(val) => openclawStore.updateConfig({ showNotifications: val })"
              />
            </el-form-item>
          </el-form>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import {
  WarningFilled,
  InfoFilled,
  Close,
  SuccessFilled,
  Setting
} from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useOpenClawStore } from '@/stores/openclaw'
import { storeToRefs } from 'pinia'

const openclawStore = useOpenClawStore()
const { degraded, status, retryCount, loading, degradedSince, lastHealthCheck } = storeToRefs(openclawStore)

const dismissed = ref(false)
const showLimitations = ref(false)
const showSettings = ref(false)
const showRecoverySuccess = ref(false)
const nextRetryIn = ref(0)
let retryTimer: number | null = null

// 计算是否显示横幅
const showBanner = computed(() => {
  return (degraded.value || status.value === 'unhealthy' || showRecoverySuccess.value) && !dismissed.value
})

// 横幅样式类
const bannerClass = computed(() => {
  if (showRecoverySuccess.value) {
    return 'banner-success'
  }
  if (status.value === 'unhealthy') {
    return 'banner-error'
  }
  return 'banner-warning'
})

// 横幅图标
const bannerIcon = computed(() => {
  if (showRecoverySuccess.value) {
    return SuccessFilled
  }
  if (status.value === 'unhealthy') {
    return WarningFilled
  }
  return InfoFilled
})

// 横幅标题
const bannerTitle = computed(() => {
  if (showRecoverySuccess.value) {
    return 'OpenClaw 已恢复连接'
  }
  if (status.value === 'unhealthy') {
    return 'OpenClaw 服务暂时不可用'
  }
  return 'OpenClaw 连接异常'
})

// 横幅描述
const bannerDescription = computed(() => {
  if (showRecoverySuccess.value) {
    return '所有功能已恢复正常，现在可以使用完整的 OpenClaw 功能。'
  }
  if (retryCount.value >= 3) {
    const nextRetryText = nextRetryIn.value > 0 ? `，${Math.ceil(nextRetryIn.value / 60)}分钟后自动重试` : ''
    return `系统已切换到降级模式${nextRetryText}。基础功能不受影响。`
  } else if (retryCount.value > 0) {
    return `正在尝试重新连接... (${retryCount.value}/3)`
  }
  return '系统已切换到知识库模式，基础对话和RAG功能正常使用。'
})

// 是否显示重试按钮
const showRetryButton = computed(() => {
  return status.value === 'unhealthy' && !loading.value && !showRecoverySuccess.value
})

// 降级持续时间
const degradedDuration = computed(() => {
  if (!degradedSince.value) return ''
  const now = new Date()
  const diff = now.getTime() - degradedSince.value.getTime()
  const minutes = Math.floor(diff / 60000)
  const hours = Math.floor(minutes / 60)

  if (hours > 0) {
    return `${hours}小时${minutes % 60}分钟`
  }
  return `${minutes}分钟`
})

// 上次检查时间
const lastCheckTime = computed(() => {
  if (!lastHealthCheck.value) return '未知'
  const now = new Date()
  const diff = now.getTime() - lastHealthCheck.value.getTime()
  const seconds = Math.floor(diff / 1000)

  if (seconds < 60) {
    return `${seconds}秒前`
  }
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) {
    return `${minutes}分钟前`
  }
  const hours = Math.floor(minutes / 60)
  return `${hours}小时前`
})

// 功能限制列表
const limitations = computed(() => {
  const limits: string[] = []

  if (degraded.value || status.value === 'unhealthy') {
    limits.push('❌ OpenClaw Agent 调用功能不可用')
    limits.push('❌ 浏览器自动化采集功能不可用')
    limits.push('❌ 增强型对话（混合推理）功能不可用')
    limits.push('✅ 基础对话功能正常')
    limits.push('✅ 知识库RAG查询功能正常')
    limits.push('✅ 本地Agent工具功能正常')
  }

  return limits
})

// 处理重试
async function handleRetry() {
  try {
    await openclawStore.manualReconnect()
    // 成功处理已在 store 中完成
  } catch (error) {
    console.error('重试连接失败:', error)
    ElMessage.error('重试连接失败，请稍后再试')
  }
}

// 显示详情
function showDetails() {
  showLimitations.value = !showLimitations.value
}

// 显示/隐藏配置
function toggleSettings() {
  showSettings.value = !showSettings.value
}

// 关闭横幅
function dismissBanner() {
  dismissed.value = true
}

// 启动倒计时
function startRetryCountdown() {
  if (retryTimer) {
    clearInterval(retryTimer)
  }

  // 如果重试次数>=3，说明进入长期降级模式，倒计时5分钟
  if (retryCount.value >= 3) {
    nextRetryIn.value = 300 // 5分钟 = 300秒
    retryTimer = window.setInterval(() => {
      nextRetryIn.value--
      if (nextRetryIn.value <= 0) {
        clearInterval(retryTimer!)
        retryTimer = null
      }
    }, 1000)
  }
}

// 停止倒计时
function stopRetryCountdown() {
  if (retryTimer) {
    clearInterval(retryTimer)
    retryTimer = null
  }
  nextRetryIn.value = 0
}

// 监听状态变化
watch(status, (newStatus, oldStatus) => {
  if (newStatus === 'healthy' && oldStatus !== 'healthy') {
    // 恢复成功，显示成功横幅3秒
    showRecoverySuccess.value = true
    dismissed.value = false
    showLimitations.value = false
    stopRetryCountdown()

    setTimeout(() => {
      showRecoverySuccess.value = false
    }, 3000)
  } else if (newStatus === 'unhealthy') {
    dismissed.value = false
  }
})

// 监听重试次数变化
watch(retryCount, (newCount) => {
  if (newCount >= 3) {
    startRetryCountdown()
  }
})

// 组件挂载时
onMounted(() => {
  if (retryCount.value >= 3) {
    startRetryCountdown()
  }
})

// 组件卸载时
onUnmounted(() => {
  stopRetryCountdown()
})
</script>

<style scoped lang="scss">
.degradation-banner {
  background: linear-gradient(135deg, #fff7e6 0%, #fffbf0 100%);
  border-bottom: 1px solid #ffd591;
  padding: 16px 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);

  &.banner-success {
    background: linear-gradient(135deg, #f6ffed 0%, #fcffe6 100%);
    border-bottom: 1px solid #b7eb8f;
  }

  &.banner-error {
    background: linear-gradient(135deg, #fff1f0 0%, #fff7f7 100%);
    border-bottom: 1px solid #ffccc7;
  }

  &.banner-warning {
    background: linear-gradient(135deg, #fff7e6 0%, #fffbf0 100%);
    border-bottom: 1px solid #ffd591;
  }

  .banner-content {
    display: flex;
    align-items: center;
    gap: 16px;

    .banner-icon {
      flex-shrink: 0;
      color: #faad14;
    }

    .banner-success & .banner-icon {
      color: #52c41a;
    }

    .banner-error & .banner-icon {
      color: #ff4d4f;
    }

    .banner-message {
      flex: 1;

      .banner-title {
        font-size: 14px;
        font-weight: 600;
        color: #262626;
        margin-bottom: 4px;
      }

      .banner-description {
        font-size: 13px;
        color: #595959;
        line-height: 1.5;
      }

      .retry-progress {
        margin-top: 12px;

        .progress-bar {
          height: 4px;
          background: rgba(0, 0, 0, 0.06);
          border-radius: 2px;
          overflow: hidden;
          margin-bottom: 6px;

          .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #1890ff 0%, #40a9ff 100%);
            transition: width 1s linear;
          }
        }

        .progress-text {
          font-size: 12px;
          color: #8c8c8c;
        }
      }

      .status-details {
        margin-top: 12px;
        display: flex;
        gap: 24px;
        padding: 8px 12px;
        background: rgba(0, 0, 0, 0.02);
        border-radius: 4px;

        .status-item {
          display: flex;
          gap: 8px;
          font-size: 12px;

          .status-label {
            color: #8c8c8c;
          }

          .status-value {
            color: #262626;
            font-weight: 500;
          }
        }
      }
    }

    .banner-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
    }
  }

  .limitations-info {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);

    .limitations-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 600;
      color: #262626;
      margin-bottom: 12px;

      .el-icon {
        color: #1890ff;
      }
    }

    .limitations-list {
      list-style: none;
      padding: 0;
      margin: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 8px;

      li {
        font-size: 13px;
        color: #595959;
        padding: 4px 0;
        line-height: 1.5;
      }
    }
  }

  .settings-panel {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);

    .settings-title {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
      font-weight: 600;
      color: #262626;
      margin-bottom: 12px;

      .el-icon {
        color: #1890ff;
      }
    }

    .settings-content {
      background: rgba(0, 0, 0, 0.02);
      padding: 16px;
      border-radius: 4px;

      .input-suffix {
        margin-left: 8px;
        font-size: 12px;
        color: #8c8c8c;
      }
    }
  }
}

// 动画
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}

.slide-down-enter-from {
  transform: translateY(-100%);
  opacity: 0;
}

.slide-down-leave-to {
  transform: translateY(-100%);
  opacity: 0;
}
</style>
