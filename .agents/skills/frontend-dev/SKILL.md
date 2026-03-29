---
name: frontend-dev
description: Vue 3前端开发工程师。开发Vue组件、页面布局、状态管理、API对接、响应式设计时使用。
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# 前端开发 Skill

为 RAGAgentLangChain 项目进行 Vue 3 前端开发。

## 核心职责

- 开发 Vue 3 组件和页面
- 实现响应式布局和交互
- 状态管理（Pinia）
- API 对接和数据处理
- 路由配置和导航
- UI 组件集成（Element Plus）
- 性能优化

## 技术栈

- **框架**: Vue 3.5+ (Composition API)
- **语言**: TypeScript 5.9+
- **构建**: Vite 7.2+
- **UI库**: Element Plus 2.9+
- **状态**: Pinia 3.0+
- **路由**: Vue Router 4.x
- **HTTP**: Axios 1.9+
- **Markdown**: markdown-it 14.1+
- **代码高亮**: highlight.js 11.11+

## 项目结构

```
frontend/src/
├── api/              # API客户端
│   ├── index.ts      # Axios配置
│   ├── auth.ts       # 认证API
│   ├── chat.ts       # 对话API
│   └── ...
├── components/       # 可复用组件
│   ├── chat/         # 聊天相关组件
│   │   ├── MessageList.vue
│   │   ├── MessageInput.vue
│   │   └── StreamingMessage.vue
│   └── common/       # 通用组件
├── composables/      # 组合式函数
│   ├── useAuth.ts
│   ├── useChat.ts
│   └── ...
├── layouts/          # 布局组件
│   ├── DefaultLayout.vue
│   └── AuthLayout.vue
├── router/           # 路由配置
│   └── index.ts
├── stores/           # Pinia状态管理
│   ├── auth.ts
│   ├── conversation.ts
│   └── ...
├── types/            # TypeScript类型定义
│   ├── api.ts
│   ├── chat.ts
│   └── ...
├── utils/            # 工具函数
│   ├── request.ts
│   ├── markdown.ts
│   └── ...
├── views/            # 页面组件
│   ├── Login.vue
│   ├── Chat.vue
│   └── ...
├── App.vue           # 根组件
└── main.ts           # 入口文件
```

## 开发规范

### 1. 组件开发规范

#### 使用 Composition API

```vue
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { Message } from '@/types/chat'

// Props定义
interface Props {
  conversationId: number
  title?: string
}

const props = withDefaults(defineProps<Props>(), {
  title: '新对话'
})

// Emits定义
interface Emits {
  (e: 'send', message: string): void
  (e: 'delete', id: number): void
}

const emit = defineEmits<Emits>()

// 响应式数据
const messages = ref<Message[]>([])
const loading = ref(false)

// 计算属性
const messageCount = computed(() => messages.value.length)

// 方法
const sendMessage = (content: string) => {
  emit('send', content)
}

// 生命周期
onMounted(() => {
  loadMessages()
})
</script>

<template>
  <div class="chat-container">
    <h2>{{ title }}</h2>
    <div v-if="loading">加载中...</div>
    <div v-else>
      <p>消息数: {{ messageCount }}</p>
    </div>
  </div>
</template>

<style scoped>
.chat-container {
  padding: 20px;
}
</style>
```

#### 组件命名规范

- 组件文件名：PascalCase（`MessageList.vue`, `ChatInput.vue`）
- 组件名称：PascalCase
- Props：camelCase
- Events：kebab-case

### 2. TypeScript 类型定义

```typescript
// types/chat.ts
export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count: number
}

export interface ChatRequest {
  conversation_id?: number
  content: string
  stream?: boolean
}

export interface ChatResponse {
  message: Message
  conversation_id: number
}
```

### 3. API 客户端开发

```typescript
// api/chat.ts
import request from '@/utils/request'
import type { ChatRequest, ChatResponse, Conversation } from '@/types/chat'

export const chatApi = {
  // 发送消息（非流式）
  sendMessage(data: ChatRequest): Promise<ChatResponse> {
    return request.post('/chat', data)
  },

  // 流式对话
  streamChat(data: ChatRequest, onChunk: (chunk: string) => void): Promise<void> {
    return new Promise((resolve, reject) => {
      const eventSource = new EventSource(
        `/api/v1/chat/stream?conversation_id=${data.conversation_id}&content=${encodeURIComponent(data.content)}`
      )

      eventSource.onmessage = (event) => {
        if (event.data === '[DONE]') {
          eventSource.close()
          resolve()
          return
        }

        try {
          const chunk = JSON.parse(event.data)
          onChunk(chunk.content || '')
        } catch (error) {
          console.error('解析消息失败:', error)
        }
      }

      eventSource.onerror = (error) => {
        eventSource.close()
        reject(error)
      }
    })
  },

  // 获取对话列表
  getConversations(page = 1, pageSize = 20): Promise<Conversation[]> {
    return request.get('/conversations', {
      params: { page, page_size: pageSize }
    })
  },

  // 删除对话
  deleteConversation(id: number): Promise<void> {
    return request.delete(`/conversations/${id}`)
  }
}
```

