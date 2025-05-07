// User and Authentication types
export interface User {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login?: string;
  preferences: UserPreferences;
}

export enum UserRole {
  ADMIN = 'admin',
  USER = 'user',
  GUEST = 'guest'
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  notification_enabled: boolean;
  items_per_page: number;
}

export interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isLoggedIn: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface LoginRequest {
  username: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
  full_name: string;
}

// Document types
export interface Document {
  id: string;
  title: string;
  content: string;
  content_type: string;
  source: string;
  owner_id: string;
  created_at: string;
  updated_at: string | null;
  language: string;
  metadata: Record<string, any>;
  enrichment_status: EnrichmentStatus;
}

export enum EnrichmentStatus {
  PENDING = 'pending',
  PROCESSING = 'processing',
  COMPLETED = 'completed',
  FAILED = 'failed',
  SKIPPED = 'skipped'
}

export interface DocumentMetadata {
  original_filename?: string;
  file_size?: number;
  author?: string;
  created_at?: string;
  modified_at?: string;
  document_type?: string;
  page_count?: number;
  language_detected?: string;
  [key: string]: any;
}

export interface DocumentEnrichment {
  id: string;
  document_id: string;
  type: string;
  data: any;
  created_at: string;
  agent: string;
}

export interface DocumentSummary {
  overall: string;
  detailed?: string;
  sections?: string[];
}

export interface DocumentTag {
  tag: string;
  confidence: number;
  category?: string;
}

// Query and Search types
export interface Query {
  id: string;
  text: string;
  sessionId: string;
  timestamp: string;
  language?: string;
  result?: QueryResult;
}

export interface QueryResult {
  answer: string;
  sources: Source[];
  processing_time: number;
  token_usage?: TokenUsage;
}

export interface Source {
  id: string;
  title: string;
  url?: string;
  content_type: string;
  score: number;
  metadata: Record<string, any>;
  content?: string;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

// Data source types
export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  config: any;
  owner_id: string;
  created_at: string;
}

export enum DataSourceType {
  FILE = 'file',
  WEB = 'web',
  DATABASE = 'database',
  API = 'api',
  SQL = 'sql'
}

export interface SQLSourceConfig {
  connection_string: string;
  query?: string;
  tables?: string[];
  schema?: string;
  max_rows: number;
}

export interface WebSourceConfig {
  url: string;
  crawl_depth: number;
  include_patterns: string[];
  exclude_patterns: string[];
}

// Agent types
export interface Agent {
  name: string;
  description: string;
  version: string;
  is_active: boolean;
  is_initialized: boolean;
  metrics: AgentMetrics;
}

export interface AgentMetrics {
  processing_time: number;
  token_usage: number;
  successful_runs: number;
  failed_runs: number;
  last_run_timestamp: string | null;
}

// System metrics and monitoring
export interface SystemMetrics {
  cpu_usage: number;
  memory_usage: number;
  disk_usage: number;
  active_users: number;
  queries_per_minute: number;
  average_query_time: number;
  error_rate: number;
  timestamp: string;
}

export interface LLMMetrics {
  total_tokens: number;
  calls: number;
  average_response_time: number;
  error_rate: number;
  tokens_per_provider: Record<string, number>;
  cost_estimate: number;
}

// Error and notification types
export interface ApiError {
  status: number;
  message: string;
  details?: Record<string, any>;
  path?: string;
  timestamp?: string;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
}

// Memory and context types
export interface MemorySession {
  id: string;
  user_id: string;
  created_at: string;
  last_used: string;
  metadata: Record<string, any>;
}

export interface ContextItem {
  id: string;
  session_id: string;
  type: 'query' | 'response' | 'document' | 'system';
  content: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

// Synthetic QA types
export interface SyntheticQA {
  id: string;
  document_id: string;
  question: string;
  answer: string;
  relevance_score: number;
  created_at: string;
}

// Search and retrieval types
export interface SearchRequest {
  query: string;
  filter?: SearchFilter;
  sort?: SearchSort;
  pagination?: Pagination;
}

export interface SearchFilter {
  document_types?: string[];
  date_range?: DateRange;
  languages?: string[];
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface DateRange {
  start?: string;
  end?: string;
}

export interface SearchSort {
  field: string;
  direction: 'asc' | 'desc';
}

export interface Pagination {
  page: number;
  items_per_page: number;
}

export interface SearchResult {
  hits: SearchHit[];
  total: number;
  page: number;
  items_per_page: number;
  processing_time: number;
}

export interface SearchHit {
  id: string;
  document_id: string;
  title: string;
  content_snippet: string;
  score: number;
  highlights?: string[];
  metadata: Record<string, any>;
}

// Settings and configuration types
export interface SystemSettings {
  llm: LLMSettings;
  retrieval: RetrievalSettings;
  enrichment: EnrichmentSettings;
  agents: AgentSettings;
  language: LanguageSettings;
}

export interface LLMSettings {
  provider: string;
  model: string;
  temperature: number;
  max_tokens: number;
}

export interface RetrievalSettings {
  type: 'dense' | 'sparse' | 'hybrid';
  top_k: number;
  reranking_enabled: boolean;
  similarity_threshold: number;
}

export interface EnrichmentSettings {
  enabled: boolean;
  synthetic_qa_enabled: boolean;
  questions_per_document: number;
  entity_masking_enabled: boolean;
}

export interface AgentSettings {
  active_agents: string[];
  timeout_seconds: number;
  retry_attempts: number;
  concurrency: number;
}

export interface LanguageSettings {
  default_language: string;
  supported_languages: string[];
  translation_enabled: boolean;
}