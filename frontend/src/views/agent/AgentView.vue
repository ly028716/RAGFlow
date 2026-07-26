<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Clock, Close, Loading, VideoPlay } from '@element-plus/icons-vue'
import { useAgentStore } from '@/stores/agent'
import type { AgentStep, DocumentChunk } from '@/types'

type Citation = DocumentChunk & { page?: number; chunk_id?: string }
type TimelineEvent = {
  kind: 'tool_call' | 'tool_result' | 'answer'
  title: string
  step?: AgentStep
  timestamp?: string
  input?: Record<string, unknown> | string
  observation?: string
  retrievalTimeMs?: number
  sources: Citation[]
}

const agentStore = useAgentStore()
const question = ref('')
const knowledgeBaseIds = ref('')
const maxIterations = ref(8)
const canRun = computed(() => question.value.trim().length > 0 && !agentStore.executing)
const activeSteps = computed(() => agentStore.currentExecution?.steps || agentStore.streamingSteps)

function parseObservation(value: unknown): any {
  if (!value) return {}
  if (typeof value === 'object') return value as Record<string, any>
  try { return JSON.parse(value as string) } catch { return {} }
}

function normalizeCitation(raw: any): Citation {
  const metadata = raw?.metadata ?? {}
  return {
    content: String(raw?.content ?? raw?.text ?? raw?.page_content ?? metadata.content ?? ''),
    document_name: String(raw?.document_name ?? raw?.document ?? raw?.source ?? metadata.document_name ?? metadata.source ?? '未知文档'),
    similarity_score: Number(raw?.similarity_score ?? raw?.similarity ?? raw?.score ?? metadata.similarity_score ?? metadata.score ?? 0),
    document_id: raw?.document_id ?? metadata.document_id,
    chunk_index: raw?.chunk_index ?? metadata.chunk_index,
    page: raw?.page ?? raw?.page_number ?? metadata.page ?? metadata.page_number
  }
}

function citationsFrom(step: AgentStep): Citation[] {
  const data = parseObservation(step.observation)
  const nested = typeof data?.result === 'string' ? parseObservation(data.result) : data?.result
  const raw = step.citations ?? data?.sources ?? data?.citations ?? data?.documents ?? data?.results ?? nested?.sources ?? nested?.results ?? (Array.isArray(data) ? data : [])
  return Array.isArray(raw) ? raw.map(normalizeCitation) : []
}

function isRetrievalAction(action: string) {
  return /knowledge[_ -]?base|retriev|rag/i.test(action)
}

const timeline = computed<TimelineEvent[]>(() => {
  const events: TimelineEvent[] = []
  for (const step of activeSteps.value || []) {
    const retrieval = isRetrievalAction(step.action || '')
    events.push({ kind: 'tool_call', title: retrieval ? '知识库检索' : `工具调用：${step.action || 'unknown'}`,
      step, timestamp: step.timestamp, input: step.action_input, sources: [] })
    const data = parseObservation(step.observation)
    const nested = typeof data?.result === 'string' ? parseObservation(data.result) : data?.result
    events.push({ kind: 'tool_result', title: retrieval ? '检索结果' : '工具结果', step,
      timestamp: step.timestamp, observation: typeof step.observation === 'string' ? step.observation : JSON.stringify(step.observation),
      retrievalTimeMs: Number(data?.retrieval_time_ms ?? data?.elapsed_ms ?? nested?.retrieval_time_ms) || undefined,
      sources: citationsFrom(step) })
  }
  const answer = agentStore.currentExecution?.result || agentStore.streamingResult
  if (answer) events.push({ kind: 'answer', title: '最终回答', observation: answer, sources: [] })
  return events
})

async function runQuery() {
  if (!canRun.value) return
  try { await agentStore.executeTask(question.value.trim(), undefined, maxIterations.value, parseKnowledgeBaseIds()); ElMessage.success('RAG Agent 执行完成') }
  catch (error: any) { ElMessage.error(error?.response?.data?.detail || '执行失败') }
}
function streamQuery() { if (canRun.value) agentStore.streamExecuteTask(question.value.trim(), undefined, maxIterations.value, parseKnowledgeBaseIds()) }
function parseKnowledgeBaseIds() {
  const ids = knowledgeBaseIds.value.split(',').map(value => Number(value.trim())).filter(value => Number.isInteger(value) && value > 0)
  return ids.length ? ids : undefined
}
function statusType(status: string) { return ({ pending: 'info', running: 'warning', completed: 'success', failed: 'danger' } as Record<string, string>)[status] || 'info' }
function statusIcon(status: string) { return ({ pending: Clock, running: Loading, completed: Check, failed: Close } as Record<string, any>)[status] || Clock }
function scorePercent(score: number) { return `${Math.round(Math.max(0, Math.min(1, score)) * 100)}%` }
function inputText(input?: Record<string, unknown> | string) { return input ? (typeof input === 'string' ? input : JSON.stringify(input)) : '' }
function observationText(event: TimelineEvent) { return event.observation && !event.sources.length ? event.observation : '' }

