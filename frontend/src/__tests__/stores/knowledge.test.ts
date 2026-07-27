/**
 * Knowledge Store 测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useKnowledgeStore } from '@/stores/knowledge'
import { knowledgeApi } from '@/api/knowledge'
import type { KnowledgeBase, Document, DocumentUpload, PaginatedList } from '@/types'

// Mock API
vi.mock('@/api/knowledge', () => ({
  knowledgeApi: {
    getList: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    getDocuments: vi.fn(),
    getDocumentStatus: vi.fn(),
    getDocumentPreview: vi.fn(),
    downloadDocument: vi.fn(),
    retryDocument: vi.fn(),
    uploadDocument: vi.fn(),
    uploadDocuments: vi.fn(),
    deleteDocument: vi.fn()
  }
}))

// 创建完整的 mock 数据
const createMockKnowledgeBase = (overrides: Partial<KnowledgeBase> = {}): KnowledgeBase => ({
  id: 1,
  name: '测试知识库',
  description: '描述',
  document_count: 0,
  created_at: '2025-01-01T00:00:00Z',
  updated_at: '2025-01-01T00:00:00Z',
  ...overrides
})

const createMockDocument = (overrides: Partial<Document> = {}): Document => ({
  id: 1,
  knowledge_base_id: 1,
  filename: 'test.pdf',
  file_size: 1024,
  file_type: 'pdf',
  status: 'completed',
  chunk_count: 10,
  created_at: '2025-01-01T00:00:00Z',
  ...overrides
})

describe('Knowledge Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('初始状态', () => {
    it('应该有正确的初始状态', () => {
      const store = useKnowledgeStore()
      
      expect(store.knowledgeBases).toEqual([])
      expect(store.currentKnowledgeBase).toBeNull()
      expect(store.documents).toEqual([])
      expect(store.total).toBe(0)
      expect(store.documentsTotal).toBe(0)
      expect(store.loading).toBe(false)
      expect(store.documentsLoading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.documentsError).toBeNull()
    })

    it('hasKnowledgeBases 应该返回 false 当列表为空', () => {
      const store = useKnowledgeStore()
      expect(store.hasKnowledgeBases).toBe(false)
    })

    it('hasError 应该返回 false 当没有错误', () => {
      const store = useKnowledgeStore()
      expect(store.hasError).toBe(false)
    })
  })

  describe('fetchKnowledgeBases', () => {
    it('应该成功获取知识库列表', async () => {
      const mockData: PaginatedList<KnowledgeBase> = {
        items: [createMockKnowledgeBase({ id: 1, name: '测试知识库', document_count: 5 })],
        total: 1
      }
      vi.mocked(knowledgeApi.getList).mockResolvedValue(mockData)

      const store = useKnowledgeStore()
      await store.fetchKnowledgeBases()

      expect(store.knowledgeBases).toEqual(mockData.items)
      expect(store.total).toBe(1)
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
    })

    it('应该处理获取失败的情况', async () => {
      const error = { response: { data: { detail: '获取失败' } } }
      vi.mocked(knowledgeApi.getList).mockRejectedValue(error)

      const store = useKnowledgeStore()
      
      await expect(store.fetchKnowledgeBases()).rejects.toThrow()
      expect(store.error).toBe('获取失败')
      expect(store.loading).toBe(false)
    })

    it('应该在加载时设置 loading 状态', async () => {
      vi.mocked(knowledgeApi.getList).mockImplementation(() => 
        new Promise(resolve => setTimeout(() => resolve({ items: [], total: 0 }), 100))
      )

      const store = useKnowledgeStore()
      const promise = store.fetchKnowledgeBases()
      
      expect(store.loading).toBe(true)
      await promise
      expect(store.loading).toBe(false)
    })
  })

  describe('createKnowledgeBase', () => {
    it('应该成功创建知识库', async () => {
      const newKb = createMockKnowledgeBase({ id: 1, name: '新知识库' })
      vi.mocked(knowledgeApi.create).mockResolvedValue(newKb)

      const store = useKnowledgeStore()
      const result = await store.createKnowledgeBase({ name: '新知识库', description: '描述' })

      expect(result).toEqual(newKb)
      expect(store.knowledgeBases[0]).toEqual(newKb)
      expect(store.total).toBe(1)
    })
  })

  describe('updateKnowledgeBase', () => {
    it('应该成功更新知识库', async () => {
      const store = useKnowledgeStore()
      store.knowledgeBases = [createMockKnowledgeBase({ id: 1, name: '旧名称' })]
      
      const updatedKb = createMockKnowledgeBase({ id: 1, name: '新名称', description: '新描述' })
      vi.mocked(knowledgeApi.update).mockResolvedValue(updatedKb)

      const result = await store.updateKnowledgeBase(1, { name: '新名称', description: '新描述' })

      expect(result).toEqual(updatedKb)
      expect(store.knowledgeBases[0].name).toBe('新名称')
    })

    it('应该更新当前选中的知识库', async () => {
      const store = useKnowledgeStore()
      store.knowledgeBases = [createMockKnowledgeBase({ id: 1, name: '旧名称' })]
      store.currentKnowledgeBase = createMockKnowledgeBase({ id: 1, name: '旧名称' })
      
      const updatedKb = createMockKnowledgeBase({ id: 1, name: '新名称', description: '新描述' })
      vi.mocked(knowledgeApi.update).mockResolvedValue(updatedKb)

      await store.updateKnowledgeBase(1, { name: '新名称' })

      expect(store.currentKnowledgeBase?.name).toBe('新名称')
    })
  })

  describe('deleteKnowledgeBase', () => {
    it('应该成功删除知识库', async () => {
      const store = useKnowledgeStore()
      store.knowledgeBases = [
        createMockKnowledgeBase({ id: 1, name: 'KB1' }),
        createMockKnowledgeBase({ id: 2, name: 'KB2' })
      ]
      store.total = 2
      
      vi.mocked(knowledgeApi.delete).mockResolvedValue({ message: '删除成功' })

      await store.deleteKnowledgeBase(1)

      expect(store.knowledgeBases.length).toBe(1)
      expect(store.knowledgeBases[0].id).toBe(2)
      expect(store.total).toBe(1)
    })

    it('应该清除当前选中的知识库如果被删除', async () => {
      const store = useKnowledgeStore()
      store.knowledgeBases = [createMockKnowledgeBase({ id: 1, name: 'KB1' })]
      store.currentKnowledgeBase = createMockKnowledgeBase({ id: 1, name: 'KB1' })
      
      vi.mocked(knowledgeApi.delete).mockResolvedValue({ message: '删除成功' })

      await store.deleteKnowledgeBase(1)

      expect(store.currentKnowledgeBase).toBeNull()
    })
  })

  describe('fetchDocuments', () => {
    it('应该成功获取文档列表', async () => {
      const mockData: PaginatedList<Document> = {
        items: [createMockDocument({ id: 1, filename: 'doc.pdf' })],
        total: 1
      }
      vi.mocked(knowledgeApi.getDocuments).mockResolvedValue(mockData)

      const store = useKnowledgeStore()
      await store.fetchDocuments(1)

      expect(store.documents).toEqual(mockData.items)
      expect(store.documentsTotal).toBe(1)
      expect(store.documentsLoading).toBe(false)
    })

    it('应该处理获取文档失败', async () => {
      const error = { response: { data: { detail: '获取文档失败' } } }
      vi.mocked(knowledgeApi.getDocuments).mockRejectedValue(error)

      const store = useKnowledgeStore()
      
      await expect(store.fetchDocuments(1)).rejects.toThrow()
      expect(store.documentsError).toBe('获取文档失败')
    })

    it('切换知识库时应忽略旧请求返回，展示最后一次请求结果', async () => {
      const store = useKnowledgeStore()

      let resolveKb2!: (val: PaginatedList<Document>) => void
      const kb2Promise = new Promise<PaginatedList<Document>>(resolve => {
        resolveKb2 = resolve
      })

      vi.mocked(knowledgeApi.getDocuments).mockImplementation((kbId: number) => {
        if (kbId === 2) return kb2Promise
        return Promise.resolve({
          items: [createMockDocument({ id: 101, knowledge_base_id: 1, filename: 'doc1.docx' })],
          total: 1
        })
      })

      const p2 = store.fetchDocuments(2)
      const p1 = store.fetchDocuments(1)

      resolveKb2({
        items: [createMockDocument({ id: 202, knowledge_base_id: 2, filename: 'doc2.txt' })],
        total: 1
      })

      await Promise.all([p2.catch(() => null), p1])

      expect(store.documents.length).toBe(1)
      expect(store.documents[0].knowledge_base_id).toBe(1)
      expect(store.documents[0].filename).toBe('doc1.docx')
    })
  })

  describe('uploadDocument', () => {
    it('应该成功上传文档并更新计数', async () => {
      const store = useKnowledgeStore()
      store.knowledgeBases = [createMockKnowledgeBase({ id: 1, name: 'KB1', document_count: 0 })]
      store.currentKnowledgeBase = createMockKnowledgeBase({ id: 1, name: 'KB1', document_count: 0 })
      
      const mockUpload: DocumentUpload = {
        id: 1,
        filename: 'test.pdf',
        file_size: 1024,
        status: 'completed',
        created_at: '2025-01-01T00:00:00Z'
      }
      const mockDoc = createMockDocument({ id: 1, filename: 'test.pdf' })
      vi.mocked(knowledgeApi.uploadDocument).mockResolvedValue(mockUpload)
      vi.mocked(knowledgeApi.getDocuments).mockResolvedValue({ items: [mockDoc], total: 1 })
      vi.mocked(knowledgeApi.getDocumentStatus).mockResolvedValue({
        document_id: 1,
        status: 'completed',
        progress: 100,
        chunk_count: 10,
        error_message: undefined
      })

      const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
      await store.uploadDocument(1, file)

      expect(store.knowledgeBases[0].document_count).toBe(1)
      expect(store.currentKnowledgeBase?.document_count).toBe(1)
    })
  })

  describe('deleteDocument', () => {
    it('应该成功删除文档并更新计数', async () => {
      const store = useKnowledgeStore()
      store.knowledgeBases = [createMockKnowledgeBase({ id: 1, name: 'KB1', document_count: 2 })]
      store.currentKnowledgeBase = createMockKnowledgeBase({ id: 1, name: 'KB1', document_count: 2 })
      store.documents = [
        createMockDocument({ id: 1, filename: 'doc1.pdf' }),
        createMockDocument({ id: 2, filename: 'doc2.pdf' })
      ]
      store.documentsTotal = 2
      
      vi.mocked(knowledgeApi.deleteDocument).mockResolvedValue({ message: '删除成功' })

      await store.deleteDocument(1, 1)

      expect(store.documents.length).toBe(1)
      expect(store.documentsTotal).toBe(1)
      expect(store.knowledgeBases[0].document_count).toBe(1)
      expect(store.currentKnowledgeBase?.document_count).toBe(1)
    })
  })

  describe('clearCurrentKnowledgeBase', () => {
    it('应该清除当前知识库和文档', () => {
      const store = useKnowledgeStore()
      store.currentKnowledgeBase = createMockKnowledgeBase({ id: 1, name: 'KB1' })
      store.documents = [createMockDocument({ id: 1, filename: 'doc.pdf' })]
      store.documentsTotal = 1
      store.documentsError = '错误'

      store.clearCurrentKnowledgeBase()

      expect(store.currentKnowledgeBase).toBeNull()
      expect(store.documents).toEqual([])
      expect(store.documentsTotal).toBe(0)
      expect(store.documentsError).toBeNull()
    })
  })

  describe('clearError', () => {
    it('应该清除所有错误', () => {
      const store = useKnowledgeStore()
      store.error = '知识库错误'
      store.documentsError = '文档错误'

      store.clearError()

      expect(store.error).toBeNull()
      expect(store.documentsError).toBeNull()
    })
  })
})
