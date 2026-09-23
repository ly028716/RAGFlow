<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const rememberMe = ref(false)

const form = reactive({
  username: '',
  password: ''
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' }
  ]
}

async function handleLogin() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const success = await authStore.login(form.username, form.password)
      if (success) {
        ElMessage.success('登录成功')
        const redirect = route.query.redirect as string
        router.push(redirect || '/chat')
      } else {
        ElMessage.error('用户名或密码错误')
      }
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '登录失败')
    } finally {
      loading.value = false
    }
  })
}

function goToRegister() {
  router.push('/register')
}
</script>

<template>
  <div class="login-view">
    <div class="login-header">
      <h1 class="app-title">AI 智能助手</h1>
      <h2 class="form-title">用户登录</h2>
    </div>
    
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleLogin"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="form.username"
          placeholder="请输入用户名"
          :prefix-icon="User"
          size="large"
        />
      </el-form-item>

      <el-form-item label="密码" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          placeholder="请输入密码"
          :prefix-icon="Lock"
          size="large"
          show-password
          @keyup.enter="handleLogin"
        />
      </el-form-item>

      <div class="form-options">
        <el-checkbox v-model="rememberMe">记住我</el-checkbox>
        <el-link type="primary" :underline="false">忘记密码?</el-link>
      </div>

      <el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="handleLogin"
          class="submit-btn"
        >
          登 录
        </el-button>
      </el-form-item>
    </el-form>

    <div class="form-footer">
      <span>还没有账号？</span>
      <el-button type="primary" link @click="goToRegister">去注册</el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-view {
  .login-header {
    text-align: center;
    margin-bottom: 24px;
    
    .app-title {
      font-size: 24px;
      font-weight: bold;
      color: $text-primary;
      margin-bottom: 8px;
    }
    
    .form-title {
      color: $text-secondary;
      font-size: 18px;
      font-weight: normal;
    }
  }

  .form-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
  }

  .submit-btn {
    width: 100%;
    margin-top: 8px;
  }

  .form-footer {
    text-align: center;
    margin-top: 16px;
    color: $text-secondary;
    font-size: 14px;
  }
}
</style>