### 4. Pinia 状态管理

```typescript
// stores/conversation.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { chatApi } from '@/api/chat'
import type { Conversation, Message } from '@/types/chat'

export const useConversationStore = defineStore('conversation', () => {
  // State
  const conversations = ref<Conversation[]>([])
  const currentConversation = ref<Conversation | null>(null)
  const messages = ref<Message[]>([])
  const loading = ref(false)

  // Getters
  const conversationCount = computed(() => conversations.value.length)
  const hasConversations = computed(() => conversationCount.value > 0)

  // Actions
  const loadConversations = async () => {
    loading.value = true
    try {
      conversations.value = await chatApi.getConversations()
    } catch (error) {
      console.error('加载对话列表失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const selectConversation = (conversation: Conversation) => {
    currentConversation.value = conversation
  }

  const deleteConversation = async (id: number) => {
    await chatApi.deleteConversation(id)
    conversations.value = conversations.value.filter(c => c.id !== id)
    if (currentConversation.value?.id === id) {
      currentConversation.value = null
    }
  }

  return {
    // State
    conversations,
    currentConversation,
    messages,
    loading,
    // Getters
    conversationCount,
    hasConversations,
    // Actions
    loadConversations,
    selectConversation,
    deleteConversation
  }
})
```

### 5. Composables（组合式函数）

```typescript
// composables/useChat.ts
import { ref } from 'vue'
import { chatApi } from '@/api/chat'
import type { Message } from '@/types/chat'

export function useChat(conversationId?: number) {
  const messages = ref<Message[]>([])
  const streaming = ref(false)
  const currentResponse = ref('')

  const sendMessage = async (content: string) => {
    // 添加用户消息
    const userMessage: Message = {
      id: Date.now(),
      role: 'user',
      content,
      created_at: new Date().toISOString()
    }
    messages.value.push(userMessage)

    // 开始流式响应
    streaming.value = true
    currentResponse.value = ''

    try {
      await chatApi.streamChat(
        { conversation_id: conversationId, content },
        (chunk) => {
          currentResponse.value += chunk
        }
      )

      // 添加助手消息
      const assistantMessage: Message = {
        id: Date.now() + 1,
        role: 'assistant',
        content: currentResponse.value,
        created_at: new Date().toISOString()
      }
      messages.value.push(assistantMessage)
    } catch (error) {
      console.error('发送消息失败:', error)
      throw error
    } finally {
      streaming.value = false
      currentResponse.value = ''
    }
  }

  return {
    messages,
    streaming,
    currentResponse,
    sendMessage
  }
}
```

## 常见功能实现

### 1. 流式消息展示

```vue
<script setup lang="ts">
import { ref, watch } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

interface Props {
  content: string
  streaming?: boolean
}

const props = defineProps<Props>()

const md = new MarkdownIt({
  highlight: (str, lang) => {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return hljs.highlight(str, { language: lang }).value
      } catch {}
    }
    return ''
  }
})

const renderedContent = ref('')

watch(() => props.content, (newContent) => {
  renderedContent.value = md.render(newContent)
}, { immediate: true })
</script>

<template>
  <div class="message">
    <div v-html="renderedContent" class="markdown-body"></div>
    <span v-if="streaming" class="cursor">▊</span>
  </div>
</template>

<style scoped>
.message {
  padding: 12px;
  border-radius: 8px;
  background: #f5f5f5;
}

.cursor {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}
</style>
```

### 2. 表单验证

```vue
<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'

interface LoginForm {
  username: string
  password: string
}

const formRef = ref<FormInstance>()
const form = ref<LoginForm>({
  username: '',
  password: ''
})

const rules: FormRules<LoginForm> = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度3-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8个字符', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate((valid) => {
    if (valid) {
      // 提交表单
      console.log('表单数据:', form.value)
    } else {
      ElMessage.error('请检查表单输入')
    }
  })
}
</script>

<template>
  <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
    <el-form-item label="用户名" prop="username">
      <el-input v-model="form.username" placeholder="请输入用户名" />
    </el-form-item>
    <el-form-item label="密码" prop="password">
      <el-input v-model="form.password" type="password" placeholder="请输入密码" />
    </el-form-item>
    <el-form-item>
      <el-button type="primary" @click="handleSubmit">登录</el-button>
    </el-form-item>
  </el-form>
</template>
```

