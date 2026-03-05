<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Plus, ChatDotRound, Document, Cpu, Setting, User, SwitchButton, ArrowDown, MagicStick, Expand, Fold, Monitor } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useConversationStore } from '@/stores/conversation'
import ChatList from '@/components/chat/ChatList.vue'
import OpenClawStatus from '@/components/OpenClawStatus.vue'
import DegradationBanner from '@/components/DegradationBanner.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const conversationStore = useConversationStore()

const sidebarCollapsed = ref(false)

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    '/chat': '智能对话',
    '/knowledge': '知识库管理',
    '/agent': 'Agent 工具',
    '/web-scraper': '网页采集',
    '/settings': '系统设置'
  }
  const basePath = '/' + route.path.split('/')[1]
  return titles[basePath] || 'AI 智能助手'
})

const showChatList = computed(() => true)

function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

async function createNewChat() {
  const conversation = await conversationStore.createConversation()
  if (conversation) {
    router.push(`/chat/${conversation.id}`)
  }
}

function goToProfile() {
  router.push('/settings')
}

async function handleLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    authStore.logout()
    router.push('/login')
  } catch {
    // 取消操作
  }
}

onMounted(() => {
  if (authStore.isAuthenticated) {
    conversationStore.fetchConversations()
  }
})
</script>

<template>
  <div class="default-layout" :class="{ collapsed: sidebarCollapsed }">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo" v-show="!sidebarCollapsed">
          <el-icon :size="24"><MagicStick /></el-icon>
          <span>AI 智能助手</span>
        </div>
        <el-button 
          :icon="sidebarCollapsed ? 'Expand' : 'Fold'" 
          @click="toggleSidebar"
          text
          class="collapse-btn"
        />
      </div>

      <nav class="sidebar-nav">
        <router-link to="/chat" class="nav-item" :class="{ active: route.path.startsWith('/chat') }">
          <el-icon><ChatDotRound /></el-icon>
          <span v-show="!sidebarCollapsed">智能对话</span>
        </router-link>
        <router-link to="/knowledge" class="nav-item" :class="{ active: route.path === '/knowledge' }">
          <el-icon><Document /></el-icon>
          <span v-show="!sidebarCollapsed">知识库</span>
        </router-link>
        <router-link to="/agent" class="nav-item" :class="{ active: route.path === '/agent' }">
          <el-icon><Cpu /></el-icon>
          <span v-show="!sidebarCollapsed">Agent 工具</span>
        </router-link>
        <router-link to="/web-scraper" class="nav-item" :class="{ active: route.path === '/web-scraper' }">
          <el-icon><Monitor /></el-icon>
          <span v-show="!sidebarCollapsed">网页采集</span>
        </router-link>
        <router-link to="/settings" class="nav-item" :class="{ active: route.path === '/settings' }">
          <el-icon><Setting /></el-icon>
          <span v-show="!sidebarCollapsed">系统设置</span>
        </router-link>
      </nav>

      <!-- 对话列表 (Always visible if space permits, or collapsed logic) -->
      <!-- In prototype, Chat List is below menus. -->
      <div class="chat-list-section">
        <div class="section-header" v-show="!sidebarCollapsed">
          <span>对话列表</span>
          <el-button :icon="Plus" size="small" @click="createNewChat" circle />
        </div>
        <el-button 
          v-show="sidebarCollapsed" 
          :icon="Plus" 
          @click="createNewChat" 
          class="new-chat-btn-collapsed"
          circle
        />
        <ChatList :collapsed="sidebarCollapsed" />
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <header class="app-header">
        <div class="header-title">{{ pageTitle }}</div>
        <div class="header-actions">
          <OpenClawStatus />
          <el-dropdown trigger="click">
            <div class="user-info">
              <el-avatar :size="32" :src="authStore.avatar || undefined">
                {{ authStore.username?.charAt(0)?.toUpperCase() }}
              </el-avatar>
              <span class="username">{{ authStore.username }}</span>
              <el-icon><ArrowDown /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="goToProfile">
                  <el-icon><User /></el-icon>个人中心
                </el-dropdown-item>
                <el-dropdown-item divided @click="handleLogout">
                  <el-icon><SwitchButton /></el-icon>退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <!-- 降级提示横幅 -->
      <DegradationBanner />

      <div class="content-wrapper">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped lang="scss">
.default-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: $sidebar-width;
  background: $sidebar-bg;
  display: flex;
  flex-direction: column;
  transition: width $transition-duration;
  
  .collapsed & {
    width: $sidebar-collapsed-width;
  }
}

.sidebar-header {
  height: $header-height;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    color: white;
    font-size: 18px;
    font-weight: 600;
  }

  .collapse-btn {
    color: $sidebar-text;
  }
}

.sidebar-nav {
  padding: 12px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  color: $sidebar-text;
  border-radius: 8px;
  margin-bottom: 4px;
  text-decoration: none;
  transition: all 0.2s;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  &.active {
    background: $sidebar-active-bg;
    color: white;
  }

  .el-icon {
    font-size: 20px;
  }

  .collapsed & {
    justify-content: center;
    padding: 12px;
  }
}

.chat-list-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding: 0 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: 8px;
  padding-top: 12px;

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 8px 12px;
    color: $sidebar-text;
    font-size: 12px;
  }

  .new-chat-btn-collapsed {
    margin: 0 auto 12px;
  }
}

.sidebar-footer {
  padding: 12px 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: $bg-page;
}

.app-header {
  height: $header-height;
  background: white;
  border-bottom: 1px solid $border-light;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;

  .header-title {
    font-size: 18px;
    font-weight: 600;
    color: $text-primary;
  }

  .user-info {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 8px;
    transition: background 0.2s;

    &:hover {
      background: $bg-light;
    }

    .username {
      color: $text-regular;
      font-size: 14px;
    }
  }
}

.content-wrapper {
  flex: 1;
  overflow: hidden;
}
</style>
