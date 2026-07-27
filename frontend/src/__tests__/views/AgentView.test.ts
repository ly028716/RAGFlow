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
  'el-input': {
    props: ['modelValue'],
    emits: ['update:modelValue'],
    template: '<textarea :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />'
  },
  'el-input-number': true,
  'el-select': {
    emits: ['update:modelValue'],
    template: '<select @change="$emit(\'update:modelValue\', [Number($event.target.value)])"><slot /></select>'
  },
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

describe('AgentView local RAG query controls', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('renders the selected-knowledge-base query workflow instead of a tool sidebar', async () => {
    const agentStore = useAgentStore()
    const knowledgeStore = useKnowledgeStore()
    vi.spyOn(agentStore, 'fetchExecutions').mockResolvedValue(undefined)
    vi.spyOn(knowledgeStore, 'fetchKnowledgeBases').mockResolvedValue(undefined)

    const wrapper = mount(AgentView, { global: { stubs: elementStubs } })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.rag-agent-view').exists()).toBe(true)
    expect(wrapper.find('.query-panel').exists()).toBe(true)
    expect(wrapper.find('.history-panel').exists()).toBe(true)
    expect(wrapper.text()).toContain('RAG Agent 调试台')
    expect(wrapper.text()).toContain('可检索知识库')
    expect(wrapper.text()).not.toContain('内置工具')
    expect(wrapper.text()).not.toContain('calculator')
    expect(wrapper.text()).not.toContain('seed_data.py')
  })

  it('requires both a question and a knowledge-base selection before execution', async () => {
    const agentStore = useAgentStore()
    const knowledgeStore = useKnowledgeStore()
    vi.spyOn(agentStore, 'fetchExecutions').mockResolvedValue(undefined)
    vi.spyOn(knowledgeStore, 'fetchKnowledgeBases').mockResolvedValue(undefined)
    const wrapper = mount(AgentView, { global: { stubs: elementStubs } })
    const buttons = wrapper.findAll('el-button-stub')

    expect(buttons).toHaveLength(2)
    expect(buttons.every(button => button.attributes('disabled') !== undefined)).toBe(true)

    await wrapper.find('textarea').setValue('How is the system deployed?')
    expect(buttons.every(button => button.attributes('disabled') !== undefined)).toBe(true)

    await wrapper.find('select').setValue('1')
    expect(buttons.map(button => button.attributes('disabled'))).toEqual(['false', 'false'])
  })
})
