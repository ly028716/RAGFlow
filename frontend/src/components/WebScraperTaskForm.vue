<template>
  <el-dialog
    :model-value="visible"
    :title="isEdit ? '编辑任务' : '创建任务'"
    width="800px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="120px"
    >
      <!-- 基本信息 -->
      <el-form-item label="任务名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入任务名称" />
      </el-form-item>

      <el-form-item label="任务描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="2"
          placeholder="请输入任务描述（可选）"
        />
      </el-form-item>

      <el-form-item label="目标URL" prop="url">
        <el-input v-model="form.url" placeholder="https://example.com/article" />
      </el-form-item>

      <el-form-item label="知识库" prop="knowledge_base_id">
        <el-select
          v-model="form.knowledge_base_id"
          placeholder="请选择知识库"
          style="width: 100%"
        >
          <el-option
            v-for="kb in knowledgeBases"
            :key="kb.id"
            :label="kb.name"
            :value="kb.id"
          />
        </el-select>
      </el-form-item>

      <!-- 调度配置 -->
      <el-form-item label="调度类型" prop="schedule_type">
        <el-radio-group v-model="form.schedule_type">
          <el-radio value="once">一次性执行</el-radio>
          <el-radio value="cron">定时执行</el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item
        v-if="form.schedule_type === 'cron'"
        label="Cron表达式"
        prop="cron_expression"
      >
        <el-input
          v-model="form.cron_expression"
          placeholder="0 0 * * * (每天凌晨0点)"
        >
          <template #append>
            <el-button @click="showCronHelp">帮助</el-button>
          </template>
        </el-input>
        <div class="form-tip">
          示例：0 0 * * * (每天0点) | 0 */6 * * * (每6小时) | 0 9 * * 1 (每周一9点)
        </div>
      </el-form-item>

      <!-- 选择器配置 -->
      <el-divider content-position="left">选择器配置</el-divider>

      <el-form-item label="标题选择器" prop="selector_config.title">
        <el-input
          v-model="form.selector_config.title"
          placeholder="h1.article-title"
        />
      </el-form-item>

      <el-form-item label="内容选择器" prop="selector_config.content">
        <el-input
          v-model="form.selector_config.content"
          placeholder="div.article-content"
        />
      </el-form-item>

      <el-form-item label="作者选择器">
        <el-input
          v-model="form.selector_config.author"
          placeholder="span.author-name（可选）"
        />
      </el-form-item>

      <el-form-item label="排除选择器">
        <el-select
          v-model="form.selector_config.exclude"
          multiple
          filterable
          allow-create
          placeholder="输入后按回车添加"
          style="width: 100%"
        >
        </el-select>
        <div class="form-tip">
          排除不需要的元素，如：script, style, .advertisement
        </div>
      </el-form-item>

      <!-- 采集器配置 -->
      <el-divider content-position="left">采集器配置</el-divider>

      <el-form-item label="等待选择器" prop="scraper_config.wait_for_selector">
        <el-input
          v-model="form.scraper_config.wait_for_selector"
          placeholder="body"
        />
      </el-form-item>

      <el-form-item label="等待超时">
        <el-input-number
          v-model="form.scraper_config.wait_timeout"
          :min="1000"
          :max="120000"
          :step="1000"
          style="width: 100%"
        />
        <div class="form-tip">单位：毫秒，范围：1000-120000</div>
      </el-form-item>

      <el-form-item label="重试次数">
        <el-input-number
          v-model="form.scraper_config.retry_times"
          :min="1"
          :max="10"
          style="width: 100%"
        />
      </el-form-item>

      <el-form-item label="重试延迟">
        <el-input-number
          v-model="form.scraper_config.retry_delay"
          :min="1"
          :max="60"
          style="width: 100%"
        />
        <div class="form-tip">单位：秒</div>
      </el-form-item>

      <el-form-item label="截图">
        <el-switch v-model="form.scraper_config.screenshot" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ isEdit ? '更新' : '创建' }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { useWebScraperStore } from '@/stores/webScraper'
import { useKnowledgeStore } from '@/stores/knowledge'
import type { Task, TaskCreateRequest, SelectorConfig, ScraperConfig } from '@/types/webScraper'

interface Props {
  visible: boolean
  task?: Task | null
}

