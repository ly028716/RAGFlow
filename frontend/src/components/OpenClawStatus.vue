<template>
  <div class="openclaw-status">
    <!-- 状态指示器 -->
    <el-badge :value="retryCount" :hidden="retryCount === 0" class="status-badge">
      <div class="status-indicator" @click="showDetails = true">
        <span class="status-dot" :style="{ backgroundColor: statusColor }"></span>
        <span class="status-text">{{ statusText }}</span>
        <el-tooltip :content="tooltipContent" placement="bottom">
          <el-icon class="info-icon"><InfoFilled /></el-icon>
        </el-tooltip>
      </div>
    </el-badge>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="showDetails"
      title="OpenClaw 连接详情"
      width="400px"
      :close-on-click-modal="true"
    >
      <div class="details-content">
        <div class="detail-item">
          <span class="label">状态:</span>
          <span class="value">
            <span class="status-dot" :style="{ backgroundColor: statusColor }"></span>
            {{ statusText }}
          </span>
        </div>
        <div v-if="version" class="detail-item">
          <span class="label">版本:</span>
          <span class="value">{{ version }}</span>
        </div>
        <div v-if="uptime > 0" class="detail-item">
          <span class="label">运行时间:</span>
          <span class="value">{{ formatUptime(uptime) }}</span>
        </div>
        <div class="detail-item">
          <span class="label">Gateway URL:</span>
          <span class="value">{{ gatewayUrl }}</span>
        </div>
        <div v-if="lastHealthCheck" class="detail-item">
          <span class="label">最后检查:</span>
          <span class="value">{{ formatLastCheck(lastHealthCheck) }}</span>
        </div>
        <div v-if="error" class="detail-item error">
          <span class="label">错误信息:</span>
          <span class="value">{{ error }}</span>
        </div>
      </div>

      <template #footer>
        <el-button @click="showDetails = false">关闭</el-button>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleReconnect"
          v-if="isUnhealthy"
        >
          重新连接
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useOpenClawStore } from '@/stores/openclaw'
import { storeToRefs } from 'pinia'

const openclawStore = useOpenClawStore()
const {
  status,
  version,
  uptime,
  gatewayUrl,
  error,
  lastHealthCheck,
  retryCount,
  loading,
  statusColor,
  statusText,
  isUnhealthy
} = storeToRefs(openclawStore)

const showDetails = ref(false)

// 计算 Tooltip 内容
const tooltipContent = computed(() => {
  if (version.value) {
    return `版本: ${version.value}\n最后检查: ${formatLastCheck(lastHealthCheck.value)}`
  }
  return '点击查看详情'
})

/**
 * 格式化运行时间
 */
function formatUptime(seconds: number): string {
  const days = Math.floor(seconds / 86400)
  const hours = Math.floor((seconds % 86400) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)

  if (days > 0) {
    return `${days}天${hours}小时`
  } else if (hours > 0) {
    return `${hours}小时${minutes}分钟`
  } else {
    return `${minutes}分钟`
  }
}

/**
 * 格式化最后检查时间
 */
function formatLastCheck(date: Date | null): string {
  if (!date) return '未知'

  const now = new Date()
  const diff = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diff < 60) {
    return `${diff}秒前`
  } else if (diff < 3600) {
    return `${Math.floor(diff / 60)}分钟前`
  } else if (diff < 86400) {
    return `${Math.floor(diff / 3600)}小时前`
  } else {
    return `${Math.floor(diff / 86400)}天前`
  }
}

/**
 * 处理重新连接
 */
async function handleReconnect() {
  try {
    await openclawStore.manualReconnect()
    if (openclawStore.isHealthy) {
      ElMessage.success('重新连接成功')
      showDetails.value = false
    } else {
      ElMessage.error('重新连接失败，请稍后再试')
    }
  } catch (err) {
    ElMessage.error('重新连接失败')
  }
}

// 生命周期
onMounted(() => {
  openclawStore.startHealthCheck()
})

onUnmounted(() => {
  openclawStore.stopHealthCheck()
})
</script>

<style scoped lang="scss">
.openclaw-status {
  display: flex;
  align-items: center;
  padding: 0 16px;

  .status-badge {
    cursor: pointer;
  }

  .status-indicator {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 4px;
    transition: background-color 0.3s;
    cursor: pointer;

    &:hover {
      background-color: rgba(0, 0, 0, 0.05);
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      display: inline-block;
    }

    .status-text {
      font-size: 14px;
      color: #333;
    }

    .info-icon {
      font-size: 16px;
      color: #999;
    }
  }
}

.details-content {
  .detail-item {
    display: flex;
    justify-content: space-between;
    padding: 12px 0;
    border-bottom: 1px solid #f0f0f0;

    &:last-child {
      border-bottom: none;
    }

    &.error {
      .value {
        color: #ff4d4f;
      }
    }

    .label {
      font-weight: 500;
      color: #666;
    }

    .value {
      color: #333;
      display: flex;
      align-items: center;
      gap: 6px;

      .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        display: inline-block;
      }
    }
  }
}

// 恢复动画
@keyframes pulse {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

.status-indicator.recovering {
  animation: pulse 1s ease-in-out;
}
</style>
