<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Clock, Close, Loading, VideoPlay } from '@element-plus/icons-vue'
import { useAgentStore } from '@/stores/agent'
import { useKnowledgeStore } from '@/stores/knowledge'
import type {
  AgentStep,
  AgentStepData,
  AgentWorkflowMetrics,
  DocumentChunk,
  ExecutionListItem
} from '@/types'

type WorkflowStage = {
  step: AgentStep
  data: AgentStepData
  title: string
}

const agentStore = useAgentStore()
const knowledgeStore = useKnowledgeStore()
const question = ref('')
const selectedKnowledgeBaseIds = ref<number[]>([])
const maxIterations = ref(8)

const activeSteps = computed(() => agentStore.currentExecution?.steps ?? agentStore.streamingSteps)
const canRun = computed(
  () => question.value.trim().length > 0 && selectedKnowledgeBaseIds.value.length > 0 && !agentStore.executing
)
const selectedKnowledgeBases = computed(() =>
  knowledgeStore.knowledgeBases.filter(knowledgeBase => selectedKnowledgeBaseIds.value.includes(knowledgeBase.id))
)

function parseObservation(observation: AgentStep['observation']): AgentStepData {
  if (!observation) return {}
  if (typeof observation === 'object') return observation as AgentStepData
  try {
    const parsed = JSON.parse(observation)
    return parsed && typeof parsed === 'object' ? parsed as AgentStepData : {}
  } catch {
    return {}
  }
}

function dataOf(step: AgentStep): AgentStepData {
  return { ...parseObservation(step.observation), ...step.data }
}

function stageTitle(phase?: AgentStep['phase'], action?: string): string {
  const title = {
    query_rewrite: '改写查询',
    retrieval: '知识库检索',
    context_selection: '上下文筛选',
    answer_and_citation_validation: '生成回答与引用校验'
  }[phase || '']
  if (title) return title
  return /knowledge[_ -]?base|retriev|rag/i.test(action || '') ? '知识库检索' : 'RAG 工作流步骤'
}

const workflowStages = computed<WorkflowStage[]>(() =>
  activeSteps.value.map(step => ({ step, data: dataOf(step), title: stageTitle(step.phase, step.action) }))
)

const answer = computed(() => agentStore.currentExecution?.result ?? agentStore.streamingResult)
const workflowMetrics = computed<AgentWorkflowMetrics>(() => {
  const retrieval = workflowStages.value.find(stage => stage.step.phase === 'retrieval')?.data
  const completion = workflowStages.value.find(
    stage => stage.step.phase === 'answer_and_citation_validation'
  )?.data
  return {
    retrieval_time_ms: retrieval?.retrieval_time_ms,
    generation_time_ms: completion?.generation_time_ms,
    total_time_ms: completion?.total_time_ms,
    tokens_used: completion?.tokens_used,
    ...agentStore.currentExecution?.metrics,
    ...agentStore.streamingMetrics
  }
})

function chunksFor(data: AgentStepData, fallback: DocumentChunk[] = []): DocumentChunk[] {
  return data.raw_chunks || data.filtered_chunks || data.sources || fallback
}

function scopeLabel(scope?: number[]): string {
  if (!scope?.length) return '未指定'
  return scope.map(id => {
    const knowledgeBase = knowledgeStore.knowledgeBases.find(item => item.id === id)
    return knowledgeBase ? `${knowledgeBase.name} (#${id})` : `#${id}`
  }).join('、')
}

function scorePercent(score: number): string {
  return `${Math.round(Math.max(0, Math.min(1, Number(score) || 0)) * 100)}%`
}

function statusType(status: string): string {
  return ({ pending: 'info', running: 'warning', completed: 'success', failed: 'danger' } as Record<string, string>)[status] || 'info'
}

function statusIcon(status: string) {
  return ({ pending: Clock, running: Loading, completed: Check, failed: Close } as Record<string, unknown>)[status] || Clock
}

async function runQuery() {
  if (!canRun.value) return
  try {
    await agentStore.executeTask(question.value.trim(), maxIterations.value, selectedKnowledgeBaseIds.value)
    ElMessage.success('RAG Agent 执行完成')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '执行失败')
  }
}

function streamQuery() {
  if (!canRun.value) return
  agentStore.streamExecuteTask(question.value.trim(), maxIterations.value, selectedKnowledgeBaseIds.value)
}

function selectExecution(execution: ExecutionListItem) {
  void agentStore.fetchExecution(execution.execution_id)
}

