import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AgentView from '@/views/agent/AgentView.vue'
import { useAgentStore } from '@/stores/agent'
import { useKnowledgeStore } from '@/stores/knowledge'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

const elementStubs = {
  'el-button': true,
  'el-input': true,
  'el-input-number': true,
  'el-select': true,
  'el-option': true,
  'el-tag': { template: '<span><slot /></span>' },
  'el-icon': true,
  'el-alert': true,
  'el-timeline': { template: '<div><slot /></div>' },
  'el-timeline-item': { template: '<div><slot /></div>' },
  'el-card': { template: '<div><slot /></div>' },
  'el-table': { template: '<div><slot /></div>' },
  'el-table-column': true,
  'el-empty': true
}

describe('AgentView constrained RAG workflow debug', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders structured workflow evidence and completion metrics', async () => {
    const store = useAgentStore()
    vi.spyOn(store, 'fetchExecutions').mockResolvedValue(undefined)
    const knowledgeStore = useKnowledgeStore()
    vi.spyOn(knowledgeStore, 'fetchKnowledgeBases').mockResolvedValue(undefined)
    store.currentExecution = {
      execution_id: 7,
      task: 'What architecture does the project use?',
      status: 'completed',
      created_at: '2026-07-26T10:00:00Z',
      result: 'The project uses a layered architecture [citation:11:2].',
      steps: [
        {
          step_number: 1,
          phase: 'query_rewrite',
          thought: 'Constrained RAG phase: query_rewrite',
          action: 'query_rewriter',
          action_input: { question: 'What architecture does the project use?' },
          observation: '',
          data: {
            knowledge_base_scope: [3],
            rewritten_query: 'project layered architecture'
          }
        },
        {
          step_number: 2,
          phase: 'retrieval',
          thought: 'Constrained RAG phase: retrieval',
          action: 'knowledge_base_search',
          action_input: { top_k: 5 },
          observation: '',
          data: {
            retrieval_parameters: { top_k: 5, similarity_threshold: 0.7 },
            raw_chunks: [{ document_name: 'architecture.md', content: 'API, service, and repository layers.', similarity_score: 0.92 }],
            retrieval_time_ms: 12.5
          }
        },
        {
          step_number: 3,
          phase: 'context_selection',
          thought: 'Constrained RAG phase: context_selection',
          action: 'context_selector',
          action_input: {},
          observation: '',
          data: { final_context: '[citation:11:2] API, service, and repository layers.' }
        },
        {
          step_number: 4,
          phase: 'answer_and_citation_validation',
          thought: 'Constrained RAG phase: answer_and_citation_validation',
          action: 'citation_validator',
          action_input: {},
          observation: '',
          data: {
            citation_validation: { valid: true, missing_citation_ids: [] },
            tokens_used: 28,
            generation_time_ms: 20,
            total_time_ms: 50
          }
        }
      ]
    }

    const wrapper = mount(AgentView, { global: { stubs: elementStubs } })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('改写查询')
    expect(wrapper.text()).toContain('project layered architecture')
    expect(wrapper.text()).toContain('知识库范围')
    expect(wrapper.text()).toContain('Top-K')
    expect(wrapper.text()).toContain('0.7')
    expect(wrapper.text()).toContain('architecture.md')
    expect(wrapper.text()).toContain('最终上下文')
    expect(wrapper.text()).toContain('引用校验通过')
    expect(wrapper.text()).toContain('28 Token')
    expect(wrapper.text()).toContain('50 ms')
  })
})
