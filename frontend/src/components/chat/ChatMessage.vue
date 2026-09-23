<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument, RefreshRight, MagicStick, Document } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import type { Message } from '@/types'

const MarkdownRenderer = defineAsyncComponent(() => import('./MarkdownRenderer.vue'))

const props = defineProps<{
  message: Message
  isStreaming?: boolean
}>()

const emit = defineEmits<{
  regenerate: []
}>()

const authStore = useAuthStore()

const isUser = computed(() => props.message.role === 'user')
const roleName = computed(() => isUser.value ? '我' : 'AI 助手')

function formatTime(time?: string): string {
  if (!time) return ''
  return new Date(time).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

async function copyContent() {
  try {
    await navigator.clipboard.writeText(props.message.content)
    ElMessage.success('已复制到剪贴板')
  } catch {
    ElMessage.error('复制失败')
  }
}

function handleRegenerate() {
  emit('regenerate')
}
</script>

<template>
  <div class="chat-message" :class="[message.role, { streaming: isStreaming }]">
    <div class="avatar">
      <el-avatar v-if="isUser" :size="36" :src="authStore.avatar || undefined">
        {{ authStore.username?.charAt(0)?.toUpperCase() }}
      </el-avatar>
      <el-avatar v-else :size="36" class="ai-avatar">
        <el-icon><MagicStick /></el-icon>
      </el-avatar>
    </div>

    <div class="content">
      <div class="message-header">
        <span class="role-name">{{ roleName }}</span>
        <span class="time">{{ formatTime(message.created_at) }}</span>
      </div>

      <div class="message-body">
        <MarkdownRenderer v-if="!isUser" :content="message.content" />
        <p v-else>{{ message.content }}</p>
        <span v-if="isStreaming" class="cursor">▊</span>

        <!-- 引用源展示 -->
        <div v-if="message.sources && message.sources.length > 0" class="sources-container">
          <div class="sources-title">
            <el-icon><Document /></el-icon>
            <span>参考资料</span>
          </div>
          <div class="sources-list">
            <div v-for="(source, index) in message.sources" :key="index" class="source-item">
              <span class="source-index">[{{ index + 1 }}]</span>
              <span class="source-name">{{ source.document_name }}</span>
              <span class="source-score">({{ (source.similarity_score * 100).toFixed(0) }}%)</span>
            </div>
          </div>
        </div>
      </div>

      <div class="message-actions" v-if="!isStreaming">
        <el-tooltip content="复制" placement="top">
          <el-button :icon="CopyDocument" text size="small" @click="copyContent" />
        </el-tooltip>
        <el-tooltip v-if="!isUser" content="重新生成" placement="top">
          <el-button :icon="RefreshRight" text size="small" @click="handleRegenerate" />
        </el-tooltip>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.chat-message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  padding: 0 20px;

  &.user {
    flex-direction: row-reverse;

    .content {
      align-items: flex-end;
    }

    .message-body {
      background: #ecf5ff;
      border-radius: 12px 12px 4px 12px;
    }

    .message-header {
      flex-direction: row-reverse;
    }
  }

  &.assistant {
    .message-body {
      background: white;
      border-radius: 12px 12px 12px 4px;
      box-shadow: $box-shadow-light;
    }
  }
}

.ai-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.content {
  display: flex;
  flex-direction: column;
  max-width: 75%;
  min-width: 100px;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 12px;
  color: $text-secondary;
}

.message-body {
  padding: 12px 16px;
  line-height: 1.6;
  word-break: break-word;

  p {
    margin: 0;
    white-space: pre-wrap;
  }
}

.cursor {
  display: inline-block;
  animation: blink 1s infinite;
  color: $primary-color;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

.message-actions {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  opacity: 0;
  transition: opacity 0.2s;

  .el-button {
    color: $text-secondary;
  }
}

.chat-message:hover .message-actions {
  opacity: 1;
}

.sources-container {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #eee;
  font-size: 12px;

  .sources-title {
    display: flex;
    align-items: center;
    gap: 4px;
    color: $text-secondary;
    margin-bottom: 8px;
    font-weight: 500;
  }

  .sources-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .source-item {
    color: $text-regular;
    display: flex;
    align-items: center;
    gap: 6px;
    
    .source-index {
      color: $primary-color;
      font-weight: 500;
    }

    .source-score {
      color: $text-secondary;
      font-size: 11px;
    }
  }
}
</style>
