// 分析进度面板：总进度条 + 错误/离线接管诊断 + Pass 1–5 Web-AI 接管工作台 + 章×批状态矩阵。
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import LinearProgress from '@mui/material/LinearProgress'
import Tooltip from '@mui/material/Tooltip'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import Chip from '@mui/material/Chip'
import TextField from '@mui/material/TextField'
import MenuItem from '@mui/material/MenuItem'
import Divider from '@mui/material/Divider'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import CircularProgress from '@mui/material/CircularProgress'
import { useApp } from '../state/AppContext'
import { useI18n } from '../state/I18nContext'
import * as clientMod from '../api/client'
import { friendlyError } from '../api/client'
import type {
  GenerateBookReportsResult,
  OfflineAnalysisResult,
  SaveTakeoverPassResult,
  TakeoverPassDetail,
  TakeoverPassSummary,
  TakeoverStatus,
} from '../types'
import { palette } from '../theme'

const STATUS_I18N_KEYS: Record<string, string> = {
  idle: 'analysis_status_idle',
  pending: 'analysis_status_pending',
  running: 'analysis_status_running',
  paused: 'analysis_status_paused',
  done: 'analysis_status_done',
  error: 'analysis_status_error',
  partial: 'analysis_status_partial',
  success: 'analysis_status_success',
  failed: 'analysis_status_failed',
  skipped: 'analysis_status_skipped',
}

// 批次状态语义色：取自 theme.ts 统一色板；pending 用中性灰（无主题角色，保留）。
const CELL_COLOR: Record<string, string> = {
  pending: '#e0e0e0',
  running: palette.primary,
  success: palette.success,
  failed: palette.error,
  skipped: palette.warning,
}

const DEFAULT_TAKEOVER_PASSES: TakeoverPassSummary[] = [
  { passName: 'pass1_structure', label: 'Pass 1 · 结构与节拍', saved: false, sizeBytes: 0, updatedAt: null },
  { passName: 'pass2_character', label: 'Pass 2 · 人物与声线', saved: false, sizeBytes: 0, updatedAt: null },
  { passName: 'pass3_style', label: 'Pass 3 · 文风与语言', saved: false, sizeBytes: 0, updatedAt: null },
  { passName: 'pass4_commercial', label: 'Pass 4 · 商业与爽点', saved: false, sizeBytes: 0, updatedAt: null },
  { passName: 'pass5_craft', label: 'Pass 5 · 技法与笔法', saved: false, sizeBytes: 0, updatedAt: null },
]

function getClientFn<T extends (...args: any[]) => any>(name: string): T | undefined {
  try {
    const fn = (clientMod as Record<string, unknown>)[name]
    return typeof fn === 'function' ? (fn as T) : undefined
  } catch {
    return undefined
  }
}

export interface ProgressPanelProps {
  offlineTriggerNonce?: number
  genre?: string
  onGoResult?: () => void
}

