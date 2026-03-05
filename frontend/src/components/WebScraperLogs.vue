<template>
  <div class="web-scraper-logs">
    <!-- 统计信息 -->
    <div v-if="statistics" class="statistics">
      <el-row :gutter="16">
        <el-col :span="6">
          <el-statistic title="总执行次数" :value="statistics.total" />
        </el-col>
        <el-col :span="6">
          <el-statistic title="成功次数" :value="statistics.success">
            <template #suffix>
              <el-icon color="#67c23a"><SuccessFilled /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="失败次数" :value="statistics.failed">
            <template #suffix>
              <el-icon color="#f56c6c"><CircleCloseFilled /></el-icon>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="6">
          <el-statistic title="成功率" :value="statistics.success_rate" :precision="1" suffix="%" />
        </el-col>
      </el-row>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-form :inline="true">
        <el-form-item label="状态">
          <el-select v-model="filterStatus" placeholder="全部" clearable @change="handleFilter">
            <el-option label="运行中" value="running" />
            <el-option label="成功" value="success" />
            <el-option label="失败" value="failed" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="handleRefresh">刷新</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 日志列表 -->
    <el-table
      v-loading="store.logsLoading"
      :data="store.logs"
      stripe
      style="width: 100%"
    >
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="log-details">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="开始时间">
                {{ formatDateTime(row.start_time) }}
              </el-descriptions-item>
              <el-descriptions-item label="结束时间">
                {{ row.end_time ? formatDateTime(row.end_time) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="抓取页面数">
                {{ row.pages_scraped }}
              </el-descriptions-item>
              <el-descriptions-item label="创建文档数">
                {{ row.documents_created }}
              </el-descriptions-item>
            </el-descriptions>

            <!-- 执行详情 -->
            <div v-if="row.execution_details" class="execution-details">
              <h4>执行详情</h4>

              <!-- 处理时间 -->
              <div v-if="row.execution_details.processing_time" class="time-info">
                <p><strong>处理时间：</strong></p>
                <ul>
                  <li>抓取: {{ row.execution_details.processing_time.scraping?.toFixed(2) }}秒</li>
                  <li>处理: {{ row.execution_details.processing_time.processing?.toFixed(2) }}秒</li>
                  <li>存储: {{ row.execution_details.processing_time.storing?.toFixed(2) }}秒</li>
                  <li v-if="row.execution_details.processing_time.total">
                    总计: {{ row.execution_details.processing_time.total.toFixed(2) }}秒
                  </li>
                </ul>
              </div>

              <!-- 处理的URL -->
              <div v-if="row.execution_details.urls_processed?.length" class="urls-info">
                <p><strong>处理的URL：</strong></p>
                <ul>
                  <li v-for="(url, index) in row.execution_details.urls_processed" :key="index">
                    <a :href="url" target="_blank" rel="noopener noreferrer">{{ url }}</a>
                  </li>
                </ul>
              </div>

              <!-- 创建的文档 -->
              <div v-if="row.execution_details.documents?.length" class="documents-info">
                <p><strong>创建的文档：</strong></p>
                <el-table :data="row.execution_details.documents" size="small" border>
                  <el-table-column prop="title" label="标题" min-width="200" />
                  <el-table-column prop="url" label="URL" min-width="200" show-overflow-tooltip />
                  <el-table-column prop="document_id" label="文档ID" width="100" />
                </el-table>
              </div>

              <!-- 错误信息 -->
              <div v-if="row.execution_details.errors?.length" class="errors-info">
                <p><strong>错误列表：</strong></p>
                <ul>
                  <li v-for="(error, index) in row.execution_details.errors" :key="index" class="error-item">
                    {{ error }}
                  </li>
                </ul>
              </div>
            </div>

            <!-- 错误消息 -->
            <div v-if="row.error_message" class="error-message">
              <el-alert type="error" :closable="false">
                <template #title>
                  <strong>错误信息：</strong>
                </template>
                <pre>{{ row.error_message }}</pre>
              </el-alert>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="id" label="ID" width="80" />

      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)" size="small">
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="start_time" label="开始时间" width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.start_time) }}
        </template>
      </el-table-column>

      <el-table-column label="耗时" width="100">
        <template #default="{ row }">
          {{ getDuration(row) }}
        </template>
      </el-table-column>

      <el-table-column prop="pages_scraped" label="抓取页面" width="100" />
      <el-table-column prop="documents_created" label="创建文档" width="100" />

      <el-table-column label="结果" min-width="200">
        <template #default="{ row }">
          <span v-if="row.status === 'running'" class="running-text">
            <el-icon class="is-loading"><Loading /></el-icon>
            执行中...
          </span>
          <span v-else-if="row.status === 'success'" class="success-text">
            执行成功
          </span>
          <span v-else-if="row.error_message" class="error-text">
            {{ row.error_message.substring(0, 50) }}{{ row.error_message.length > 50 ? '...' : '' }}
          </span>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="store.totalLogs"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { SuccessFilled, CircleCloseFilled, Loading } from '@element-plus/icons-vue'
