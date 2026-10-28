// 共享旅程定义：供 HomeDashboard.JourneyStepper 与 HelpWorkbench.StartPanel 复用。
// WS-A4：三步闭环旅程 — 配置模型 → 拆一本书 → 写一章并质检
import type { Locale } from '../i18n/translations'
import type { WorkbenchKey } from '../layout/WorkbenchNav'
import type { Overview } from '../types'

export type JourneyStatus = 'done' | 'active' | 'pending'

export interface JourneyDefinition {
  key: string
  index: number
  title: Record<Locale, string>
  description: Record<Locale, string>
  workbench: WorkbenchKey
}

/**
 * 三步旅程静态定义（顺序固定，不含状态）。
 * 共享给 HomeDashboard 与 HelpWorkbench，避免两处文案漂移。
 */
export const JOURNEY_DEFINITIONS: JourneyDefinition[] = [
  {
    key: 'model',
    index: 0,
    title: { 'zh-CN': '配置模型', 'en-US': 'Configure Model' },
    description: { 'zh-CN': '连接外部 AI 模型', 'en-US': 'Connect an AI model' },
    workbench: 'system',
  },
  {
    key: 'analyze',
    index: 1,
    title: { 'zh-CN': '拆一本书', 'en-US': 'Analyze a Book' },
    description: { 'zh-CN': '导入 TXT 一键拆解', 'en-US': 'Import TXT & deconstruct' },
    workbench: 'analysis',
  },
  {
    key: 'write_qc',
    index: 2,
    title: { 'zh-CN': '写一章并质检', 'en-US': 'Write & QC' },
    description: { 'zh-CN': '在创作室写作并一键质检', 'en-US': 'Draft in Studio & run QC' },
    workbench: 'writing',
  },
]

/**
 * 根据概览计算每一步的状态。
 * 规则（与任务描述一致 + 对 Step3 补充 active 以避免“永远 pending”）：
 * - Step 1: modelConfigured ? done : pending
 * - Step 2: totalBooks > 0 ? done : (modelConfigured ? active : pending)
 * - Step 3: totalAssets >= 4 && totalBooks > 0 ? done : (totalBooks > 0 ? active : pending)
 *   4 张资产阈值对应拆一本书后的典型产物（声线/结构/笔法/商业）；recentActivity 视为弱信号备选。
 */
export function getJourneyStatuses(overview: Overview | null): JourneyStatus[] {
  if (!overview) return ['pending', 'pending', 'pending']
  const s1: JourneyStatus = overview.modelConfigured ? 'done' : 'pending'
  const s2: JourneyStatus = overview.totalBooks > 0 ? 'done' : (overview.modelConfigured ? 'active' : 'pending')
  const hasRecentActivity = Array.isArray(overview.recentActivity) && overview.recentActivity.length > 0
  const s3Done = (overview.totalAssets >= 4 && overview.totalBooks > 0) || (hasRecentActivity && overview.totalAssets > 0)
  const s3: JourneyStatus = s3Done ? 'done' : (overview.totalBooks > 0 ? 'active' : 'pending')
  return [s1, s2, s3]
}

/**
 * 计算 Stepper 的 activeStep：首个未完成的下标；全部完成则返回 length（全部打勾态）。
 */
export function getJourneyActiveStep(statuses: JourneyStatus[]): number {
  const idx = statuses.findIndex((s) => s !== 'done')
  return idx === -1 ? statuses.length : idx
}
