// 首启引导向导 v2 — 4 步，可重播，感知模型是否已配置。
// 触发条件：空库 && 未标记过 onboarded（v2 键为准，自动迁移 v1 旧键）。
import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import Alert from '@mui/material/Alert'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Dialog from '@mui/material/Dialog'
import DialogActions from '@mui/material/DialogActions'
import DialogContent from '@mui/material/DialogContent'
import DialogTitle from '@mui/material/DialogTitle'
import MobileStepper from '@mui/material/MobileStepper'
import Typography from '@mui/material/Typography'
import Grid from '@mui/material/Grid'
import type { WorkbenchKey } from '../layout/WorkbenchNav'
import { readStorage, writeStorage } from '../safeStorage'
import { useI18n } from '../state/I18nContext'
import { ink } from '../ink'

export const STORAGE_KEY_V2 = 'novellab.onboarded.v2'
const STORAGE_KEY_V1 = 'novellab.onboarded'

export interface OnboardState {
  done: boolean
  dismissedAt: number
}

function parseV2(): OnboardState | null {
  const raw = readStorage(STORAGE_KEY_V2)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as OnboardState
    if (parsed && parsed.done === true && typeof parsed.dismissedAt === 'number') return parsed
    return null
  } catch {
    return null
  }
}

export function isOnboarded(): boolean {
  const v2 = parseV2()
  if (v2?.done) return true
  // 迁移：旧键存在则写入新键并认为已完成
  if (readStorage(STORAGE_KEY_V1) === '1') {
    writeStorage(STORAGE_KEY_V2, JSON.stringify({ done: true, dismissedAt: Date.now() } satisfies OnboardState))
    return true
  }
  return false
}

/** 供 AppShell 监听：重播引导（清 v2 键并触发重渲染的事件）。 */
export const REPLAY_EVENT = 'novellab:replay-onboarding'
export function replayOnboarding(): void {
  writeStorage(STORAGE_KEY_V2, JSON.stringify({ done: false, dismissedAt: 0 } satisfies OnboardState))
  // 使用 Storage 的值已改，但同页 isOnboarded 读的是内存；用自定义事件让 AppShell 重置 onboarded 状态
  try { window.dispatchEvent(new CustomEvent(REPLAY_EVENT)) } catch { /* noop in tests without window */ }
}

interface Step {
  title: string
  body: ReactNode
  cta: { label: string; go?: WorkbenchKey }
  /** 为未配模型时提供的替代 CTA（仅 step 2 使用） */
  altCta?: { label: string; go: WorkbenchKey; hint: string }
}

type NextAction = { key: WorkbenchKey; title: string; desc: string; accent: string }