export default function ProgressPanel({
  offlineTriggerNonce = 0,
  genre: externalGenre = '',
  onGoResult,
}: ProgressPanelProps = {}) {
  const { t, locale } = useI18n()
  const { book, batchStates, status, loadBookResults, refreshOverview } = useApp()

  const [offlineBusy, setOfflineBusy] = useState(false)
  const [offlineErr, setOfflineErr] = useState('')
  const [offlineData, setOfflineData] = useState<OfflineAnalysisResult | null>(null)
  const [copied, setCopied] = useState(false)

  // Web-AI Takeover Pass 1-5 工作台状态
  const [takeoverStatus, setTakeoverStatus] = useState<TakeoverStatus | null>(null)
  const [takeoverOpen, setTakeoverOpen] = useState(false)
  const [selectedPass, setSelectedPass] = useState<string>('pass1_structure')
  const [bundleLoading, setBundleLoading] = useState(false)
  const [passDetail, setPassDetail] = useState<TakeoverPassDetail | null>(null)
  const [copiedBundleChars, setCopiedBundleChars] = useState<number | null>(null)
  const [bundlePreviewOpen, setBundlePreviewOpen] = useState(false)
  const [replyText, setReplyText] = useState('')
  const [savingPass, setSavingPass] = useState(false)
  const [passSaveInfo, setPassSaveInfo] = useState<SaveTakeoverPassResult | null>(null)
  const [finalizing, setFinalizing] = useState(false)
  const [finalizeResult, setFinalizeResult] = useState<GenerateBookReportsResult | null>(null)
  const [genres, setGenres] = useState<string[]>([])
  const [finalizeGenre, setFinalizeGenre] = useState<string>(externalGenre || '')
  const [prevExtGenre, setPrevExtGenre] = useState<string>(externalGenre)

  if (externalGenre !== prevExtGenre) {
    setPrevExtGenre(externalGenre)
    if (externalGenre) {
      setFinalizeGenre(externalGenre)
    }
  }

  const lastHandledNonceRef = useRef<number>(0)

  const refreshTakeoverStatus = useCallback(async (bid: string) => {
    const getStatusFn = getClientFn<(id: string) => Promise<TakeoverStatus>>('getTakeoverStatus')
    if (!bid || !getStatusFn) return null
    try {
      const st = await getStatusFn(bid)
      setTakeoverStatus(st)
      return st
    } catch {
      return null
    }
  }, [])

  // 挂载或切书时：重置上一本书的接管缓存，拉取题材字典与当前书的接管状态
  useEffect(() => {
    setOfflineData(null)
    setTakeoverStatus(null)
    setPassDetail(null)
    setCopiedBundleChars(null)
    setPassSaveInfo(null)
    setFinalizeResult(null)
    setReplyText('')
    if (!book?.bookId) return

    let cancelled = false
    const getStatusFn = getClientFn<(id: string) => Promise<TakeoverStatus>>('getTakeoverStatus')
    if (getStatusFn) {
      getStatusFn(book.bookId)
        .then((st) => {
          if (!cancelled && st) setTakeoverStatus(st)
        })
        .catch(() => {})
    }

    const getGenresFn =
      getClientFn<() => Promise<string[]>>('listGenres')
      ?? getClientFn<() => Promise<string[]>>('getGenres')
    if (getGenresFn) {
      getGenresFn()
        .then((list) => {
          if (!cancelled && Array.isArray(list)) setGenres(list)
        })
        .catch(() => {})
    }

    return () => {
      cancelled = true
    }
  }, [book?.bookId])

  const handleOffline = useCallback(async (targetGenre?: string) => {
    const runOfflineFn = getClientFn<(id: string, g?: string) => Promise<OfflineAnalysisResult>>('runOfflineAnalysis')
    if (!book?.bookId) return
    setTakeoverOpen(true)
    if (!runOfflineFn) return
    const effectiveGenre = targetGenre || externalGenre || finalizeGenre || 'unknown'
    setOfflineBusy(true)
    setOfflineErr('')
    setCopied(false)
    try {
      const res = await runOfflineFn(book.bookId, effectiveGenre)
      setOfflineData(res)
      if (res.genre && res.genre !== 'unknown' && !finalizeGenre) {
        setFinalizeGenre(res.genre)
      }
      await refreshTakeoverStatus(book.bookId)
    } catch (e) {
      setOfflineErr(friendlyError(e))
    } finally {
      setOfflineBusy(false)
    }
  }, [book?.bookId, externalGenre, finalizeGenre, refreshTakeoverStatus])

  // 响应顶栏控制条传来的 offlineTriggerNonce（彻底修复首次切换挂载丢事件缺陷）
  useEffect(() => {
    if (offlineTriggerNonce > 0 && offlineTriggerNonce !== lastHandledNonceRef.current && book?.bookId) {
      lastHandledNonceRef.current = offlineTriggerNonce
      void handleOffline(externalGenre || 'unknown')
    }
  }, [offlineTriggerNonce, book?.bookId, externalGenre, handleOffline])

  // 兼容外部自定义事件触发
  useEffect(() => {
    const onOffline = (e: Event) => {
      const g = (e as CustomEvent<{ genre?: string }>).detail?.genre || externalGenre || 'unknown'
      void handleOffline(g)
    }
    window.addEventListener('novellab:run-offline-analysis', onOffline)
    return () => window.removeEventListener('novellab:run-offline-analysis', onOffline)
  }, [handleOffline, externalGenre])

  const handleCopyPassBundle = async () => {
    const getPassFn = getClientFn<(id: string, p: string) => Promise<TakeoverPassDetail>>('getTakeoverPass')
    if (!book?.bookId || !getPassFn || bundleLoading) return
    setBundleLoading(true)
    setOfflineErr('')
    setCopiedBundleChars(null)
    try {
      const detail = await getPassFn(book.bookId, selectedPass)
      setPassDetail(detail)
      const text = detail.promptBundle || ''
      let clipOk = false
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        try {
          await navigator.clipboard.writeText(text)
          clipOk = true
        } catch {
          clipOk = false
        }
      }
      if (clipOk) {
        setCopiedBundleChars(detail.charCount || text.length)
      } else {
        setBundlePreviewOpen(true)
      }
    } catch (e) {
      setOfflineErr(friendlyError(e))
    } finally {
      setBundleLoading(false)
    }
  }

  const handleSavePassReply = async () => {
    const savePassFn = getClientFn<(id: string, p: string, c: string) => Promise<SaveTakeoverPassResult>>('saveTakeoverPass')
    if (!book?.bookId || !savePassFn || !replyText.trim() || savingPass) return
    setSavingPass(true)
    setOfflineErr('')
    setPassSaveInfo(null)
    try {
      const res = await saveTakeoverPassCompat(savePassFn, book.bookId, selectedPass, replyText)
      setPassSaveInfo(res)
      setReplyText('')
      const updated = await refreshTakeoverStatus(book.bookId)
      const list = updated?.passes?.length ? updated.passes : DEFAULT_TAKEOVER_PASSES
      const nextUnsaved = list.find((p) => p.passName !== selectedPass && !p.saved)
      if (nextUnsaved) {
        setSelectedPass(nextUnsaved.passName)
        setCopiedBundleChars(null)
      }
    } catch (e) {
      setOfflineErr(friendlyError(e))
    } finally {
      setSavingPass(false)
    }
  }

  const handleFinalizeReports = async () => {
    const genReportsFn = getClientFn<
      (id: string, opts?: { genre?: string; assemble?: boolean }) => Promise<GenerateBookReportsResult>
    >('generateBookReports')
    if (!book?.bookId || !genReportsFn || finalizing) return
    setFinalizing(true)
    setOfflineErr('')
    setFinalizeResult(null)
    try {
      const chosenGenre = finalizeGenre || externalGenre || offlineData?.genre || 'unknown'
      const res = await genReportsFn(book.bookId, { genre: chosenGenre, assemble: true })
      setFinalizeResult(res)
      await Promise.allSettled([
        loadBookResults?.(book.bookId),
        refreshOverview?.(),
        refreshTakeoverStatus(book.bookId),
      ])
    } catch (e) {
      setOfflineErr(friendlyError(e))
    } finally {
      setFinalizing(false)
    }
  }

  const { done, total } = useMemo(() => {
    if (!book) return { done: 0, total: 0 }
    let d = 0
    let tCount = 0
    for (const ch of book.chapters) {
      tCount += ch.batchCount
      for (let bi = 0; bi < ch.batchCount; bi++) {
        const st = batchStates[`c${ch.index}-b${bi}`]?.status
        if (st === 'success') d++
      }
    }
    return { done: d, total: tCount }
  }, [book, batchStates])

  const pct = total > 0 ? Math.round((done / total) * 100) : 0

  if (!book) {
    return (
      <Box sx={{ p: 3, textAlign: 'center' }}>
        <Typography color="text.secondary">{t('analysis_need_book')}</Typography>
      </Box>
    )
  }

  const currentStatusLabel = t(STATUS_I18N_KEYS[status?.status ?? 'idle'] ?? 'analysis_status_idle')
  const passes = takeoverStatus?.passes?.length ? takeoverStatus.passes : DEFAULT_TAKEOVER_PASSES
  const showTakeoverWorkbench = Boolean(offlineData || takeoverStatus?.sampledReady || takeoverOpen)
  const savedPassCount = passes.filter((p) => p.saved).length

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1, mb: 1 }}>
        <Typography variant="h6">
          {t('analysis_prog_title')}
        </Typography>
        <Button
          size="small"
          variant="outlined"
          disabled={offlineBusy}
          onClick={() => void handleOffline()}
          startIcon={offlineBusy ? <CircularProgress size={14} /> : undefined}
        >
          {t('analysis_offline_run_btn', '运行离线量化拆解 & AI 接管工作台')}
        </Button>
      </Box>

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
        <Box sx={{ flex: 1 }}>
          <LinearProgress variant="determinate" value={pct} sx={{ height: 10, borderRadius: 5 }} />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'nowrap' }}>
          {done} / {total} {t('analysis_batches_unit')} · {pct}%
        </Typography>
      </Box>
      <Typography variant="caption" color="text.secondary">
        {t('analysis_prog_status_current')}：{currentStatusLabel} · {t('analysis_prog_checkpoint')} {status?.cursor || '-'}
      </Typography>

      {status?.lastError && (
        <Alert
          severity="error"
          sx={{ mt: 2 }}
          action={
            <Button color="inherit" size="small" disabled={offlineBusy} onClick={() => void handleOffline()}>
              {offlineBusy ? <CircularProgress size={14} /> : t('analysis_btn_offline', '离线量化拆解 & 接管包')}
            </Button>
          }
        >
          {friendlyError(status.lastError)}
          {status.takeoverGuidePath ? `\n已自动生成离线接管清单：${status.takeoverGuidePath}` : ''}
        </Alert>
      )}

      {status?.reportError && (
        <Alert severity="warning" sx={{ mt: 1.5 }}>
          {status.reportError}
        </Alert>
      )}

      {offlineErr && (
        <Alert severity="error" sx={{ mt: 1.5 }} onClose={() => setOfflineErr('')}>
          {offlineErr}
        </Alert>
      )}

      {offlineData && (
        <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, flexWrap: 'wrap', gap: 1 }}>
            <Typography variant="subtitle2" fontWeight={700}>
              {t('analysis_offline_done_title', '离线量化拆解与 AI 接管任务包已就绪')}
            </Typography>
            <Button
              size="small"
              variant="contained"
              onClick={() => {
                if (navigator?.clipboard?.writeText) {
                  void navigator.clipboard.writeText(offlineData.guideMarkdown)
                }
                setCopied(true)
              }}
            >
              {copied ? '已复制 ✓' : t('analysis_copy_guide', '复制 AI 接管指令包')}
            </Button>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            全书 {offlineData.totalChapters} 章 · 分层采样 {offlineData.selectedCount} 章（{offlineData.sampleWords.toLocaleString()} 字）
            {' · '}平均句长 {String(offlineData.metrics?.avgSentenceLen ?? offlineData.metrics?.avg_sentence_len ?? '-')}
            {' · '}对白占比 {String(offlineData.metrics?.dialogueRatio ?? offlineData.metrics?.dialogue_ratio ?? '-')}
            {' · '}词汇丰富度 TTR {String(offlineData.metrics?.charTtr ?? offlineData.metrics?.char_ttr ?? '-')}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            落盘路径：{offlineData.guidePath}
          </Typography>
          <Box sx={{ maxHeight: 180, overflow: 'auto', bgcolor: 'action.hover', p: 1.5, borderRadius: 1 }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>{offlineData.guideMarkdown}</pre>
          </Box>
        </Paper>
      )}

      {/* 交互式 Pass 1–5 Web-AI 接管工作台 */}
      {showTakeoverWorkbench && (
        <Paper variant="outlined" sx={{ p: 2.5, mt: 2, display: 'flex', flexDirection: 'column', gap: 2 }} data-testid="takeover-workbench">
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
            <Typography variant="subtitle1" fontWeight={700}>
              {t('analysis_offline_workbench_title', 'Web-AI 离线接管拆书工作台（Pass 1–5）')}
            </Typography>
            <Chip
              size="small"
              color={savedPassCount >= 5 ? 'success' : 'primary'}
              label={`${savedPassCount} / ${passes.length} Pass`}
            />
          </Box>

          {/* Step 1: 选择 Pass */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t('analysis_takeover_step1_title', '第一步：选择拆书阶段（Pass 1–5）')}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
              {passes.map((p) => {
                const active = p.passName === selectedPass
                const badge = p.saved
                  ? t('analysis_takeover_pass_saved', '✓ 已入库')
                  : t('analysis_takeover_pass_pending', '待完成')
                return (
                  <Button
                    key={p.passName}
                    size="small"
                    variant={active ? 'contained' : 'outlined'}
                    color={p.saved ? 'success' : 'primary'}
                    onClick={() => {
                      setSelectedPass(p.passName)
                      setCopiedBundleChars(null)
                      setPassSaveInfo(null)
                    }}
                    data-testid={`takeover-pass-${p.passName}`}
                  >
                    {`${p.label || p.passName} (${badge})`}
                  </Button>
                )
              })}
            </Box>
          </Box>

          <Divider />

          {/* Step 2: 一键复制本 Pass 完整投喂包 */}
          <Box>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              {t('analysis_takeover_step2_title', '第二步：复制本 Pass 完整投喂包（Prompt + 分层采样切片）')}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Button
                variant="contained"
                size="small"
                disabled={bundleLoading}
                onClick={() => void handleCopyPassBundle()}
                startIcon={bundleLoading ? <CircularProgress size={14} color="inherit" /> : undefined}
              >
                {t('analysis_takeover_copy_bundle_btn', '复制本 Pass 完整投喂包')}
              </Button>
              {passDetail?.promptBundle && (
                <Button size="small" variant="text" onClick={() => setBundlePreviewOpen(true)}>
                  {locale === 'en-US' ? 'Preview Bundle' : '查看投喂包原文'}
                </Button>
              )}
              {copiedBundleChars != null && (
                <Typography variant="caption" color="success.main" fontWeight={600}>
                  {t('analysis_takeover_copied_bundle', '已复制本 Pass 投喂包（{chars} 字）✓', {
                    chars: copiedBundleChars.toLocaleString(),
                  })}
                </Typography>
              )}
            </Box>
          </Box>

          <Divider />

          {/* Step 3: 粘贴 AI 回复并保存本 Pass JSON */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Typography variant="subtitle2">
              {t('analysis_takeover_step3_title', '第三步：粘贴 Web-AI 回复并保存本 Pass JSON')}
            </Typography>
            <TextField
              multiline
              rows={5}
              fullWidth
              size="small"
              value={replyText}
              onChange={(e) => setReplyText(e.target.value)}
              placeholder={t(
                'analysis_takeover_paste_placeholder',
                '将任意网页版 AI（ChatGPT / Claude / DeepSeek / 豆包等）返回的 JSON 或 ```json ... ``` 代码块直接粘贴到这里……',
              )}
              InputProps={{ style: { fontFamily: 'monospace', fontSize: 12 } }}
            />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              <Button
                variant="outlined"
                size="small"
                disabled={!replyText.trim() || savingPass}
                onClick={() => void handleSavePassReply()}
                startIcon={savingPass ? <CircularProgress size={14} /> : undefined}
              >
                {t('analysis_takeover_save_pass_btn', '保存本 Pass JSON')}
              </Button>
              {passSaveInfo && (
                <Alert severity="success" sx={{ py: 0 }}>
                  {t('analysis_takeover_pass_save_ok', '已保存 {passName}（字段数：{count}）', {
                    passName: passSaveInfo.passName,
                    count: passSaveInfo.keys?.length ?? 0,
                  })}
                </Alert>
              )}
            </Box>
          </Box>

          <Divider />

          {/* Step 4: 一键组装四维资产并生成万字双报告 */}
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
            <Typography variant="subtitle2">
              {t('analysis_takeover_step4_title', '第四步：组装四维资产并生成万字双报告')}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap' }}>
              {genres.length > 0 ? (
                <TextField
                  select
                  size="small"
                  label={t('analysis_genre_label')}
                  value={finalizeGenre}
                  onChange={(e) => setFinalizeGenre(e.target.value)}
                  sx={{ minWidth: 180 }}
                >
                  {genres.map((g) => (
                    <MenuItem key={g} value={g}>{g}</MenuItem>
                  ))}
                  {finalizeGenre && !genres.includes(finalizeGenre) && (
                    <MenuItem value={finalizeGenre}>{finalizeGenre}</MenuItem>
                  )}
                  {!genres.includes('unknown') && (
                    <MenuItem value="unknown">unknown</MenuItem>
                  )}
                </TextField>
              ) : (
                <TextField
                  size="small"
                  label={t('analysis_genre_label')}
                  value={finalizeGenre}
                  onChange={(e) => setFinalizeGenre(e.target.value)}
                  placeholder="xianxia / unknown"
                  sx={{ minWidth: 180 }}
                />
              )}
              <Button
                variant="contained"
                color="success"
                size="small"
                disabled={finalizing}
                onClick={() => void handleFinalizeReports()}
                startIcon={finalizing ? <CircularProgress size={14} color="inherit" /> : undefined}
              >
                {t('analysis_takeover_finalize_btn', '一键组装四维资产并生成万字双报告')}
              </Button>
              {finalizeResult && onGoResult && (
                <Button size="small" variant="outlined" onClick={onGoResult}>
                  {t('analysis_tab_result')}
                </Button>
              )}
            </Box>

            {finalizeResult && (
              <Alert severity={finalizeResult.reportOk === false ? 'warning' : 'success'}>
                <Typography variant="body2" fontWeight={600}>
                  {t('analysis_takeover_finalize_ok', '已组装 {assets} 张资产卡，生成 {reports} 份报告（共 {chars} 字）', {
                    assets: finalizeResult.assembled?.length ?? 0,
                    reports: finalizeResult.reports?.length ?? 0,
                    chars: (finalizeResult.totalChars ?? 0).toLocaleString(),
                  })}
                </Typography>
                {finalizeResult.assembled?.length > 0 && (
                  <Typography variant="caption" display="block">
                    {finalizeResult.assembled.join(' · ')}
                  </Typography>
                )}
                {finalizeResult.reportError && (
                  <Typography variant="caption" color="warning.main" display="block">
                    {finalizeResult.reportError}
                  </Typography>
                )}
              </Alert>
            )}
          </Box>
        </Paper>
      )}

      {/* 剪贴板不可用时的手动复制兜底弹窗 / 预览弹窗 */}
      <Dialog open={bundlePreviewOpen} onClose={() => setBundlePreviewOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{selectedPass}</DialogTitle>
        <DialogContent>
          <TextField
            multiline
            rows={14}
            fullWidth
            value={passDetail?.promptBundle ?? ''}
            InputProps={{ readOnly: true, style: { fontFamily: 'monospace', fontSize: 12 } }}
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBundlePreviewOpen(false)}>{t('action_close', '关闭')}</Button>
        </DialogActions>
      </Dialog>

      {/* 章×批矩阵 */}
      <Box sx={{ mt: 3 }}>
        {book.chapters.map((ch) => {
          const cols = Math.max(ch.batchCount, 1)
          return (
            <Box key={ch.index} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography variant="caption" noWrap sx={{ width: 140, flexShrink: 0 }}>
                {t('analysis_chap_prefix')}{ch.index}{t('analysis_chap_suffix')}
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: '3px' }}>
                {Array.from({ length: cols }).map((_, bi) => {
                  const key = `c${ch.index}-b${bi}`
                  const st = batchStates[key]?.status ?? 'pending'
                  const statusLabel = t(STATUS_I18N_KEYS[st] ?? 'analysis_status_pending')
                  const tooltipText = locale === 'en-US'
                    ? `Ch.${ch.index} Batch ${bi} · ${statusLabel}`
                    : `第${ch.index}章 第${bi}批 · ${statusLabel}`
                  return (
                    <Tooltip key={bi} title={tooltipText}>
                      <Box
                        sx={{
                          width: 14,
                          height: 14,
                          borderRadius: '3px',
                          bgcolor: (theme) =>
                            st === 'pending' && theme.palette.mode === 'dark'
                              ? 'rgba(255,255,255,0.16)'
                              : (CELL_COLOR[st] ?? CELL_COLOR.pending),
                        }}
                      />
                    </Tooltip>
                  )
                })}
              </Box>
            </Box>
          )
        })}
      </Box>

      {/* 图例 */}
      <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
        {(['pending', 'running', 'success', 'failed', 'skipped'] as const).map((s) => (
          <Box key={s} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box
              sx={{
                width: 12,
                height: 12,
                borderRadius: '3px',
                bgcolor: (theme) =>
                  s === 'pending' && theme.palette.mode === 'dark' ? 'rgba(255,255,255,0.16)' : CELL_COLOR[s],
              }}
            />
            <Typography variant="caption" color="text.secondary">
              {t(STATUS_I18N_KEYS[s] ?? s)}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  )
}

async function saveTakeoverPassCompat(
  fn: (id: string, p: string, c: string) => Promise<SaveTakeoverPassResult>,
  bookId: string,
  passName: string,
  content: string,
): Promise<SaveTakeoverPassResult> {
  return fn(bookId, passName, content)
}
