import request from './index'
import type {
  KnowledgeBase,
  KnowledgeBaseCreate,
  KnowledgeBaseUpdate,
  Document,
  DocumentUpload,
  RAGQueryRequest,
  RAGQueryResponse,
  PaginatedList
} from '@/types'

export const knowledgeApi = {
  // 知识库管理
  getList(skip = 0, limit = 20, keyword = ''): Promise<PaginatedList<KnowledgeBase>> {
    return request.get('/knowledge-bases', { params: { skip, limit, keyword: keyword || undefined } })
  },

  getById(id: number): Promise<KnowledgeBase> {
    return request.get(`/knowledge-bases/${id}`)
  },

  create(data: KnowledgeBaseCreate): Promise<KnowledgeBase> {
    return request.post('/knowledge-bases', data)
  },

  update(id: number, data: KnowledgeBaseUpdate): Promise<KnowledgeBase> {
    return request.put(`/knowledge-bases/${id}`, data)
  },

  delete(id: number): Promise<{ message: string }> {
    return request.delete(`/knowledge-bases/${id}`)
  },

  // 文档管理
  getDocuments(kbId: number, skip = 0, limit = 20): Promise<PaginatedList<Document>> {
    return request.get('/documents', { params: { knowledge_base_id: kbId, skip, limit } })
  },

  uploadDocument(kbId: number, file: File): Promise<DocumentUpload> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/documents/upload', formData, {
      params: { knowledge_base_id: kbId }
    })
  },

  uploadDocuments(kbId: number, files: File[]): Promise<{ documents: DocumentUpload[], errors: any[] }> {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return request.post('/documents/upload-batch', formData, {
      params: { knowledge_base_id: kbId }
    })
  },

  getDocumentStatus(docId: number): Promise<{ document_id: number, status: string, progress: number, chunk_count: number, error_message?: string }> {
    return request.get(`/documents/${docId}/status`)
  },

  getDocumentPreview(docId: number, maxChars = 1000): Promise<{ document_id: number, filename: string, content: string, total_length: number }> {
    return request.get(`/documents/${docId}/preview`, { params: { max_chars: maxChars } })
  },

  downloadDocument(docId: number): Promise<Blob> {
    return request.get(`/documents/${docId}/download`, { responseType: 'blob' })
  },

  retryDocument(docId: number): Promise<Document> {
    return request.post(`/documents/${docId}/retry`)
  },

  deleteDocument(docId: number): Promise<{ message: string }> {
    return request.delete(`/documents/${docId}`)
  },

  // RAG查询
  query(data: RAGQueryRequest): Promise<RAGQueryResponse> {
    return request.post('/rag/query', data)
  }
}
