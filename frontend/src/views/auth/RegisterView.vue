<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  agreement: false
})

const validatePassword = (rule: any, value: string, callback: any) => {
  if (value === '') {
    callback(new Error('请输入密码'))
  } else if (!/[A-Za-z]/.test(value)) {
    callback(new Error('密码必须包含字母'))
  } else if (!/\d/.test(value)) {
    callback(new Error('密码必须包含数字'))
  } else {
    if (form.confirmPassword !== '') {
      formRef.value?.validateField('confirmPassword')
    }
    callback()
  }
}

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value === '') {
    callback(new Error('请再次输入密码'))
  } else if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
    { min: 3, max: 50, message: '用户名长度为3-50个字符', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '用户名只能包含字母、数字和下划线', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
    { validator: validatePassword, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

async function handleRegister() {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    loading.value = true
    try {
      const success = await authStore.register(
        form.username,
        form.password
      )
      if (success) {
        ElMessage.success('注册成功，请登录')
        router.push('/login')
      }
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '注册失败')
    } finally {
      loading.value = false
    }
  })
}

function goToLogin() {
  router.push('/login')
}
</script>

<template>
  <div class="register-view">
    <div class="register-header">
      <h1 class="app-title">AI 智能助手</h1>
      <h2 class="form-title">用户注册</h2>
    </div>
    
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      @submit.prevent="handleRegister"
    >
      <el-form-item label="用户名" prop="username">
        <el-input
          v-model="form.username"
          placeholder="请输入用户名"
          :prefix-icon="User"
          size="large"
        />
      </el-form-item>

      <el-form-item label="设置密码 (8位+)" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          placeholder="至少8位，包含字母和数字"
          :prefix-icon="Lock"
          size="large"
          show-password
        />
      </el-form-item>

      <el-form-item label="确认密码" prop="confirmPassword">
        <el-input
          v-model="form.confirmPassword"
          type="password"
          placeholder="请再次输入密码"
          :prefix-icon="Lock"
          size="large"
          show-password
          @keyup.enter="handleRegister"
        />
      </el-form-item>

      <el-form-item prop="agreement">
        <el-checkbox v-model="form.agreement">
          我已阅读并同意 <el-link type="primary" :underline="false">《用户协议》</el-link>
        </el-checkbox>
      </el-form-item>

      <el-form-item>
        <el-button
          type="primary"
          size="large"
          :loading="loading"
          @click="handleRegister"
          class="submit-btn"
          :disabled="!form.agreement"
        >
          注 册
        </el-button>
      </el-form-item>
    </el-form>

    <div class="form-footer">
      <span>已有账号？</span>
      <el-button type="primary" link @click="goToLogin">去登录</el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.register-view {
  .register-header {
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
