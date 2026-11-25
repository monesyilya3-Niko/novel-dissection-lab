// 前端类型定义。这里用 camelCase 命名（对齐 TS 习惯），
// 与后端 snake_case JSON 的转换统一在 api/client.ts 中完成。

export type BatchStatus = 'pending' | 'running' | 'success' | 'failed' | 'skipped'

export interface Batch {
  chapterIndex: number
  batchIndex: number
  charStart: number
  charEnd: number
  text: string
  status: BatchStatus
}

export interface Chapter {
  index: number
  title: string
  batchCount: number
  text?: string
  batches: Batch[]
}

export interface Book {
  bookId: string
  title: string
  sourcePath: string
  totalChapters: number
  /** 切章时因正文为空被跳过的章数（导入报告用，2026-11-04） */
  skippedEmptyChapters?: number
  chapters: Chapter[]
}

export interface BatchState {
  status: BatchStatus
  asset?: string
  ts: number
}

export interface TaskState {
  schemaVersion: number
  bookId: string
  title: string
  stateRevision: number
  cursor: string
  chapterStates: Record<string, BatchState>
  assetIndex: Record<string, string[]>
}

export interface ProgressEvent {
  bookId?: string | null
  taskId?: string | null
  taskType?: string | null
  cursor: string
  chapterIndex: number
  batchIndex: number
  // 后端会推送 running/success/failed（批级）以及 paused/done/error（任务级）。
  status: BatchStatus | 'paused' | 'done' | 'error'
  done: number
  total: number
}

export interface ModelInfo {
  id: string
  modelName: string
  protocol: string
  baseUrl: string
  hasKey: boolean
}

export interface ApiResponse<T> {
  code: number
  data: T
  message: string
}

// 服务端状态机：idle | running | paused | done | error
export type TaskStatus = 'idle' | 'running' | 'paused' | 'done' | 'partial' | 'error'

export interface StatusInfo {
  status: TaskStatus
  bookId: string | null
  cursor: string
  done: number
  total: number
  lastError?: string
  reportError?: string
  takeoverGuidePath?: string
  /** 批次状态快照（c1-b0 → {status, asset}）；刷新后据此恢复进度矩阵。 */
  chapterStates?: Record<string, { status: string; asset?: string | null }>
}

// ---------------------------------------------------------------------------
// 阶段一新增类型（工作台可视化，见 DESIGN_gui_workbench §3.4）
// ---------------------------------------------------------------------------

export type AssetKind =
  | 'voice'
  | 'structure'
  | 'commercial'
  | 'craft'
  | 'genre_pack'
  | 'prose_card'
  // 跨书题材蒸馏卡（distilled）与题材文风卡寻址索引（prose_card_index）各自独立成 kind，
  // 不得与 voice / prose_card 混用（后端 services.assert_asset_kind 按内容拒绝错配）。
  | 'distilled'
  | 'prose_card_index'
  | 'trope'
  | 'report'
  | 'book'

export interface AssetItem {
  kind: AssetKind
  id: string
  name: string
  path: string
  size: number
  mtime: number
  bookId?: string
  /** 该题材 slug（题材包 / 文风卡的题材标识），用于判断两份是否同题材 */
  genre?: string
  /** 一句话说明「这是什么」，列表层直接显示，免得用户点进去才知道 */
  purpose?: string
  /** 一句话说明「用在哪」，与 purpose 配套 */
  usage?: string
}

export interface Overview {
  /** 已拆完的书（status=done），首页「已拆书」KPI 用。 */
  totalBooks: number
  /** 已导入的书（含未拆），用于判断是否真正的新手空库。 */
  totalImportedBooks?: number
  /** 写作项目中已入库的章节数（chapter-*.txt）。 */
  totalWritingChapters?: number
  /** reports/qc 下已生成的 QC 报告数。 */
  totalQcReports?: number
  totalGenrePacks: number
  totalReports: number
  totalAssets: number
  assetsByKind: Record<string, number>
  modelConfigured: boolean
  modelReady?: boolean
  recentActivity: string[]
}

export interface OfflineAnalysisResult {
  bookId: string
  title: string
  genre: string
  totalChapters: number
  selectedCount: number
  selectedIndices: number[]
  sampleWords: number
  metrics: Record<string, unknown>
  sampledDir: string
  rawDir: string
  guidePath: string
  guideMarkdown: string
}

export interface TakeoverPassSummary {
  passName: string
  label: string
  saved: boolean
  sizeBytes: number
  updatedAt: string | number | null
}

export interface TakeoverStatus {
  bookId: string
  sampledReady: boolean
  passes: TakeoverPassSummary[]
  assembledCards: string[]
  reports: string[]
}

export interface TakeoverPassDetail {
  bookId: string
  passName: string
  promptBundle: string
  charCount: number
  saved: boolean
  existingJson: string | Record<string, unknown> | null
}

export interface SaveTakeoverPassResult {
  bookId: string
  passName: string
  savedPath: string
  keys: string[]
  sizeBytes: number
}

export interface GenerateBookReportsResult {
  bookId: string
  assembled: string[]
  reports: string[]
  reportOk: boolean
  reportError?: string
  totalChars: number
}

