// 认证相关类型
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserInfo {
  id: number
  username: string
  full_name?: string
  email?: string
  avatar?: string
  created_at: string
  is_active: boolean
  deletion_requested_at?: string
  deletion_scheduled_at?: string
}

// 对话相关类型
export interface Conversation {
  id: number
  title: string
  created_at: string
  updated_at: string
  message_count?: number
}

export interface Message {
  id: number
  conversation_id?: number
  role: 'user' | 'assistant' | 'system'
  content: string
  tokens?: number
  rag_used?: boolean
  sources?: DocumentChunk[]
  created_at: string
}

export interface ChatRequest {
  conversation_id?: number | null
  content: string
  config?: ChatConfig
  rag?: ChatRagConfig
}

export interface ChatConfig {
  temperature?: number
  max_tokens?: number
  system_prompt_id?: number | null
  knowledge_base_ids?: number[]
}

export type RAGStrategy = 'rag_only' | 'rag_prefer' | 'llm_only'

export interface ChatRagConfig {
  enabled?: boolean
  knowledge_base_ids?: number[]
  strategy?: RAGStrategy
  top_k?: number
  score_threshold?: number | null
}

// 知识库相关类型
export interface KnowledgeBase {
  id: number
  name: string
  description?: string
  category?: string
  document_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseCreate {
  name: string
  description?: string
  category?: string
}

export interface KnowledgeBaseUpdate {
  name?: string
  description?: string
  category?: string
}

export interface Document {
  id: number
  knowledge_base_id: number
  filename: string
  file_size: number
  file_type: string
  status: 'pending' | 'processing' | 'completed' | 'failed'
  chunk_count: number
  error_message?: string
  created_at: string
}

export interface DocumentUpload {
  id: number
  filename: string
  file_size: number
  status: string
  created_at: string
}

export interface RAGQueryRequest {
  knowledge_base_ids: number[]
  question: string
  top_k?: number
  conversation_id?: string
}

export interface DocumentChunk {
  content: string
  document_name: string
  similarity_score: number
  document_id?: number
  chunk_index?: number
  page?: number
  page_number?: number
  metadata?: Record<string, any>
}

export interface RAGQueryResponse {
  answer: string
  sources: DocumentChunk[]
  tokens_used: number
}

// Agent相关类型
export interface AgentTool {
  id: number
  name: string
  description: string
  tool_type: 'builtin' | 'custom'
  config?: Record<string, any>
  is_enabled: boolean
  created_at: string
}

export interface ToolCreate {
  name: string
  description: string
  config?: Record<string, any>
}

export interface ToolUpdate {
  name?: string
  description?: string
  config?: Record<string, any>
  is_enabled?: boolean
}

export interface TaskExecuteRequest {
  task: string
  knowledge_base_ids?: number[]
  max_iterations?: number
}

export interface AgentRetrievalParameters {
  top_k?: number
  similarity_threshold?: number
}

export interface CitationValidation {
  valid: boolean
  missing_citation_ids: string[]
}

export interface AgentStepData {
  original_question?: string
  rewritten_query?: string
  knowledge_base_scope?: number[]
  retrieval_parameters?: AgentRetrievalParameters
  raw_chunks?: DocumentChunk[]
  filtered_chunks?: DocumentChunk[]
  sources?: DocumentChunk[]
  final_context?: string
  context_char_count?: number
  raw_chunk_count?: number
  answer?: string
  citation_validation?: CitationValidation
  tokens_used?: number
  retrieval_time_ms?: number
  generation_time_ms?: number
  total_time_ms?: number
}

export interface AgentWorkflowMetrics {
  retrieval_time_ms?: number
  generation_time_ms?: number
  total_time_ms?: number
  tokens_used?: number
}

export interface AgentStep {
  step_number: number
  thought: string
  action: string
  action_input: Record<string, any> | string
  observation: string | Record<string, any>
  citations?: DocumentChunk[]
  citation_count?: number
  phase?: 'query_rewrite' | 'retrieval' | 'context_selection' | 'answer_and_citation_validation' | string
  data?: AgentStepData
  timestamp?: string
}

export type AgentStreamEvent =
  | { type: 'step'; data: AgentStep }
  | { type: 'token'; data: { content: string } }
  | { type: 'result'; data: { result: string; steps?: AgentStep[]; status?: ExecutionResponse['status']; metrics?: AgentWorkflowMetrics } }
  | { type: 'error'; data: { message: string; steps?: AgentStep[]; metrics?: AgentWorkflowMetrics } }

export interface ExecutionResponse {
  execution_id: number
  task: string
  result?: string
  steps: AgentStep[]
  status: 'pending' | 'running' | 'completed' | 'failed'
  error_message?: string
  created_at: string
  completed_at?: string
  metrics?: AgentWorkflowMetrics
}

export interface ExecutionListItem {
  execution_id: number
  task: string
  result?: string
  status: string
  error_message?: string
  step_count: number
  created_at: string
  completed_at?: string
}

// 系统提示词相关类型
export interface SystemPrompt {
  id: number
  user_id?: number
  name: string
  content: string
  category: string
  is_default: boolean
  is_system: boolean
  created_at: string
  updated_at: string
}

export interface SystemPromptCreate {
  name: string
  content: string
  category?: string
}

export interface SystemPromptUpdate {
  name?: string
  content?: string
  category?: string
}

// 知识库权限相关类型
export interface KnowledgeBasePermission {
  id: number
  knowledge_base_id: number
  user_id?: number
  username?: string
  permission_type: 'owner' | 'editor' | 'viewer'
  is_public: boolean
  created_at: string
}

export interface PermissionCreate {
  user_id?: number
  permission_type: 'editor' | 'viewer'
}

export interface PermissionUpdate {
  permission_type: 'editor' | 'viewer'
}

export interface ShareKnowledgeBaseRequest {
  username: string
  permission_type: 'editor' | 'viewer'
}

// 用户头像相关类型
export interface AvatarUploadResponse {
  avatar_url: string
  thumbnail_url: string
  message: string
}

// API响应类型
export interface ApiResponse<T = any> {
  code?: number
  message?: string
  data?: T
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface PaginatedList<T> {
  items: T[]
  total: number
}
