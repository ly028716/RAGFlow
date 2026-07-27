<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading, User } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { authApi } from '@/api/auth'
import { userApi, type DeletionStatusResponse } from '@/api/user'
import AvatarUploader from '@/components/common/AvatarUploader.vue'
import PromptSelector from '@/components/common/PromptSelector.vue'

const authStore = useAuthStore()

const activeTab = ref('account') // Default to 'account' to match prototype grouping
const passwordFormRef = ref<FormInstance>()
const deletionFormRef = ref<FormInstance>()
const passwordLoading = ref(false)
const deletionLoading = ref(false)
const deletionStatusLoading = ref(false)
const deletionStatus = ref<DeletionStatusResponse | null>(null)

// Mock Configs for new tabs
const modelConfig = reactive({
  defaultModel: 'qwen-plus',
  apiKey: ''
})

const vectorConfig = reactive({
  prefix: 'kiro_kb_',
  embeddingModel: 'text-embedding-v3'
})

const cacheConfig = reactive({
  enabled: true,
  ttl: 3600
})

const passwordForm = reactive({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const deletionForm = reactive({
  password: '',
  reason: ''
})

const validateConfirmPassword = (rule: any, value: string, callback: any) => {
  if (value !== passwordForm.newPassword) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const passwordRules: FormRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少8位', trigger: 'blur' },
    { pattern: /^(?=.*[A-Za-z])(?=.*\d)/, message: '密码必须包含字母和数字', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const deletionRules: FormRules = {
  password: [
    { required: true, message: '请输入密码以确认身份', trigger: 'blur' }
  ]
}

// 是否有待处理的注销请求
const hasDeletionRequest = computed(() => deletionStatus.value?.has_deletion_request ?? false)

async function handleChangePassword() {
  if (!passwordFormRef.value) return

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return

    passwordLoading.value = true
    try {
      await authApi.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
      ElMessage.success('密码修改成功')
      passwordFormRef.value?.resetFields()
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '密码修改失败')
    } finally {
      passwordLoading.value = false
    }
  })
}

function handleAvatarChange(url: string | null) {
  if (authStore.user) {
    authStore.user.avatar = url || undefined
  }
}

// 获取注销状态
async function fetchDeletionStatus() {
  deletionStatusLoading.value = true
  try {
    deletionStatus.value = await userApi.getDeletionStatus()
  } catch (error: any) {
    console.error('获取注销状态失败:', error)
  } finally {
    deletionStatusLoading.value = false
  }
}

// 请求注销账号
async function handleRequestDeletion() {
  if (!deletionFormRef.value) return

  await deletionFormRef.value.validate(async (valid) => {
    if (!valid) return

    // 二次确认
    try {
      await ElMessageBox.confirm(
        '您确定要注销账号吗？注销后将有7天冷静期，期间可以取消。冷静期过后，您的所有数据将被永久删除，包括对话记录、知识库、文档等，且无法恢复。',
        '确认注销账号',
        {
          confirmButtonText: '确认注销',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger'
        }
      )
    } catch {
      return // 用户取消
    }

    deletionLoading.value = true
    try {
      const result = await userApi.requestDeletion({
        password: deletionForm.password,
        reason: deletionForm.reason || undefined
      })
      ElMessage.success(result.message)
      deletionFormRef.value?.resetFields()
      await fetchDeletionStatus()
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '注销请求失败')
    } finally {
      deletionLoading.value = false
    }
  })
}

// 取消注销请求
async function handleCancelDeletion() {
  try {
    await ElMessageBox.confirm(
      '确定要取消注销请求吗？取消后您的账号将恢复正常状态。',
      '取消注销',
      {
        confirmButtonText: '确认取消',
        cancelButtonText: '返回',
        type: 'info'
      }
    )
  } catch {
    return // 用户取消
  }

  deletionLoading.value = true
  try {
    const result = await userApi.cancelDeletion()
    ElMessage.success(result.message)
    await fetchDeletionStatus()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '取消注销失败')
  } finally {
    deletionLoading.value = false
  }
}

onMounted(() => {
  authStore.fetchUserInfo()
  fetchDeletionStatus()
})
</script>

