<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Delete, Edit, Document, Upload, FolderOpened, Share, View, Download, RefreshRight } from '@element-plus/icons-vue'
import { useKnowledgeStore } from '@/stores/knowledge'
import ShareDialog from '@/components/knowledge/ShareDialog.vue'
import type { KnowledgeBase, KnowledgeBaseCreate, Document as DocType } from '@/types'
import type { UploadProps, UploadRawFile, UploadRequestOptions } from 'element-plus'
import { knowledgeApi } from '@/api/knowledge'

import RAGQueryPanel from '@/components/knowledge/RAGQueryPanel.vue'
import { APP_CONSTANTS, parseApiError } from '@/utils/constants'

const knowledgeStore = useKnowledgeStore()

// 状态
const searchQuery = ref('')
const showCreateDialog = ref(false)
const showDetailDrawer = ref(false)
const showShareDialog = ref(false)
const createForm = ref<KnowledgeBaseCreate>({ name: '', description: '', category: '' })
const editingKb = ref<KnowledgeBase | null>(null)
const uploading = ref(false)

// 预览状态
const previewVisible = ref(false)
const previewContent = ref('')
const previewTitle = ref('')
const previewLoading = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | undefined

function fetchKnowledgeBasesByKeyword() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    knowledgeStore.kbPagination.page = 1
    knowledgeStore.fetchKnowledgeBases(searchQuery.value.trim())
  }, 300)
}

watch(searchQuery, fetchKnowledgeBasesByKeyword)

// 方法
async function handleCreate() {
  if (!createForm.value.name.trim()) {
    ElMessage.warning('请输入知识库名称')
    return
  }
  
  try {
    await knowledgeStore.createKnowledgeBase(createForm.value)
    ElMessage.success('创建成功')
    showCreateDialog.value = false
    createForm.value = { name: '', description: '', category: '' }
  } catch (error: any) {
    ElMessage.error(parseApiError(error, '创建失败'))
  }
}

async function handleEdit(kb: KnowledgeBase) {
  editingKb.value = kb
  createForm.value = { name: kb.name, description: kb.description || '', category: kb.category || '' }
  showCreateDialog.value = true
}

async function handleUpdate() {
  if (!editingKb.value || !createForm.value.name.trim()) return
  
  try {
    await knowledgeStore.updateKnowledgeBase(editingKb.value.id, createForm.value)
    ElMessage.success('更新成功')
    showCreateDialog.value = false
    editingKb.value = null
    createForm.value = { name: '', description: '', category: '' }
  } catch (error: any) {
    ElMessage.error(parseApiError(error, '更新失败'))
  }
}

async function handleDelete(kb: KnowledgeBase) {
  try {
    await ElMessageBox.confirm(
      `确定要删除知识库"${kb.name}"吗？此操作将同时删除所有文档，不可恢复。`,
      '删除确认',
      { type: 'warning' }
    )
    await knowledgeStore.deleteKnowledgeBase(kb.id)
    ElMessage.success('删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(parseApiError(error, '删除失败'))
    }
  }
}

function handleViewDetail(kb: KnowledgeBase) {
  knowledgeStore.fetchKnowledgeBase(kb.id)
  knowledgeStore.fetchDocuments(kb.id)
  showDetailDrawer.value = true
}

// 分页处理
function handleKbPageChange(page: number) {
  knowledgeStore.kbPagination.page = page
  knowledgeStore.fetchKnowledgeBases()
}

function handleDocPageChange(page: number) {
  knowledgeStore.docPagination.page = page
  if (knowledgeStore.currentKnowledgeBase) {
    knowledgeStore.fetchDocuments(knowledgeStore.currentKnowledgeBase.id)
  }
}

// 文件上传前验证
const beforeUpload: UploadProps['beforeUpload'] = (rawFile: UploadRawFile) => {
  // 检查文件大小
  if (rawFile.size > APP_CONSTANTS.UPLOAD.MAX_FILE_SIZE) {
    ElMessage.error(`文件大小不能超过 ${APP_CONSTANTS.UPLOAD.MAX_FILE_SIZE / 1024 / 1024}MB`)
    return false
  }
  
  // 检查文件类型
  const ext = '.' + rawFile.name.split('.').pop()?.toLowerCase()
  if (!APP_CONSTANTS.UPLOAD.ALLOWED_TYPES.includes(ext)) {
    ElMessage.error(`不支持的文件类型，仅支持 ${APP_CONSTANTS.UPLOAD.ALLOWED_TYPES.join(', ')}`)
    return false
  }
  
  return true
}