export interface SavedChapterSummary {
  chapterNo: number
  filename: string
  title: string
  wordCount: number
  charCount: number
  updatedAt: number
}

export interface SavedChapterDetail {
  project: string
  chapterNo: number
  filename: string
  title?: string
  content: string
  wordCount: number
  charCount: number
}

export interface ChapterScore {
  chapterIndex: number
  title: string
  consistency: number
  quality: number
}

export interface BookResults {
  bookId: string
  title: string
  voiceCard: Record<string, unknown>
  structure: Record<string, unknown>
  commercial: Record<string, unknown>
  craftCard: Record<string, unknown>
  chapterScores: ChapterScore[]
  reportIds: string[]
}

export interface ReportItem {
  id: string
  name: string
  kind: 'book' | 'craft'
  bookId: string
  size: number
}

export interface AssetListResult {
  total: number
  items: AssetItem[]
}

// ---------------------------------------------------------------------------
// W16/W17 阶段二：写作（M2）+ 质检（M3）
// ---------------------------------------------------------------------------

export interface WritingProject {
  id: string
  name: string
  readOnly: boolean
  platform?: string
  genre?: string
  targetWords?: number
  summary?: string
}

export interface InjectResult {
  prompt: string
  charCount: number
  injectedKinds: string[]
  meta: { sourceTitle: string; genre: string; savedPath: string | null }
}

export interface WritingAttempt {
  attempt: number
  consistency: number
  quality: number
  consistencyOk: boolean
  qualityOk: boolean
  issues: string[]
  charCount: number
}

export interface WritingTaskState {
  taskId: string
  // cancelled：后端 cancel() 会置这个状态（writing_service 主循环里检查）。
  // 原先类型定义漏了它，前端终态判定也随之漏掉，于是取消后一直转圈。
  status: 'pending' | 'running' | 'scoring' | 'rewriting' | 'done' | 'degraded' | 'error' | 'cancelled'
  mode: 'llm' | 'no_model'
  chapterNo: number
  attempt?: number
  score?: number | null
  qualityScore?: number | null
  targetScore: number
  passLine: number
  chapterPath?: string | null
  message?: string
  attempts: WritingAttempt[]
  error?: string | null
  // 降级模式额外字段
  prompt?: string
  guideMarkdown?: string
  guidePath?: string
  notice?: string
}

export interface ConsistencyResult {
  score: number
  dims: { voice: number; emotion: number; narration: number; banned: number; imagery: number }
  details: string[]
  radar?: {
    indicators: { name: string; max: number }[]
    series: { name: string; value: number[] }[]
  }
}

export interface QualityCheckResult {
  score: number
  maxScore: number
  verdict: string
  details: string[]
  issues: string[]
}

export interface ScoreResult {
  consistency: ConsistencyResult
  quality: QualityCheckResult
  verdict: string
  passLine: number
}

// 这些是**运行时**键名（deepToCamel 之后），不是后端源码里的 snake_case。
export interface ImportChapterResult {
  chapterPath: string
  chapterNo: number
  title?: string
  charCount: number
  overwrote: boolean
  consistencyScore?: number
  qualityScore?: number
  qualityVerdict?: string
  passLine?: number
}

export interface QcIssue {
  type: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  chapter?: number
  detail: string
}

export interface QcDimension {
  key: string
  label: string
  layer: string
  score: number
  issues: QcIssue[]
  /** 引擎原始数据（部分维度含 perChapter：章号 → 原始小分） */
  raw?: Record<string, unknown>
}

export interface QcLayer {
  layer: string
  label: string
  score: number
  dimensions: QcDimension[]
}

export interface QualityTaskState {
  taskId: string
  status: 'pending' | 'running' | 'done' | 'error'
  phase: string
  target: string
  verdict: string | null
  totalScore: number | null
  layers: QcLayer[]
  issues: QcIssue[]
  totalIssues?: number
  issuesTruncated?: boolean
  issuesLimit?: number
  meta: Record<string, unknown>
  reportJson: string | null
  reportMd: string | null
  error: string | null
}

export interface QcReportItem {
  name: string
  path: string
  verdict: string
  totalScore: number | null
  createdAt: string | null
}

/** 桥段库条目（后端 /api/tropes，直读 assets/trope-library.json）。 */
export interface TropeSkeleton {
  setup: string
  escalation: string[]
  payoff: string
  aftermath: string
}

export interface TropeParameter {
  name: string
  options: string[]
}

export interface Trope {
  id: string
  name: string
  category: string
  /** 后端 genre_scope，经 deepToCamel 转换 */
  genreScope: string
  /** 后端 applicable_genres，经 deepToCamel 转换 */
  applicableGenres: string[]
  skeleton: TropeSkeleton
  /** 后端 abstraction_level，经 deepToCamel 转换 */
  abstractionLevel: string
  parameters: TropeParameter[]
  effectiveness: string
  variations: string[]
  /** 后端 common_failures，经 deepToCamel 转换 */
  commonFailures: string[]
}

export interface TropeListResult {
  /** 运行时键名是 totalCount（后端源码写 total_count，client.ts 已转 camelCase）。
   *  2026-09-30 修过前端误读 totalCount 导致数量徽标恒为 0 的 bug。 */
  totalCount: number
  tropes: Trope[]
}