export default function OnboardingWizard({
  onDone,
  onNavigate,
  modelConfigured,
}: {
  onDone: () => void
  onNavigate: (k: WorkbenchKey) => void
  modelConfigured?: boolean
}) {
  const { t } = useI18n()
  const [step, setStep] = useState(0)

  const finish = (go?: WorkbenchKey | unknown) => {
    const target = typeof go === 'string' ? (go as WorkbenchKey) : undefined
    writeStorage(STORAGE_KEY_V2, JSON.stringify({ done: true, dismissedAt: Date.now() } satisfies OnboardState))
    onDone()
    if (target) onNavigate(target)
  }

  const nextActions: NextAction[] = useMemo(() => [
    { key: 'analysis', title: t('onboarding_s4_action_analysis', '拆一本书'), desc: t('onboarding_s4_action_analysis_desc', '选一本 TXT 一键拆解'), accent: ink.cinnabar },
    { key: 'assets', title: t('onboarding_s4_action_assets', '逛资产库'), desc: t('onboarding_s4_action_assets_desc', '看示例资产长什么样'), accent: ink.teal },
    { key: 'writing', title: t('onboarding_s4_action_writing', '写一章'), desc: t('onboarding_s4_action_writing_desc', '用示例资产试写'), accent: ink.gold },
  ], [t])

  const steps = useMemo<Step[]>(
    () => [
      {
        title: t('onboarding_s1_title', '欢迎使用暮冬念春'),
        body: (
          <Typography variant="body2" color="text.secondary">
            {t('onboarding_s1_body', '把优秀小说拆成可复用的写作资产，再用这些资产驱动创作。全流程在本机完成，不会上传任何数据。三步上手，随时可跳过。')}
          </Typography>
        ),
        cta: { label: t('onboarding_next', '下一步') },
      },
      {
        title: t('onboarding_s2_title', '第一步：导入并拆书'),
        body: modelConfigured === false ? (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {t('onboarding_s2_body', '到「分析」页导入一本 TXT 全本，选择题材后启动拆书。拆解完成后自动生成文风卡、笔法卡、结构/商业观测等资产与万字分析报告。')}
            </Typography>
            <Alert severity="info" sx={{ borderRadius: 2, fontSize: 13 }}>
              {t('onboarding_s2_model_hint', '配好模型才能拆书，也可先用示例语料体验离线功能')}
            </Alert>
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            {t('onboarding_s2_body', '到「分析」页导入一本 TXT 全本，选择题材后启动拆书。拆解完成后自动生成文风卡、笔法卡、结构/商业观测等资产与万字分析报告。')}
          </Typography>
        ),
        cta: { label: t('onboarding_goto_import', '去导入'), go: 'analysis' as WorkbenchKey },
        altCta: modelConfigured === false ? {
          label: t('onboarding_goto_model', '去配置模型'),
          go: 'system' as WorkbenchKey,
          hint: t('onboarding_s2_model_hint', '配好模型才能拆书，也可先用示例语料体验离线功能'),
        } : undefined,
      },
      {
        title: t('onboarding_s3_title', '第二步：查看资产与质检'),
        body: (
          <Typography variant="body2" color="text.secondary">
            {t('onboarding_s3_body', '「资产库」浏览全部结构化资产；「质检」页可对任意章节跑 12 维质量检查与全书质检；「写作」页用资产注入辅助生成新章节。')}
          </Typography>
        ),
        cta: { label: t('onboarding_next', '下一步') },
      },
      {
        title: t('onboarding_s4_title', '下一步做什么'),
        body: (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              {t('onboarding_s4_body', '挑一个开始，边用边熟悉：')}
            </Typography>
            <Grid container spacing={1.5}>
              {nextActions.map((a) => (
                <Grid item xs={12} sm={4} key={a.key}>
                  <Card
                    variant="outlined"
                    onClick={() => finish(a.key)}
                    data-testid={`onboarding-action-${a.key}`}
                    sx={{
                      cursor: 'pointer',
                      borderLeft: `3px solid ${a.accent}`,
                      transition: 'transform 0.15s, box-shadow 0.15s',
                      '&:hover': { transform: 'translateY(-2px)', boxShadow: '0 6px 18px rgba(16,16,20,0.08)' },
                    }}
                  >
                    <CardContent sx={{ p: 1.75, '&:last-child': { pb: 1.75 } }}>
                      <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.25 }}>{a.title}</Typography>
                      <Typography variant="caption" color="text.secondary">{a.desc}</Typography>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>
        ),
        cta: { label: t('onboarding_get_started', '开始使用') },
      },
    ],
    [t, modelConfigured, nextActions],
  )

  const current = steps[step]
  const isLast = step === steps.length - 1
  // 未配模型时，第二步主按钮改为去配模型
  const effectiveCta = step === 1 && current.altCta ? current.altCta : current.cta

  return (
    <Dialog open onClose={() => finish()} maxWidth="sm" fullWidth data-testid="onboarding">
      <DialogTitle sx={{ fontWeight: 600 }}>{current.title}</DialogTitle>
      <DialogContent>
        <Box sx={{ minHeight: 108, display: 'flex', alignItems: 'center' }}>{current.body}</Box>
        <MobileStepper
          variant="dots"
          steps={steps.length}
          position="static"
          activeStep={step}
          sx={{ bgcolor: 'transparent', pl: 0 }}
          nextButton={null}
          backButton={null}
        />
      </DialogContent>
      <DialogActions sx={{ flexWrap: 'wrap', gap: 0.5 }}>
        <Button size="small" color="inherit" onClick={() => finish()}>
          {t('onboarding_skip', '跳过')}
        </Button>
        {step > 0 && (
          <Button size="small" onClick={() => setStep((s) => s - 1)}>
            {t('onboarding_prev', '上一步')}
          </Button>
        )}
        {/* 未配模型时在第二步额外展示次要去向 */}
        {step === 1 && current.altCta && (
          <Button size="small" variant="outlined" onClick={() => finish(current.altCta!.go)} data-testid="onboarding-alt-cta">
            {current.altCta.label}
          </Button>
        )}
        <Button
          variant="contained"
          size="small"
          data-testid="onboarding-primary-cta"
          onClick={() => (isLast ? finish(effectiveCta.go) : (step === 1 ? finish(effectiveCta.go) : setStep((s) => s + 1)))}
        >
          {isLast ? current.cta.label : (step === 1 ? effectiveCta.label : current.cta.label)}
        </Button>
      </DialogActions>
    </Dialog>
  )
}