// 自定义上传
async function customUpload(options: UploadRequestOptions) {
  if (!knowledgeStore.currentKnowledgeBase) return
  
  try {
    const response = await knowledgeStore.uploadDocument(knowledgeStore.currentKnowledgeBase.id, options.file as File)
    // Notify element-plus upload component of success
    options.onSuccess(response)
  } catch (error: any) {
    options.onError(error)
    ElMessage.error(parseApiError(error, '上传失败'))
    throw error
  }
}

async function handleDeleteDocument(docId: number) {
  if (!knowledgeStore.currentKnowledgeBase) return
  
  try {
    await ElMessageBox.confirm('确定要删除此文档吗？', '删除确认', { type: 'warning' })
    await knowledgeStore.deleteDocument(docId, knowledgeStore.currentKnowledgeBase.id)
    ElMessage.success('删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(parseApiError(error, '删除失败'))
    }
  }
}

// 文档操作
async function handlePreview(doc: DocType) {
  previewTitle.value = doc.filename
  previewVisible.value = true
  previewLoading.value = true
  previewContent.value = ''
  
  try {
    const res = await knowledgeApi.getDocumentPreview(doc.id)
    previewContent.value = res.content || '暂无内容预览'
  } catch (error: any) {
    previewContent.value = '无法加载预览内容: ' + parseApiError(error)
  } finally {
    previewLoading.value = false
  }
}

async function handleDownload(doc: DocType) {
  try {
    await knowledgeStore.downloadDocument(doc.id, doc.filename)
    ElMessage.success('开始下载')
  } catch (error: any) {
    ElMessage.error(parseApiError(error, '下载失败'))
  }
}

async function handleRetry(doc: DocType) {
  try {
    await knowledgeStore.retryDocument(doc.id)
    ElMessage.success('已提交重试')
  } catch (error: any) {
    ElMessage.error(parseApiError(error, '重试失败'))
  }
}

function closeDialog() {
  showCreateDialog.value = false
  editingKb.value = null
  createForm.value = { name: '', description: '', category: '' }
}