<template>
  <div class="settings-view">
    <div class="settings-content">
      <el-tabs v-model="activeTab" class="settings-tabs">
        <!-- 账号设置 Tab -->
        <el-tab-pane label="账号设置" name="account">
          <div class="tab-content">
            <div class="section">
              <h3>基本信息</h3>
              <el-form label-position="top">
                <el-form-item label="头像">
                  <div class="avatar-setting">
                    <AvatarUploader 
                      :model-value="authStore.user?.avatar"
                      :size="64"
                      @change="handleAvatarChange"
                    />
                    <el-button size="small" style="margin-left: 12px">更换头像</el-button>
                  </div>
                </el-form-item>
                <el-form-item label="昵称">
                  <el-input :model-value="authStore.user?.full_name" placeholder="请输入昵称" />
                </el-form-item>
                <el-form-item label="邮箱">
                  <el-input :model-value="authStore.user?.email" disabled>
                    <template #append>(不可修改)</template>
                  </el-input>
                </el-form-item>
              </el-form>
            </div>
            
            <el-divider />
            
            <div class="section">
              <h3>安全设置</h3>
              <el-form label-position="top">
                <el-form-item label="登录密码">
                  <!-- 这里为了简化展示，实际应弹窗或跳子页 -->
                  <div class="password-change-area">
                     <el-form
                      ref="passwordFormRef"
                      :model="passwordForm"
                      :rules="passwordRules"
                      label-width="100px"
                      size="small"
                      style="max-width: 400px"
                    >
                      <el-form-item label="当前密码" prop="oldPassword">
                        <el-input v-model="passwordForm.oldPassword" type="password" show-password />
                      </el-form-item>
                      <el-form-item label="新密码" prop="newPassword">
                        <el-input v-model="passwordForm.newPassword" type="password" show-password />
                      </el-form-item>
                      <el-form-item label="确认密码" prop="confirmPassword">
                        <el-input v-model="passwordForm.confirmPassword" type="password" show-password />
                      </el-form-item>
                      <el-form-item>
                        <el-button type="primary" :loading="passwordLoading" @click="handleChangePassword">修改密码</el-button>
                      </el-form-item>
                    </el-form>
                  </div>
                </el-form-item>
                
                <el-form-item label="账号注销">
                   <div v-if="!hasDeletionRequest">
                      <el-button type="danger" plain @click="activeTab = 'danger-zone'">前往注销页面</el-button>
                   </div>
                   <div v-else>
                      <el-tag type="warning">注销申请进行中</el-tag>
                      <el-button type="text" @click="activeTab = 'danger-zone'">查看详情</el-button>
                   </div>
                </el-form-item>
              </el-form>
            </div>
          </div>
        </el-tab-pane>

        <!-- 模型与密钥 Tab -->
        <el-tab-pane label="模型与密钥" name="models">
          <div class="tab-content">
            <div class="section">
              <h3>LLM 模型配置</h3>
              <el-form label-position="top">
                <el-form-item label="默认模型">
                  <el-select v-model="modelConfig.defaultModel">
                    <el-option label="qwen-plus" value="qwen-plus" />
                  </el-select>
                </el-form-item>
                <el-form-item label="API Key">
                  <el-input v-model="modelConfig.apiKey" type="password" show-password placeholder="sk-..." />
                  <p class="hint">设置后将覆盖系统默认 Key</p>
                </el-form-item>
              </el-form>
            </div>
            
            <el-divider />
            
            <div class="section">
              <h3>提示词管理</h3>
              <PromptSelector :show-manage="true" />
            </div>
          </div>
        </el-tab-pane>

        <!-- 向量库配置 Tab -->
        <el-tab-pane label="向量库配置" name="vector">
          <div class="tab-content">
             <div class="section">
              <h3>向量数据库 (Chroma)</h3>
              <el-form label-position="top">
                <el-form-item label="Collection Prefix">
                  <el-input v-model="vectorConfig.prefix" placeholder="kiro_kb_" />
                </el-form-item>
                <el-form-item label="Embedding Model">
                  <el-select v-model="vectorConfig.embeddingModel">
                    <el-option label="text-embedding-v3" value="text-embedding-v3" />
                  </el-select>
                </el-form-item>
              </el-form>
             </div>
          </div>
        </el-tab-pane>

        <!-- 缓存与限流 Tab -->
        <el-tab-pane label="缓存与限流" name="cache">
           <div class="tab-content">
             <div class="section">
               <h3>缓存设置</h3>
               <el-form label-position="top">
                 <el-form-item label="启用 LLM 缓存">
                   <el-switch v-model="cacheConfig.enabled" />
                 </el-form-item>
                 <el-form-item label="TTL (秒)">
                   <el-input-number v-model="cacheConfig.ttl" :min="60" />
                 </el-form-item>
               </el-form>
             </div>
           </div>
        </el-tab-pane>

        <!-- 统计与健康 Tab -->
        <el-tab-pane label="统计与健康" name="stats">
           <div class="tab-content">
             <div class="section">
               <h3>系统状态</h3>
               <div class="stats-grid">
                 <div class="stat-card">
                   <div class="label">API 状态</div>
                   <div class="value success">Running</div>
                 </div>
                 <div class="stat-card">
                   <div class="label">Token 消耗 (本月)</div>
                   <div class="value">12,500</div>
                 </div>
                 <div class="stat-card">
                   <div class="label">RAG 检索次数</div>
                   <div class="value">85</div>
                 </div>
               </div>
             </div>
           </div>
        </el-tab-pane>
        
        <!-- 隐藏的 Danger Zone Tab (用于注销详情) -->
        <el-tab-pane label="注销详情" name="danger-zone" v-if="true">
           <div class="tab-content">
              <h3>账号注销管理</h3>
              <!-- 加载状态 -->
              <div v-if="deletionStatusLoading" class="loading-state">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>加载中...</span>
              </div>
              
              <!-- 已有注销请求 -->
              <template v-else-if="hasDeletionRequest">
                <el-alert
                  type="warning"
                  :closable="false"
                  show-icon
                  class="deletion-alert"
                >
                  <template #title>
                    <span class="alert-title">账号注销请求已提交</span>
                  </template>
                  <template #default>
                    <div class="deletion-info">
                      <p>{{ deletionStatus?.message }}</p>
                      <el-descriptions :column="1" size="small" class="deletion-details">
                        <el-descriptions-item label="请求时间">
                          {{ deletionStatus?.requested_at ? new Date(deletionStatus.requested_at).toLocaleString() : '-' }}
                        </el-descriptions-item>
                        <el-descriptions-item label="计划删除时间">
                          {{ deletionStatus?.scheduled_at ? new Date(deletionStatus.scheduled_at).toLocaleString() : '-' }}
                        </el-descriptions-item>
                        <el-descriptions-item v-if="deletionStatus?.reason" label="注销原因">
                          {{ deletionStatus.reason }}
                        </el-descriptions-item>
                        <el-descriptions-item label="剩余时间">
                          <span class="remaining-time">
                            {{ deletionStatus?.remaining_days }} 天 {{ deletionStatus?.remaining_hours }} 小时
                          </span>
                        </el-descriptions-item>
                      </el-descriptions>
                      <div class="deletion-actions" v-if="deletionStatus?.can_cancel">
                        <el-button
                          type="primary"
                          :loading="deletionLoading"
                          @click="handleCancelDeletion"
                        >
                          取消注销请求
                        </el-button>
                      </div>
                    </div>
                  </template>
                </el-alert>
              </template>
              
              <!-- 无注销请求，显示注销表单 -->
              <template v-else>
                <el-alert
                  type="info"
                  :closable="false"
                  show-icon
                  class="deletion-warning"
                >
                  <template #title>注销须知</template>
                  <template #default>
                    <ul class="warning-list">
                      <li>注销账号后，您的所有数据将被永久删除，包括对话记录、知识库、文档等</li>
                      <li>注销请求提交后有 <strong>7天冷静期</strong>，期间您可以随时取消</li>
                      <li>冷静期过后，账号将被自动删除，且无法恢复</li>
                      <li>请确保您已备份重要数据</li>
                    </ul>
                  </template>
                </el-alert>
                
                <el-form
                  ref="deletionFormRef"
                  :model="deletionForm"
                  :rules="deletionRules"
                  label-width="100px"
                  style="max-width: 500px; margin-top: 20px"
                >
                  <el-form-item label="确认密码" prop="password">
                    <el-input
                      v-model="deletionForm.password"
                      type="password"
                      placeholder="请输入密码以确认身份"
                      show-password
                    />
                  </el-form-item>
                  <el-form-item label="注销原因">
                    <el-input
                      v-model="deletionForm.reason"
                      type="textarea"
                      :rows="3"
                      placeholder="请告诉我们您注销的原因（可选）"
                      maxlength="500"
                      show-word-limit
                    />
                  </el-form-item>
                  <el-form-item>
                    <el-button
                      type="danger"
                      :loading="deletionLoading"
                      @click="handleRequestDeletion"
                    >
                      申请注销账号
                    </el-button>
                  </el-form-item>
                </el-form>
              </template>
           </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<style scoped lang="scss">
