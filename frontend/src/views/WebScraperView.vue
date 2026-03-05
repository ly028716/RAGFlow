<template>
  <div class="web-scraper-view">
    <div class="header">
      <h2>网页采集任务</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon>
        创建任务
      </el-button>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部" clearable @change="handleFilter">
            <el-option label="运行中" value="active" />
            <el-option label="已暂停" value="paused" />
            <el-option label="已停止" value="stopped" />
          </el-select>
        </el-form-item>
        <el-form-item label="调度类型">
          <el-select v-model="filterForm.schedule_type" placeholder="全部" clearable @change="handleFilter">
            <el-option label="一次性" value="once" />
            <el-option label="定时" value="cron" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="handleFilter">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </div>

    <!-- 任务列表 -->
    <el-table
      v-loading="store.loading"
      :data="store.tasks"
      stripe
      style="width: 100%"
    >
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="任务名称" min-width="150" />
      <el-table-column prop="url" label="目标URL" min-width="200" show-overflow-tooltip />
      <el-table-column label="调度类型" width="100">
        <template #default="{ row }">
          <el-tag :type="row.schedule_type === 'once' ? 'info' : 'success'" size="small">
            {{ row.schedule_type === 'once' ? '一次性' : '定时' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag
            :type="getStatusType(row.status)"
            size="small"
          >
            {{ getStatusText(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="last_run_at" label="最后执行" width="160">
        <template #default="{ row }">
          {{ row.last_run_at ? formatDate(row.last_run_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="next_run_at" label="下次执行" width="160">
        <template #default="{ row }">
          {{ row.next_run_at ? formatDate(row.next_run_at) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'active'"
            type="success"
            size="small"
            @click="handleStart(row)"
          >
            启动
          </el-button>
          <el-button
            v-if="row.status === 'active'"
            type="warning"
            size="small"
            @click="handleStop(row)"
          >
            停止
          </el-button>
          <el-button size="small" @click="handleViewLogs(row)">
            日志
          </el-button>
          <el-button size="small" @click="handleEdit(row)">
            编辑
          </el-button>
          <el-button
            type="danger"
            size="small"
            @click="handleDelete(row)"
          >
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination">
      <el-pagination
        v-model:current-page="pagination.page"
        v-model:page-size="pagination.pageSize"
        :total="store.totalTasks"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="handleSizeChange"
        @current-change="handlePageChange"
      />
    </div>

    <!-- 任务表单对话框 -->
    <WebScraperTaskForm
      v-model:visible="formVisible"
      :task="currentTask"
      @success="handleFormSuccess"
    />

    <!-- 日志对话框 -->
    <el-dialog
      v-model="logsVisible"
      title="执行日志"
      width="80%"
      :close-on-click-modal="false"
    >
      <WebScraperLogs v-if="logsVisible" :task-id="currentTaskId" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useWebScraperStore } from '@/stores/webScraper'
import WebScraperTaskForm from '@/components/WebScraperTaskForm.vue'
import WebScraperLogs from '@/components/WebScraperLogs.vue'
import type { Task, TaskStatus } from '@/types/webScraper'

const store = useWebScraperStore()

// 筛选表单
const filterForm = ref({
  status: '',
  schedule_type: ''
})

// 分页
const pagination = ref({
  page: 1,
  pageSize: 20
})

// 表单对话框
const formVisible = ref(false)
const currentTask = ref<Task | null>(null)

// 日志对话框
const logsVisible = ref(false)
const currentTaskId = ref<number>(0)

// 自动刷新定时器
let refreshTimer: ReturnType<typeof setInterval> | null = null

// 加载任务列表
const loadTasks = async () => {
  const params = {
    status: filterForm.value.status || undefined,
    schedule_type: filterForm.value.schedule_type || undefined,
    skip: (pagination.value.page - 1) * pagination.value.pageSize,
    limit: pagination.value.pageSize
  }
  await store.loadTasks(params)
}

// 筛选
const handleFilter = () => {
  pagination.value.page = 1
  loadTasks()
}

// 重置
const handleReset = () => {
  filterForm.value = {
    status: '',
    schedule_type: ''
  }
  pagination.value.page = 1
  loadTasks()
}

// 分页变化
const handlePageChange = () => {
  loadTasks()
}

const handleSizeChange = () => {
  pagination.value.page = 1
  loadTasks()
}

// 创建任务
const handleCreate = () => {
  currentTask.value = null
  formVisible.value = true
}

// 编辑任务
const handleEdit = (task: Task) => {
  currentTask.value = task
  formVisible.value = true
}

// 启动任务
const handleStart = async (task: Task) => {
  try {
    await store.startTask(task.id)
    await loadTasks()
  } catch (error) {
    console.error('启动任务失败:', error)
  }
}

// 停止任务
const handleStop = async (task: Task) => {
  try {
    await ElMessageBox.confirm('确定要停止该任务吗？', '提示', {
      type: 'warning'
    })
    await store.stopTask(task.id)
    await loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('停止任务失败:', error)
    }
  }
}

// 删除任务
const handleDelete = async (task: Task) => {
  try {
    await ElMessageBox.confirm(
      '删除任务将同时删除所有执行日志，此操作不可逆，确定要删除吗？',
      '警告',
      {
        type: 'warning',
        confirmButtonText: '确定删除',
        cancelButtonText: '取消'
      }
    )
    await store.deleteTask(task.id)
    await loadTasks()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除任务失败:', error)
    }
  }
}

// 查看日志
const handleViewLogs = (task: Task) => {
  currentTaskId.value = task.id
  logsVisible.value = true
}

// 表单提交成功
const handleFormSuccess = () => {
  formVisible.value = false
  loadTasks()
}

// 获取状态类型
const getStatusType = (status: TaskStatus) => {
  const typeMap = {
    active: 'success',
    paused: 'warning',
    stopped: 'info'
  }
  return typeMap[status] || 'info'
}

// 获取状态文本
const getStatusText = (status: TaskStatus) => {
  const textMap = {
    active: '运行中',
    paused: '已暂停',
    stopped: '已停止'
  }
  return textMap[status] || status
}

// 格式化日期
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 启动自动刷新
const startAutoRefresh = () => {
  refreshTimer = window.setInterval(() => {
    if (store.activeTasks.length > 0) {
      store.refreshTasks({
        status: filterForm.value.status || undefined,
        schedule_type: filterForm.value.schedule_type || undefined,
        skip: (pagination.value.page - 1) * pagination.value.pageSize,
        limit: pagination.value.pageSize
      })
    }
  }, 10000) // 每10秒刷新一次
}

// 停止自动刷新
const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

onMounted(() => {
  loadTasks()
  startAutoRefresh()
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.web-scraper-view {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.filter-bar {
  margin-bottom: 20px;
  padding: 16px;
  background: #f5f7fa;
  border-radius: 4px;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