onMounted(() => agentStore.fetchExecutions())
</script>

<template>
  <div class="rag-agent-view">
    <header class="page-header"><div><h2>RAG Agent 调试台</h2><p>查看知识库检索工具调用、引用片段与生成耗时。</p></div><el-tag type="success" effect="plain">仅本地知识库</el-tag></header>
    <section class="query-panel"><el-input v-model="question" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="输入基于知识库的问题" /><el-input v-model="knowledgeBaseIds" class="kb-input" placeholder="知识库 ID（逗号分隔，例如 1,2）" /><div class="query-actions"><label>最大步数 <el-input-number v-model="maxIterations" :min="1" :max="30" size="small" /></label><div><el-button type="primary" :icon="VideoPlay" :loading="agentStore.executing" :disabled="!canRun" @click="runQuery">执行检索</el-button><el-button :icon="VideoPlay" :loading="agentStore.executing" :disabled="!canRun" @click="streamQuery">流式调试</el-button></div></div></section>

    <section v-if="timeline.length" class="trace-panel"><h3>执行与引用时间线</h3><el-timeline>
      <el-timeline-item v-for="(event, index) in timeline" :key="`${event.kind}-${index}`" :timestamp="event.timestamp" placement="top">
        <el-card shadow="never" class="timeline-card">
          <div class="event-heading"><strong>{{ event.title }}</strong><el-tag size="small" effect="plain">{{ event.kind }}</el-tag><span v-if="event.retrievalTimeMs !== undefined" class="duration">{{ event.retrievalTimeMs }} ms</span></div>
          <p v-if="event.step?.thought && event.kind === 'tool_call'" class="thought">{{ event.step.thought }}</p>
          <pre v-if="event.kind === 'tool_call' && event.input">{{ inputText(event.input) }}</pre>
          <p v-if="observationText(event)" class="observation">{{ observationText(event) }}</p>
          <div v-if="event.sources.length" class="citations"><div v-for="(source, sourceIndex) in event.sources" :key="sourceIndex" class="citation"><div><strong>{{ source.document_name }}</strong><span v-if="source.page !== undefined"> · 第 {{ source.page }} 页</span><span v-if="source.chunk_index !== undefined"> · 片段 {{ source.chunk_index }}</span><el-tag size="small" type="success">{{ scorePercent(source.similarity_score) }}</el-tag></div><p>{{ source.content }}</p></div></div>
        </el-card>
      </el-timeline-item>
    </el-timeline></section>
    <section v-else class="trace-panel"><el-empty description="提交问题后显示检索时间线" /></section>

    <section class="history-panel"><h3>最近调试记录</h3><el-empty v-if="!agentStore.executions.length" description="暂无调试记录" /><el-table v-else :data="agentStore.executions.slice(0, 8)" size="small" @row-click="row => agentStore.fetchExecution(row.execution_id)"><el-table-column prop="task" label="问题" show-overflow-tooltip /><el-table-column prop="status" label="状态" width="110"><template #default="{ row }"><el-tag :type="statusType(row.status)" size="small"><el-icon><component :is="statusIcon(row.status)" /></el-icon>{{ row.status }}</el-tag></template></el-table-column><el-table-column prop="created_at" label="时间" width="180" /></el-table></section>
  </div>
</template>

<style scoped>
.rag-agent-view { height: 100%; overflow: auto; padding: 24px; background: var(--el-bg-color-page); }
.page-header, .query-actions, .event-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; }
.page-header { margin-bottom: 20px; } h2, h3 { margin: 0; } .page-header p { margin: 8px 0 0; color: var(--el-text-color-secondary); }
.query-panel, .trace-panel, .history-panel { margin-bottom: 20px; padding: 20px; background: #fff; border-radius: 8px; }
.kb-input { margin-top: 12px; }
.query-actions { margin-top: 14px; } .query-actions label { display: flex; align-items: center; gap: 8px; color: var(--el-text-color-secondary); }
.event-heading { justify-content: flex-start; } .event-heading .duration { margin-left: auto; color: var(--el-color-primary); font-variant-numeric: tabular-nums; }
.thought, .observation { white-space: pre-wrap; line-height: 1.6; } pre { white-space: pre-wrap; margin: 8px 0; color: var(--el-text-color-secondary); }
.citation { margin-top: 12px; padding: 12px; border-left: 3px solid var(--el-color-success); background: var(--el-fill-color-light); } .citation .el-tag { float: right; } .citation p { margin: 8px 0 0; line-height: 1.5; }
</style>