onMounted(() => {
  void agentStore.fetchExecutions().catch(() => undefined)
  void knowledgeStore.fetchKnowledgeBases().catch(() => undefined)
})
</script>

<template>
  <div class="rag-agent-view">
    <header class="page-header">
      <div>
        <h2>RAG Agent 调试台</h2>
        <p>仅使用所选本地知识库，展示受限 RAG Agent 的四阶段执行证据。</p>
      </div>
      <el-tag type="success" effect="plain">仅本地知识库</el-tag>
    </header>

    <section class="query-panel" aria-label="RAG Agent 查询">
      <label for="agent-question">问题</label>
      <el-input
        id="agent-question"
        v-model="question"
        type="textarea"
        :rows="3"
        maxlength="2000"
        show-word-limit
        placeholder="输入基于知识库的问题"
      />
      <label for="agent-knowledge-bases">可检索知识库</label>
      <el-select
        id="agent-knowledge-bases"
        v-model="selectedKnowledgeBaseIds"
        class="kb-select"
        multiple
        filterable
        clearable
        placeholder="请选择至少一个知识库"
        aria-label="可检索知识库"
      >
        <el-option
          v-for="knowledgeBase in knowledgeStore.knowledgeBases"
          :key="knowledgeBase.id"
          :label="`${knowledgeBase.name} (#${knowledgeBase.id})`"
          :value="knowledgeBase.id"
        />
      </el-select>
      <p v-if="selectedKnowledgeBases.length" class="selected-scope">
        已选择：{{ selectedKnowledgeBases.map(item => item.name).join('、') }}
      </p>
      <div class="query-actions">
        <label>最大步骤
          <el-input-number v-model="maxIterations" :min="1" :max="30" size="small" />
        </label>
        <div>
          <el-button type="primary" :icon="VideoPlay" :loading="agentStore.executing" :disabled="!canRun" @click="runQuery">
            执行检索
          </el-button>
          <el-button :icon="VideoPlay" :loading="agentStore.executing" :disabled="!canRun" @click="streamQuery">
            流式调试
          </el-button>
        </div>
      </div>
    </section>

    <el-alert
      v-if="agentStore.streamingError"
      class="execution-error"
      type="error"
      :title="agentStore.streamingError"
      :closable="false"
      show-icon
    />

    <section v-if="workflowStages.length" class="trace-panel" aria-label="RAG Agent 工作流时间线">
      <h3>执行与引用时间线</h3>
      <el-timeline>
        <el-timeline-item
          v-for="stage in workflowStages"
          :key="stage.step.step_number"
          :timestamp="stage.step.timestamp"
          placement="top"
        >
          <el-card shadow="never" class="timeline-card">
            <div class="event-heading">
              <strong>{{ stage.step.step_number }}. {{ stage.title }}</strong>
              <el-tag size="small" effect="plain">{{ stage.step.action }}</el-tag>
            </div>

            <div v-if="stage.data.knowledge_base_scope" class="field-row">
              <span>知识库范围</span><strong>{{ scopeLabel(stage.data.knowledge_base_scope) }}</strong>
            </div>
            <div v-if="stage.data.rewritten_query" class="field-row">
              <span>改写查询</span><strong>{{ stage.data.rewritten_query }}</strong>
            </div>
            <div v-if="stage.data.retrieval_parameters" class="field-row">
              <span>检索参数</span>
              <strong>Top-K {{ stage.data.retrieval_parameters.top_k ?? '—' }} · 阈值 {{ stage.data.retrieval_parameters.similarity_threshold ?? '—' }}</strong>
            </div>
            <div v-if="stage.data.retrieval_time_ms !== undefined" class="field-row">
              <span>检索耗时</span><strong>{{ stage.data.retrieval_time_ms }} ms</strong>
            </div>

            <div v-if="chunksFor(stage.data, stage.step.citations).length" class="citations">
              <h4>{{ stage.data.filtered_chunks ? '筛选后片段' : '检索片段' }}</h4>
              <article
                v-for="(source, sourceIndex) in chunksFor(stage.data, stage.step.citations)"
                :key="`${source.document_id ?? source.document_name}-${sourceIndex}`"
                class="citation"
              >
                <div>
                  <strong>{{ source.document_name }}</strong>
                  <span v-if="source.page ?? source.page_number"> · 第 {{ source.page ?? source.page_number }} 页</span>
                  <span v-if="source.chunk_index !== undefined"> · 片段 {{ source.chunk_index }}</span>
                  <el-tag size="small" type="success">{{ scorePercent(source.similarity_score) }}</el-tag>
                </div>
                <p>{{ source.content }}</p>
              </article>
            </div>

            <div v-if="stage.data.final_context" class="final-context">
              <h4>最终上下文</h4>
              <pre>{{ stage.data.final_context }}</pre>
            </div>

            <div v-if="stage.data.citation_validation" class="field-row citation-validation">
              <span>引用校验</span>
              <el-tag :type="stage.data.citation_validation.valid ? 'success' : 'danger'">
                {{ stage.data.citation_validation.valid ? '引用校验通过' : '引用校验失败' }}
              </el-tag>
              <small v-if="stage.data.citation_validation.missing_citation_ids.length">
                缺失：{{ stage.data.citation_validation.missing_citation_ids.join('、') }}
              </small>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </section>
    <section v-else class="trace-panel">
      <el-empty description="提交问题后显示四阶段 RAG 执行轨迹" />
    </section>

    <section v-if="answer || workflowStages.length" class="answer-panel" aria-live="polite">
      <h3>流式回答</h3>
      <p>{{ answer || '正在等待模型输出…' }}</p>
      <div class="metric-grid" aria-label="执行指标">
        <div><span>Token</span><strong>{{ workflowMetrics.tokens_used ?? 0 }} Token</strong></div>
        <div><span>检索耗时</span><strong>{{ workflowMetrics.retrieval_time_ms ?? 0 }} ms</strong></div>
        <div><span>生成耗时</span><strong>{{ workflowMetrics.generation_time_ms ?? 0 }} ms</strong></div>
        <div><span>总耗时</span><strong>{{ workflowMetrics.total_time_ms ?? 0 }} ms</strong></div>
      </div>
    </section>

    <section class="history-panel">
      <h3>最近调试记录</h3>
      <el-empty v-if="!agentStore.executions.length" description="暂无调试记录" />
      <el-table
        v-else
        :data="agentStore.executions.slice(0, 8)"
        size="small"
        @row-click="selectExecution"
      >
        <el-table-column prop="task" label="问题" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">
              <el-icon><component :is="statusIcon(row.status)" /></el-icon>{{ row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="时间" width="180" />
      </el-table>
    </section>
  </div>
</template>

<style scoped>
.rag-agent-view { height: 100%; overflow: auto; padding: 24px; background: var(--el-bg-color-page); }
.page-header, .query-actions, .event-heading, .field-row { display: flex; align-items: center; gap: 12px; }
.page-header, .query-actions { justify-content: space-between; }
.page-header { margin-bottom: 20px; }
h2, h3, h4 { margin: 0; }
.page-header p { margin: 8px 0 0; color: var(--el-text-color-secondary); }
.query-panel, .trace-panel, .answer-panel, .history-panel { margin-bottom: 20px; padding: 20px; background: var(--el-bg-color); border-radius: 8px; }
.query-panel > label { display: block; margin: 12px 0 6px; font-weight: 600; }
.query-panel > label:first-child { margin-top: 0; }
.kb-select { width: 100%; }
.selected-scope { margin: 8px 0 0; color: var(--el-text-color-secondary); }
.query-actions { margin-top: 14px; }
.query-actions > label { display: flex; align-items: center; gap: 8px; color: var(--el-text-color-secondary); }
.execution-error { margin-bottom: 20px; }
.timeline-card { margin-bottom: 8px; }
.event-heading { justify-content: space-between; }
.field-row { margin-top: 12px; align-items: baseline; flex-wrap: wrap; }
.field-row > span { min-width: 84px; color: var(--el-text-color-secondary); }
.field-row small { color: var(--el-color-danger); }
.citations, .final-context { margin-top: 16px; }
.citations h4, .final-context h4 { margin-bottom: 8px; font-size: 14px; }
.citation { margin-top: 8px; padding: 12px; border-left: 3px solid var(--el-color-success); background: var(--el-fill-color-light); }
.citation .el-tag { float: right; }
.citation p, .answer-panel > p { margin: 8px 0 0; white-space: pre-wrap; line-height: 1.6; }
.final-context pre { max-height: 260px; overflow: auto; padding: 12px; white-space: pre-wrap; background: var(--el-fill-color-light); }
.metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(135px, 1fr)); gap: 12px; margin-top: 16px; }
.metric-grid > div { padding: 12px; border: 1px solid var(--el-border-color-lighter); border-radius: 6px; }
.metric-grid span, .metric-grid strong { display: block; }
.metric-grid span { color: var(--el-text-color-secondary); font-size: 13px; }
.metric-grid strong { margin-top: 4px; font-variant-numeric: tabular-nums; }
</style>