interface Emits {
  (e: 'update:visible', value: boolean): void
  (e: 'success'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const store = useWebScraperStore()
const knowledgeStore = useKnowledgeStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const isEdit = computed(() => !!props.task)

// 表单数据
const form = ref<TaskCreateRequest>({
  name: '',
  description: '',
  url: '',
  knowledge_base_id: 0,
  schedule_type: 'once',
  cron_expression: '',
  selector_config: {
    title: '',
    content: '',
    author: '',
    exclude: []
  },
  scraper_config: {
    wait_for_selector: 'body',
    wait_timeout: 30000,
    screenshot: false,
    retry_times: 3,
    retry_delay: 5
  }
})

// 知识库列表
const knowledgeBases = computed(() => knowledgeStore.knowledgeBases)

// 表单验证规则
const rules: FormRules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' },
    { min: 1, max: 200, message: '长度在 1 到 200 个字符', trigger: 'blur' }
  ],
  url: [
    { required: true, message: '请输入目标URL', trigger: 'blur' },
    {
      pattern: /^https?:\/\/.+/,
      message: 'URL必须以http://或https://开头',
      trigger: 'blur'
    }
  ],
  knowledge_base_id: [
    { required: true, message: '请选择知识库', trigger: 'change' }
  ],
  cron_expression: [
    {
      validator: (rule, value, callback) => {
        if (form.value.schedule_type === 'cron' && !value) {
          callback(new Error('定时任务必须提供Cron表达式'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ],
  'selector_config.title': [
    { required: true, message: '请输入标题选择器', trigger: 'blur' }
  ],
  'selector_config.content': [
    { required: true, message: '请输入内容选择器', trigger: 'blur' }
  ],
  'scraper_config.wait_for_selector': [
    { required: true, message: '请输入等待选择器', trigger: 'blur' }
  ]
}

// 初始化表单
const initForm = () => {
  if (props.task) {
    form.value = {
      name: props.task.name,
      description: props.task.description || '',
      url: props.task.url,
      knowledge_base_id: props.task.knowledge_base_id,
      schedule_type: props.task.schedule_type,
      cron_expression: props.task.cron_expression || '',
      selector_config: JSON.parse(JSON.stringify(props.task.selector_config)),
      scraper_config: JSON.parse(JSON.stringify(props.task.scraper_config))
    }
  } else {
    form.value = {
      name: '',
      description: '',
      url: '',
      knowledge_base_id: 0,
      schedule_type: 'once',
      cron_expression: '',
      selector_config: {
        title: '',
        content: '',
        author: '',
        exclude: []
      },
      scraper_config: {
        wait_for_selector: 'body',
        wait_timeout: 30000,
        screenshot: false,
        retry_times: 3,
        retry_delay: 5
      }
    }
  }
}

// 显示Cron帮助
const showCronHelp = () => {
  ElMessageBox.alert(
    `Cron表达式格式：分 时 日 月 周

示例：
• 0 0 * * * - 每天凌晨0点
• 0 */6 * * * - 每6小时
• 0 9 * * 1 - 每周一上午9点
• 0 0 1 * * - 每月1号凌晨0点
• 30 8 * * 1-5 - 工作日上午8:30

在线工具：https://crontab.guru/`,
    'Cron表达式帮助',
    { confirmButtonText: '知道了' }
  )
}

// 提交表单
const handleSubmit = async () => {
  if (!formRef.value) return

  try {
    await formRef.value.validate()
    submitting.value = true

    if (isEdit.value && props.task) {
      await store.updateTask(props.task.id, form.value)
    } else {
      await store.createTask(form.value)
    }

    emit('success')
    handleClose()
  } catch (error) {
    console.error('表单提交失败:', error)
  } finally {
    submitting.value = false
  }
}

// 关闭对话框
const handleClose = () => {
  emit('update:visible', false)
  formRef.value?.resetFields()
}

// 监听对话框打开
watch(() => props.visible, (visible) => {
  if (visible) {
    initForm()
  }
})

// 加载知识库列表
onMounted(async () => {
  if (knowledgeBases.value.length === 0) {
    await knowledgeStore.fetchKnowledgeBases()
  }
})
</script>

<style scoped>
.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

:deep(.el-divider__text) {
  font-weight: 600;
  color: #303133;
}
</style>
