import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { knowledgeApi } from '@/api/knowledge'
import type { KnowledgeBase, Document, KnowledgeBaseCreate, KnowledgeBaseUpdate } from '@/types'

export const useKnowledgeStore = defineStore('knowledge', () => {
  // State
  const knowledgeBases = ref<KnowledgeBase[]>([])
  const currentKnowledgeBase = ref<KnowledgeBase | null>(null)
  const documents = ref<Document[]>([])
  const total = ref(0)
  const documentsTotal = ref(0)
  const loading = ref(false)
  const documentsLoading = ref(false)
  const error = ref<string | null>(null)
  const documentsError = ref<string | null>(null)

  // Pagination State
  const kbPagination = ref({ page: 1, pageSize: 20 })
  const docPagination = ref({ page: 1, pageSize: 20 })
  const documentsKbId = ref<number | null>(null)
  const documentsFetchSeq = ref(0)

  // Getters
  const hasKnowledgeBases = computed(() => knowledgeBases.value.length > 0)
  const hasError = computed(() => error.value !== null)

  async function waitForDocumentTerminalStatus(documentId: number, timeoutMs = 60_000, intervalMs = 1_500) {
    const start = Date.now()
    while (Date.now() - start < timeoutMs) {
      const status = await knowledgeApi.getDocumentStatus(documentId)
      const index = documents.value.findIndex(d => d.id === documentId)
      if (index !== -1) {
        documents.value[index] = {
          ...documents.value[index],
          status: status.status as Document['status'],
          chunk_count: status.chunk_count,
          error_message: status.error_message
        }
      }
      if (status.status === 'completed' || status.status === 'failed') {
        return status
      }
      await new Promise(resolve => setTimeout(resolve, intervalMs))
    }
    return null
  }

  // Actions
  async function fetchKnowledgeBases(keyword = '') {
    loading.value = true
    error.value = null
    try {
      const skip = (kbPagination.value.page - 1) * kbPagination.value.pageSize
      const res = await knowledgeApi.getList(skip, kbPagination.value.pageSize, keyword)
      knowledgeBases.value = res.items
      total.value = res.total
    } catch (e: any) {
      error.value = e.response?.data?.detail || '加载知识库列表失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchKnowledgeBase(id: number) {
    loading.value = true
    error.value = null
    try {
      currentKnowledgeBase.value = await knowledgeApi.getById(id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '加载知识库详情失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createKnowledgeBase(data: KnowledgeBaseCreate) {
    const kb = await knowledgeApi.create(data)
    // If on first page, prepend
    if (kbPagination.value.page === 1) {
      knowledgeBases.value.unshift(kb)
      if (knowledgeBases.value.length > kbPagination.value.pageSize) {
        knowledgeBases.value.pop()
      }
    }
    total.value++
    return kb
  }

  async function updateKnowledgeBase(id: number, data: KnowledgeBaseUpdate) {
    const kb = await knowledgeApi.update(id, data)
    const index = knowledgeBases.value.findIndex(k => k.id === id)
    if (index !== -1) {
      knowledgeBases.value[index] = kb
    }
    if (currentKnowledgeBase.value?.id === id) {
      currentKnowledgeBase.value = kb
    }
    return kb
  }

  async function deleteKnowledgeBase(id: number) {
    await knowledgeApi.delete(id)
    knowledgeBases.value = knowledgeBases.value.filter(k => k.id !== id)
    total.value--
    if (currentKnowledgeBase.value?.id === id) {
      currentKnowledgeBase.value = null
    }
    // Refresh if list becomes empty but total > 0 (handle pagination hole)
    if (knowledgeBases.value.length === 0 && total.value > 0) {
      if (kbPagination.value.page > 1) {
        kbPagination.value.page--
      }
      fetchKnowledgeBases()
    }
  }

  async function fetchDocuments(kbId: number) {
    if (documentsKbId.value !== kbId) {
      documentsKbId.value = kbId
      documents.value = []
      documentsTotal.value = 0
      documentsError.value = null
      docPagination.value = { ...docPagination.value, page: 1 }
    }

    const seq = ++documentsFetchSeq.value
    documentsLoading.value = true
    documentsError.value = null
    try {
      const skip = (docPagination.value.page - 1) * docPagination.value.pageSize
      const res = await knowledgeApi.getDocuments(kbId, skip, docPagination.value.pageSize)
      if (seq !== documentsFetchSeq.value || documentsKbId.value !== kbId) return
      documents.value = res.items
      documentsTotal.value = res.total
    } catch (e: any) {
      if (seq !== documentsFetchSeq.value || documentsKbId.value !== kbId) return
      documentsError.value = e.response?.data?.detail || '加载文档列表失败'
      throw e
    } finally {
      if (seq !== documentsFetchSeq.value || documentsKbId.value !== kbId) return
      documentsLoading.value = false
    }
  }

  async function uploadDocument(kbId: number, file: File) {
    const doc = await knowledgeApi.uploadDocument(kbId, file)
    // Refresh documents list
    await fetchDocuments(kbId)
    await waitForDocumentTerminalStatus(doc.id)
    // Update KB document count
    const kb = knowledgeBases.value.find(k => k.id === kbId)
    if (kb) {
      kb.document_count++
    }
    if (currentKnowledgeBase.value?.id === kbId) {
      currentKnowledgeBase.value.document_count++
    }
    return doc
  }

  async function uploadDocuments(kbId: number, files: File[]) {
    const result = await knowledgeApi.uploadDocuments(kbId, files)
    // Refresh documents list
    await fetchDocuments(kbId)
    // Update KB document count
    const successCount = result.documents.length
    const kb = knowledgeBases.value.find(k => k.id === kbId)
    if (kb) {
      kb.document_count += successCount
    }
    if (currentKnowledgeBase.value?.id === kbId) {
      currentKnowledgeBase.value.document_count += successCount
    }
    return result
  }

  async function deleteDocument(docId: number, kbId: number) {
    await knowledgeApi.deleteDocument(docId)
    documents.value = documents.value.filter(d => d.id !== docId)
    documentsTotal.value--
    // Update KB document count
    const kb = knowledgeBases.value.find(k => k.id === kbId)
    if (kb) {
      kb.document_count--
    }
    if (currentKnowledgeBase.value?.id === kbId) {
      currentKnowledgeBase.value.document_count--
    }
    // Refresh if empty to fill page
    if (documents.value.length === 0 && documentsTotal.value > 0) {
      if (docPagination.value.page > 1) {
        docPagination.value.page--
      }
      fetchDocuments(kbId)
    }
  }

  async function downloadDocument(docId: number, filename: string) {
    const blob = await knowledgeApi.downloadDocument(docId)
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
  }

  async function retryDocument(docId: number) {
    const doc = await knowledgeApi.retryDocument(docId)
    const index = documents.value.findIndex(d => d.id === docId)
    if (index !== -1) {
      documents.value[index] = doc
    }
    await waitForDocumentTerminalStatus(docId)
    return doc
  }

  function clearCurrentKnowledgeBase() {
    currentKnowledgeBase.value = null
    documents.value = []
    documentsTotal.value = 0
    documentsError.value = null
    docPagination.value = { page: 1, pageSize: 20 }
    documentsKbId.value = null
    documentsFetchSeq.value = 0
  }

  function clearError() {
    error.value = null
    documentsError.value = null
  }

  return {
    knowledgeBases,
    currentKnowledgeBase,
    documents,
    total,
    documentsTotal,
    loading,
    documentsLoading,
    error,
    documentsError,
    kbPagination,
    docPagination,
    hasKnowledgeBases,
    hasError,
    fetchKnowledgeBases,
    fetchKnowledgeBase,
    createKnowledgeBase,
    updateKnowledgeBase,
    deleteKnowledgeBase,
    fetchDocuments,
    uploadDocument,
    uploadDocuments,
    deleteDocument,
    downloadDocument,
    retryDocument,
    clearCurrentKnowledgeBase,
    clearError
  }
})