.settings-view {
  height: 100%;
  padding: 20px;
  background: white;
  overflow-y: auto;
}

.settings-content {
  max-width: 900px;
  margin: 0 auto;
}

.settings-tabs {
  // Tabs styles
}

.section {
  padding: 20px 0;
  
  h3 {
    margin-bottom: 20px;
    font-size: 16px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    border-left: 4px solid var(--el-color-primary);
    padding-left: 12px;
  }
}

.avatar-setting {
  display: flex;
  align-items: center;
}

.hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  
  .stat-card {
    padding: 16px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
    
    .label {
      font-size: 13px;
      color: var(--el-text-color-secondary);
      margin-bottom: 8px;
    }
    
    .value {
      font-size: 20px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      
      &.success {
        color: var(--el-color-success);
      }
    }
  }
}

.password-change-area {
  padding: 16px;
  background: var(--el-fill-color-light);
  border-radius: 8px;
}

// Reuse deletion styles
.loading-state {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--el-text-color-secondary);
  padding: 20px;
}

.deletion-alert {
  margin-bottom: 20px;
  .alert-title { font-weight: 600; }
}

.deletion-info {
  p { margin-bottom: 12px; color: var(--el-text-color-regular); }
}

.remaining-time {
  color: var(--el-color-warning);
  font-weight: 600;
}

.warning-list {
  margin: 8px 0 0 0;
  padding-left: 20px;
  
  li {
    margin-bottom: 8px;
    color: var(--el-text-color-regular);
    line-height: 1.6;
    strong { color: var(--el-color-warning); }
  }
}
</style>
