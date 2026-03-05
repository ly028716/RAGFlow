import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false, layout: 'auth' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { requiresAuth: false, layout: 'auth' }
  },
  {
    path: '/',
    name: 'Home',
    redirect: '/chat'
  },
  {
    path: '/chat',
    name: 'Chat',
    component: () => import('@/views/chat/ChatView.vue'),
    meta: { requiresAuth: true, title: '智能对话' }
  },
  {
    path: '/chat/:id',
    name: 'ChatDetail',
    component: () => import('@/views/chat/ChatView.vue'),
    meta: { requiresAuth: true, title: '智能对话' }
  },
  {
    path: '/knowledge',
    name: 'Knowledge',
    component: () => import('@/views/knowledge/KnowledgeView.vue'),
    meta: { requiresAuth: true, title: '知识库' }
  },
  {
    path: '/agent',
    name: 'Agent',
    component: () => import('@/views/agent/AgentView.vue'),
    meta: { requiresAuth: true, title: 'Agent' }
  },
  {
    path: '/web-scraper',
    name: 'WebScraper',
    component: () => import('@/views/WebScraperView.vue'),
    meta: { requiresAuth: true, title: '网页采集' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/settings/SettingsView.vue'),
    meta: { requiresAuth: true, title: '设置' }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFound.vue')
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()

  // 需要认证但未登录
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  // 已登录访问登录/注册页
  if (!to.meta.requiresAuth && authStore.isAuthenticated && 
      (to.name === 'Login' || to.name === 'Register')) {
    next({ name: 'Chat' })
    return
  }

  next()
})

export default router