function closeDrawer() {
  showDetailDrawer.value = false
  knowledgeStore.clearCurrentKnowledgeBase()
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getStatusType(status: string): string {
  const types: Record<string, string> = {
    pending: 'info',
    processing: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status] || 'info'
}

function getStatusText(status: string): string {
  const texts: Record<string, string> = {
    pending: '待处理',
    processing: '处理中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status] || status
}

onMounted(() => {
  knowledgeStore.fetchKnowledgeBases()
})
</script>

<template>
  <div class="knowledge-view">
    <!-- 顶部操作栏 -->
    <div class="header">
      <div class="search-box">
        <el-input
          v-model="searchQuery"
          placeholder="搜索知识库..."
          :prefix-icon="Search"
          clearable
        />
      </div>
      <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
        创建知识库
      </el-button>
    </div>

    <!-- 知识库列表 -->
    <div class="kb-container" v-loading="knowledgeStore.loading">
      <div class="kb-list">
        <template v-if="knowledgeStore.knowledgeBases.length > 0">
          <div 
            v-for="kb in knowledgeStore.knowledgeBases"
            :key="kb.id" 
            class="kb-card"
            @click="handleViewDetail(kb)"
          >
            <div class="kb-icon">
              <el-icon :size="32"><FolderOpened /></el-icon>
            </div>
            <div class="kb-info">
              <h3 class="kb-name">{{ kb.name }}</h3>
              <p class="kb-desc">{{ kb.description || '暂无描述' }}</p>
              <div class="kb-meta">
                <span class="doc-count">
                  <el-icon><Document /></el-icon>
                  {{ kb.document_count }} 个文档
                </span>
                <span class="category" v-if="kb.category">
                  <el-tag size="small">{{ kb.category }}</el-tag>
                </span>
              </div>
            </div>
            <div class="kb-actions" @click.stop>
              <el-button text :icon="Upload" type="primary" @click="handleViewDetail(kb)" title="上传文档">上传</el-button>
              <el-button text :icon="Edit" @click="handleEdit(kb)" title="编辑" />
              <el-button text :icon="Delete" type="danger" @click="handleDelete(kb)" title="删除" />
            </div>
          </div>
        </template>
        
        <!-- 空状态 -->
        <div v-else class="empty-state">
          <el-icon :size="64" color="#c0c4cc"><FolderOpened /></el-icon>
          <h3>暂无知识库</h3>
          <p>创建您的第一个知识库，开始管理文档</p>
          <el-button type="primary" :icon="Plus" @click="showCreateDialog = true">
            创建知识库
          </el-button>
        </div>
      </div>
      
      <!-- 知识库分页 -->
      <div class="pagination-container" v-if="knowledgeStore.total > 0">
        <el-pagination
          v-model:current-page="knowledgeStore.kbPagination.page"
          v-model:page-size="knowledgeStore.kbPagination.pageSize"
          :total="knowledgeStore.total"
          layout="total, prev, pager, next"
          @current-change="handleKbPageChange"
        />
      </div>
    </div>

    <!-- 创建/编辑对话框 -->
    <el-dialog
      :title="editingKb ? '编辑知识库' : '创建知识库'"
      v-model="showCreateDialog"
      width="500px"
      @close="closeDialog"
    >
      <el-form :model="createForm" label-width="80px">
        <el-form-item label="名称" required>
          <el-input v-model="createForm.name" placeholder="请输入知识库名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="createForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="请输入知识库描述" 
            maxlength="500"
          />
        </el-form-item>
        <el-form-item label="分类">
          <el-input v-model="createForm.category" placeholder="请输入分类标签" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="closeDialog">取消</el-button>
        <el-button type="primary" @click="editingKb ? handleUpdate() : handleCreate()">
          {{ editingKb ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 知识库详情抽屉 -->
    <el-drawer
      v-model="showDetailDrawer"
      :title="knowledgeStore.currentKnowledgeBase?.name || '知识库详情'"
      size="600px"
      @close="closeDrawer"
    >
      <template v-if="knowledgeStore.currentKnowledgeBase">
        <div class="drawer-content">
          <!-- 知识库信息 -->
          <div class="kb-detail-info">
            <p v-if="knowledgeStore.currentKnowledgeBase.description">
              {{ knowledgeStore.currentKnowledgeBase.description }}
            </p>
            <div class="meta-info">
              <span>创建时间: {{ formatDate(knowledgeStore.currentKnowledgeBase.created_at) }}</span>
              <span v-if="knowledgeStore.currentKnowledgeBase.category">
                分类: <el-tag size="small">{{ knowledgeStore.currentKnowledgeBase.category }}</el-tag>
              </span>
            </div>
            <div class="kb-actions-bar">
              <el-button :icon="Share" @click="showShareDialog = true">
                分享知识库
              </el-button>
            </div>
          </div>

          <!-- 文档上传 -->
          <div class="upload-section">
            <el-upload
              :auto-upload="true"
              :http-request="customUpload"
              :before-upload="beforeUpload"
              :show-file-list="true"
              accept=".pdf,.docx,.txt,.md"
              drag
              multiple
            >
              <el-icon :size="40"><Upload /></el-icon>
              <div class="upload-text">
                <p>拖拽文件到此处，或点击上传</p>
                <p class="upload-hint">支持 PDF、Word、TXT、Markdown 格式，最大 10MB</p>
              </div>
            </el-upload>
          </div>

          <!-- 文档列表 -->
          <div class="documents-section">
            <h4>文档列表 ({{ knowledgeStore.documentsTotal }})</h4>
            <div class="doc-list" v-loading="knowledgeStore.documentsLoading">
              <template v-if="knowledgeStore.documents.length > 0">
                <div v-for="doc in knowledgeStore.documents" :key="doc.id" class="doc-item">
                  <div class="doc-icon">
                    <el-icon><Document /></el-icon>
                  </div>
                  <div class="doc-info">
                    <span class="doc-name">{{ doc.filename }}</span>
                    <span class="doc-meta">
                      {{ formatFileSize(doc.file_size) }} · {{ doc.chunk_count }} 个分块
                    </span>
                  </div>
                  <el-tooltip v-if="doc.status === 'failed' && doc.error_message" :content="doc.error_message" placement="top">
                    <el-tag :type="getStatusType(doc.status)" size="small">
                      {{ getStatusText(doc.status) }}
                    </el-tag>
                  </el-tooltip>
                  <el-tag v-else :type="getStatusType(doc.status)" size="small">
                    {{ getStatusText(doc.status) }}
                  </el-tag>
                  <div class="doc-actions">
                    <!-- 预览 -->
                    <el-button 
                      link 
                      :icon="View" 
                      type="primary"
                      @click="handlePreview(doc)"
                      title="预览"
                    />
                    <!-- 下载 -->
                    <el-button 
                      link 
                      :icon="Download" 
                      type="primary"
                      @click="handleDownload(doc)"
                      title="下载"
                    />
                    <!-- 重试 (仅失败时) -->
                    <el-button 
                      v-if="doc.status === 'failed'"
                      link 
                      :icon="RefreshRight" 
                      type="warning"
                      @click="handleRetry(doc)"
                      title="重试"
                    />
                    <!-- 删除 -->
                    <el-button 
                      link 
                      :icon="Delete" 
                      type="danger" 
                      @click="handleDeleteDocument(doc.id)"
                      title="删除"
                    />
                  </div>
                </div>
              </template>
              <div v-else class="no-docs">
                <p>暂无文档，请上传文档</p>
              </div>
            </div>
            
            <!-- 文档分页 -->
            <div class="pagination-container" v-if="knowledgeStore.documentsTotal > 0">
              <el-pagination
                v-model:current-page="knowledgeStore.docPagination.page"
                v-model:page-size="knowledgeStore.docPagination.pageSize"
                :total="knowledgeStore.documentsTotal"
                layout="prev, pager, next"
                small
                @current-change="handleDocPageChange"
              />
            </div>
          </div>

          <!-- RAG 测试区域 -->
          <div class="rag-test-section">
            <h4>知识库问答测试</h4>
            <RAGQueryPanel :knowledge-base-id="knowledgeStore.currentKnowledgeBase.id" :knowledge-bases="[knowledgeStore.currentKnowledgeBase]" />
          </div>
        </div>
      </template>
    </el-drawer>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewVisible"
      :title="previewTitle"
      width="600px"
      append-to-body
    >
      <div class="preview-content" v-loading="previewLoading">
        <pre>{{ previewContent }}</pre>
      </div>
    </el-dialog>

    <!-- 分享对话框 -->
    <ShareDialog
      v-if="knowledgeStore.currentKnowledgeBase"
      v-model="showShareDialog"
      :knowledge-base-id="knowledgeStore.currentKnowledgeBase.id"
    />
  </div>
</template>

<style scoped lang="scss">
.knowledge-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;

  .search-box {
    width: 300px;
  }
}

.kb-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.kb-list {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  align-content: start;
  padding-bottom: 20px;
}

.kb-card {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: var(--el-color-primary);
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  }

  .kb-icon {
    flex-shrink: 0;
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--el-color-primary-light-9);
    border-radius: 8px;
    color: var(--el-color-primary);
  }

  .kb-info {
    flex: 1;
    min-width: 0;

    .kb-name {
      margin: 0 0 8px;
      font-size: 16px;
      font-weight: 500;
    }

    .kb-desc {
      margin: 0 0 12px;
      font-size: 13px;
      color: var(--el-text-color-secondary);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .kb-meta {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 12px;
      color: var(--el-text-color-secondary);

      .doc-count {
        display: flex;
        align-items: center;
        gap: 4px;
      }
    }
  }

  .kb-actions {
    display: flex;
    gap: 4px;
  }
}

.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  color: var(--el-text-color-secondary);

  h3 {
    margin: 16px 0 8px;
    color: var(--el-text-color-primary);
  }

  p {
    margin-bottom: 20px;
  }
}

.pagination-container {
  display: flex;
  justify-content: center;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-light);
}

