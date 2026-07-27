import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { agentApi } from '@/api/agent'
import type {
  AgentTool,
  ToolCreate,
  ToolUpdate,
  ExecutionResponse,
  ExecutionListItem,
  AgentStep,
  AgentWorkflowMetrics
} from '@/types'

export const useAgentStore = defineStore('agent', () => {
  // State
  const tools = ref<AgentTool[]>([])
  const toolsTotal = ref(0)
  const executions = ref<ExecutionListItem[]>([])
  const executionsTotal = ref(0)
  const currentExecution = ref<ExecutionResponse | null>(null)
  const loading = ref(false)
  const executing = ref(false)
  const streamingSteps = ref<AgentStep[]>([])
  const streamingResult = ref('')
  const streamingMetrics = ref<AgentWorkflowMetrics>({})
  const streamingError = ref<string | null>(null)

  // Getters
  const enabledTools = computed(() => tools.value.filter(t => t.is_enabled))
  const builtinTools = computed(() => tools.value.filter(t => t.tool_type === 'builtin'))
  const customTools = computed(() => tools.value.filter(t => t.tool_type === 'custom'))

  // Actions
  async function fetchTools(params?: { skip?: number, limit?: number, tool_type?: string, is_enabled?: boolean }) {
    loading.value = true
    try {
      const res = await agentApi.getTools(params)
      tools.value = res.items
      toolsTotal.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function createTool(data: ToolCreate) {
    const tool = await agentApi.createTool(data)
    tools.value.unshift(tool)
    toolsTotal.value++
    return tool
  }

  async function updateTool(id: number, data: ToolUpdate) {
    const tool = await agentApi.updateTool(id, data)
    const index = tools.value.findIndex(t => t.id === id)
    if (index !== -1) {
      tools.value[index] = tool
    }
    return tool
  }

  async function deleteTool(id: number) {
    await agentApi.deleteTool(id)
    tools.value = tools.value.filter(t => t.id !== id)
    toolsTotal.value--
  }

  async function toggleTool(id: number, enabled: boolean) {
    return updateTool(id, { is_enabled: enabled })
  }

  async function executeTask(task: string, maxIterations?: number, knowledgeBaseIds?: number[]) {
    executing.value = true
    currentExecution.value = null
    streamingSteps.value = []
    streamingResult.value = ''
    streamingMetrics.value = {}
    streamingError.value = null
    
    try {
      const result = await agentApi.executeTask({ task, knowledge_base_ids: knowledgeBaseIds, max_iterations: maxIterations })
      currentExecution.value = result
      return result
    } finally {
      executing.value = false
    }
  }

  function streamExecuteTask(task: string, maxIterations?: number, knowledgeBaseIds?: number[]) {
    executing.value = true
    currentExecution.value = null
    streamingSteps.value = []
    streamingResult.value = ''
    streamingMetrics.value = {}
    streamingError.value = null
    
    const cancel = agentApi.streamExecuteTask(
      { task, knowledge_base_ids: knowledgeBaseIds, max_iterations: maxIterations },
      (event) => {
        if (event.type === 'step') {
          const index = streamingSteps.value.findIndex(step => step.step_number === event.data.step_number)
          if (index === -1) streamingSteps.value.push(event.data)
          else streamingSteps.value[index] = event.data
        } else if (event.type === 'token') {
          streamingResult.value += event.data.content
        } else if (event.type === 'result') {
          streamingResult.value = event.data.result
          if (event.data.steps) streamingSteps.value = event.data.steps
          streamingMetrics.value = event.data.metrics || {}
        } else if (event.type === 'error') {
          if (event.data.steps) streamingSteps.value = event.data.steps
          streamingMetrics.value = event.data.metrics || {}
          streamingError.value = event.data.message
          executing.value = false
        }
      },
      (error) => {
        executing.value = false
        streamingError.value = error.message
        console.error('流式执行错误:', error)
      },
      () => {
        executing.value = false
      }
    )
    
    return cancel
  }

  async function fetchExecutions(params?: { skip?: number, limit?: number, status?: string }) {
    loading.value = true
    try {
      const res = await agentApi.getExecutions(params)
      executions.value = res.items
      executionsTotal.value = res.total
    } finally {
      loading.value = false
    }
  }

  async function fetchExecution(id: number) {
    loading.value = true
    try {
      currentExecution.value = await agentApi.getExecution(id)
    } finally {
      loading.value = false
    }
  }

  function clearCurrentExecution() {
    currentExecution.value = null
    streamingSteps.value = []
    streamingResult.value = ''
    streamingMetrics.value = {}
    streamingError.value = null
  }

  return {
    tools,
    toolsTotal,
    executions,
    executionsTotal,
    currentExecution,
    loading,
    executing,
    streamingSteps,
    streamingResult,
    streamingMetrics,
    streamingError,
    enabledTools,
    builtinTools,
    customTools,
    fetchTools,
    createTool,
    updateTool,
    deleteTool,
    toggleTool,
    executeTask,
    streamExecuteTask,
    fetchExecutions,
    fetchExecution,
    clearCurrentExecution
  }
})
