import { describe, expect, it, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AgentView from '@/views/agent/AgentView.vue'
import { useAgentStore } from '@/stores/agent'
import { useKnowledgeStore } from '@/stores/knowledge'

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn() }
}))

describe('AgentView RAG citation timeline', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders retrieval tool events and source citation metadata', async () => {
    const store = useAgentStore()
    vi.spyOn(store, 'fetchExecutions').mockResolvedValue(undefined)
    const knowledgeStore = useKnowledgeStore()
    vi.spyOn(knowledgeStore, 'fetchKnowledgeBases').mockResolvedValue(undefined)
    store.currentExecution = {
      execution_id: 7,
      task: '系统架构是什么？',
      status: 'completed',
      created_at: '2026-07-26T10:00:00Z',
      result: '系统采用分层架构。',
      steps: [{
        step_number: 1,
        thought: '先检索知识库',
        action: 'knowledge_base_retrieval',
        action_input: { query: '系统架构', knowledge_base_ids: [1], top_k: 3 },
        observation: JSON.stringify({
          type: 'tool_result',
          retrieval_time_ms: 42.5,
          sources: [{ document_name: '架构设计.md', page: 3, similarity_score: 0.92, content: '采用 API、Service、Repository 分层。' }]
        }),
        timestamp: '2026-07-26T10:00:01Z'
      }]
    }

    const wrapper = mount(AgentView, { global: { stubs: {
      'el-button': true, 'el-input': true, 'el-input-number': true,
      'el-select': true, 'el-option': true, 'el-alert': true,
      'el-tag': { template: '<span><slot /></span>' }, 'el-icon': true,
      'el-timeline': { template: '<div><slot /></div>' },
      'el-timeline-item': { template: '<div><slot /></div>' },
      'el-card': { template: '<div><slot /></div>' },
      'el-table': { template: '<div><slot /></div>' }, 'el-table-column': true, 'el-empty': true
    } } })
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('知识库检索')
    expect(wrapper.text()).toContain('42.5 ms')
    expect(wrapper.text()).toContain('架构设计.md')
    expect(wrapper.text()).toContain('第 3 页')
    expect(wrapper.text()).toContain('92%')
    expect(wrapper.text()).toContain('采用 API、Service、Repository 分层。')
  })
})