.drawer-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.kb-detail-info {
  p {
    margin: 0 0 12px;
    color: var(--el-text-color-secondary);
  }

  .meta-info {
    display: flex;
    gap: 16px;
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }
  
  .kb-actions-bar {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--el-border-color-light);
  }
}

.upload-section {
  :deep(.el-upload-dragger) {
    padding: 20px;
  }

  .upload-text {
    p {
      margin: 8px 0 0;
      font-size: 14px;
    }

    .upload-hint {
      font-size: 12px;
      color: var(--el-text-color-secondary);
    }
  }
}

.documents-section {
  h4 {
    margin: 0 0 12px;
    font-size: 14px;
  }

  .doc-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .doc-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: var(--el-fill-color-light);
    border-radius: 6px;

    .doc-icon {
      color: var(--el-text-color-secondary);
    }

    .doc-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 4px;

      .doc-name {
        font-size: 14px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .doc-meta {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
    
    .doc-actions {
      display: flex;
      align-items: center;
      gap: 4px;
    }
  }

  .no-docs {
    padding: 40px;
    text-align: center;
    color: var(--el-text-color-secondary);
  }
}

.rag-test-section {
  h4 {
    margin: 0 0 12px;
    font-size: 14px;
  }
}

.preview-content {
  max-height: 400px;
  overflow-y: auto;
  
  pre {
    white-space: pre-wrap;
    word-wrap: break-word;
    word-break: break-all;
    font-family: inherit;
    font-size: 14px;
    line-height: 1.5;
    margin: 0;
  }
}
</style>