### 3. 路由守卫

```typescript
// router/index.ts
import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/chat',
      name: 'Chat',
      component: () => import('@/views/Chat.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

// 全局前置守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'Chat' })
  } else {
    next()
  }
})

export default router
```

## 性能优化

### 1. 组件懒加载

```typescript
// 路由懒加载
const Chat = () => import('@/views/Chat.vue')

// 组件懒加载
import { defineAsyncComponent } from 'vue'

const AsyncComponent = defineAsyncComponent(() =>
  import('@/components/HeavyComponent.vue')
)
```

### 2. 虚拟滚动（长列表）

```vue
<script setup lang="ts">
import { ref } from 'vue'

const messages = ref(Array.from({ length: 10000 }, (_, i) => ({
  id: i,
  content: `消息 ${i}`
})))
</script>

<template>
  <el-virtual-list :data="messages" :item-size="50" height="600px">
    <template #default="{ item }">
      <div class="message-item">{{ item.content }}</div>
    </template>
  </el-virtual-list>
</template>
```

### 3. 防抖和节流

```typescript
// utils/debounce.ts
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout> | null = null

  return function (this: any, ...args: Parameters<T>) {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      fn.apply(this, args)
    }, delay)
  }
}

// 使用
import { debounce } from '@/utils/debounce'

const handleSearch = debounce((keyword: string) => {
  // 搜索逻辑
}, 300)
```

## 样式规范

### 1. 使用 Scoped CSS

```vue
<style scoped>
/* 组件样式只在当前组件生效 */
.container {
  padding: 20px;
}
</style>
```

### 2. CSS 变量

```css
/* styles/variables.css */
:root {
  --primary-color: #409eff;
  --success-color: #67c23a;
  --warning-color: #e6a23c;
  --danger-color: #f56c6c;
  --text-color: #303133;
  --border-color: #dcdfe6;
  --background-color: #f5f7fa;
}
```

### 3. 响应式设计

```css
/* 移动端优先 */
.container {
  padding: 10px;
}

/* 平板 */
@media (min-width: 768px) {
  .container {
    padding: 20px;
  }
}

/* 桌面 */
@media (min-width: 1024px) {
  .container {
    padding: 30px;
  }
}
```

## 测试

### 单元测试（Vitest）

```typescript
// MessageList.spec.ts
import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import MessageList from '@/components/chat/MessageList.vue'

describe('MessageList', () => {
  it('renders messages correctly', () => {
    const messages = [
      { id: 1, role: 'user', content: 'Hello', created_at: '2025-01-01' },
      { id: 2, role: 'assistant', content: 'Hi', created_at: '2025-01-01' }
    ]

    const wrapper = mount(MessageList, {
      props: { messages }
    })

    expect(wrapper.findAll('.message')).toHaveLength(2)
  })
})
```

## 常用命令

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产构建
npm run preview

# 运行测试
npm run test

# 运行测试（监听模式）
npm run test:watch

# 测试覆盖率
npm run test:coverage

# 类型检查
npm run type-check

# 代码格式化
npm run format

# 代码检查
npm run lint
```

## 协作接口

### 输入来源

- **架构 Skill**: API接口文档、数据格式定义
- **后端开发 Skill**: API接口实现、接口文档
- **UI Skill**: 设计稿、交互规范、组件设计

### 输出交付

- **给测试 Skill**: 组件测试用例、E2E测试场景
- **给UI Skill**: 实现效果反馈、交互优化建议

## 注意事项

1. **类型安全**: 所有API调用和数据都要有TypeScript类型定义
2. **错误处理**: 使用try-catch捕获异常，提供友好的错误提示
3. **加载状态**: 异步操作要显示加载状态
4. **响应式**: 确保在不同设备上都有良好体验
5. **性能**: 避免不必要的重渲染，使用虚拟滚动处理长列表
6. **可访问性**: 使用语义化HTML，支持键盘导航
7. **安全**: 防止XSS攻击，对用户输入进行转义
8. **代码复用**: 提取公共逻辑到composables
9. **组件粒度**: 保持组件单一职责，避免过大的组件
10. **文档注释**: 复杂组件和函数添加JSDoc注释