import { useWebScraperStore } from '@/stores/webScraper'
import { webScraperApi } from '@/api/webScraper'
import type { Log, LogStatus, LogStatisticsResponse } from '@/types/webScraper'

interface Props {
  taskId: number
}

const props = defineProps<Props>()

const store = useWebScraperStore()

// 筛选状态
const filterStatus = ref<LogStatus | ''>('')

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20
})

// 统计信息
const statistics = ref<LogStatisticsResponse | null>(null)

// 自动刷新定时器
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 是否有运行中的日志
const hasRunningLogs = computed(() => store.runningLogs.length > 0)

// 加载日志列表
const loadLogs = async () => {
  const params = {
    status: filterStatus.value || undefined,
    skip: (pagination.value.page - 1) * pagination.value.pageSize,
    limit: pagination.value.pageSize
  }
  await store.loadLogs(props.taskId, params)
}

// 加载统计信息
const loadStatistics = async () => {
  try {
    statistics.value = await webScraperApi.getLogStatistics(props.taskId)
  } catch (error) {
    console.error('加载统计信息失败:', error)
  }
}

// 筛选
const handleFilter = () => {
  pagination.value.page = 1
  loadLogs()
}

// 刷新
const handleRefresh = () => {
  loadLogs()
  loadStatistics()
}

// 分页变化
const handlePageChange = () => {
  loadLogs()
}

const handleSizeChange = () => {
  pagination.value.page = 1
  loadLogs()
}

// 获取状态类型
const getStatusType = (status: LogStatus) => {
  const typeMap = {
    running: 'warning',
    success: 'success',
    failed: 'danger'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: LogStatus) => {
  const textMap = {
    running: '运行中',
    success: '成功',
    failed: '失败'
  }
  return textMap[status] || status
}

// 格式化日期时间
const formatDateTime = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 获取执行时长
const getDuration = (log: Log) => {
  if (!log.end_time) {
    return '-'
  }
  const start = new Date(log.start_time).getTime()
  const end = new Date(log.end_time).getTime()
  const duration = (end - start) / 1000

  if (duration < 60) {
    return `${duration.toFixed(1)}秒`
  } else if (duration < 3600) {
    const minutes = Math.floor(duration / 60)
    const seconds = Math.floor(duration % 60)
    return `${minutes}分${seconds}秒`
  } else {
    const hours = Math.floor(duration / 3600)
    const minutes = Math.floor((duration % 3600) / 60)
    return `${hours}小时${minutes}分`
  }
}

// 启动自动刷新
const startAutoRefresh = () => {
  refreshTimer = window.setInterval(() => {
    if (hasRunningLogs.value) {
      store.refreshLogs(props.taskId, {
        status: filterStatus.value || undefined,
        skip: (pagination.value.page - 1) * pagination.value.pageSize,
        limit: pagination.value.pageSize
      })
    }
  }, 5000) // 每5秒刷新一次
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  loadLogs()
  loadStatistics()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
  store.clearLogs()
})
</script>

<style scoped>
.web-scraper-logs {
  padding: 20px;
}

.statistics {
  margin-bottom: 20px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 4px;
}

.filter-bar {
  margin-bottom: 20px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.log-details {
  padding: 20px;
  background: #fafafa;
}

.execution-details {
  margin-top: 20px;
}

.execution-details h4 {
  margin: 16px 0 8px 0;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.time-info,
.urls-info,
.documents-info,
.errors-info {
  margin-top: 12px;
}

.time-info ul,
.urls-info ul,
.errors-info ul {
  margin: 8px 0;
  padding-left: 20px;
}

.time-info li,
.urls-info li {
  margin: 4px 0;
  font-size: 13px;
  color: #606266;
}

.urls-info a {
  color: #409eff;
  text-decoration: none;
}

.urls-info a:hover {
  text-decoration: underline;
}

.documents-info {
  margin-top: 12px;
}

.errors-info .error-item {
  margin: 4px 0;
  color: #f56c6c;
  font-size: 13px;
}

.error-message {
  margin-top: 16px;
}

.error-message pre {
  margin: 8px 0 0 0;
  padding: 12px;
  background: #fef0f0;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.running-text {
  color: #e6a23c;
  display: flex;
  align-items: center;
  gap: 4px;
}

.success-text {
  color: #67c23a;
}

.error-text {
  color: #f56c6c;
}
</style>
