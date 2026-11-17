// 分析进度面板：总进度条 + 错误/离线接管诊断 + 章×批状态矩阵。
import { useCallback, useEffect, useMemo, useState } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import LinearProgress from '@mui/material/LinearProgress'
import Tooltip from '@mui/material/Tooltip'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import CircularProgress from '@mui/material/CircularProgress'
import { useApp } from '../state/AppContext'
import { useI18n } from '../state/I18nContext'
import { friendlyError, runOfflineAnalysis } from '../api/client'
import type { OfflineAnalysisResult } from '../types'
import { palette } from '../theme'

const STATUS_I18N_KEYS: Record<string, string> = {
  idle: 'analysis_status_idle',
  pending: 'analysis_status_pending',
  running: 'analysis_status_running',
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

export default function ProgressPanel() {
  const { t, locale } = useI18n()
  const { book, batchStates, status } = useApp()
  const [offlineBusy, setOfflineBusy] = useState(false)
  const [offlineErr, setOfflineErr] = useState('')
  const [offlineData, setOfflineData] = useState<OfflineAnalysisResult | null>(null)
  const [copied, setCopied] = useState(false)

  const handleOffline = useCallback(async (genre = 'unknown') => {
    if (!book?.bookId || typeof runOfflineAnalysis !== 'function') return
    setOfflineBusy(true)
    setOfflineErr('')
    setCopied(false)
    try {
      const res = await runOfflineAnalysis(book.bookId, genre)
      setOfflineData(res)
    } catch (e) {
      setOfflineErr(friendlyError(e))
    } finally {
      setOfflineBusy(false)
    }
  }, [book?.bookId])

  useEffect(() => {
    const onOffline = (e: Event) => {
      const g = (e as CustomEvent<{ genre?: string }>).detail?.genre || 'unknown'
      void handleOffline(g)
    }
    window.addEventListener('novellab:run-offline-analysis', onOffline)
    return () => window.removeEventListener('novellab:run-offline-analysis', onOffline)
  }, [handleOffline])

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

  return (
    <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
      <Typography variant="h6" gutterBottom>
        {t('analysis_prog_title')}
      </Typography>
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
            typeof runOfflineAnalysis === 'function' ? (
              <Button color="inherit" size="small" disabled={offlineBusy} onClick={() => void handleOffline()}>
                {offlineBusy ? <CircularProgress size={14} /> : t('analysis_btn_offline', '离线量化拆解 & 接管包')}
              </Button>
            ) : undefined
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
                void navigator.clipboard.writeText(offlineData.guideMarkdown)
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
          <Box sx={{ maxHeight: 220, overflow: 'auto', bgcolor: 'action.hover', p: 1.5, borderRadius: 1 }}>
            <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>{offlineData.guideMarkdown}</pre>
          </Box>
        </Paper>
      )}

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
                          bgcolor: CELL_COLOR[st] ?? CELL_COLOR.pending,
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
            <Box sx={{ width: 12, height: 12, borderRadius: '3px', bgcolor: CELL_COLOR[s] }} />
            <Typography variant="caption" color="text.secondary">
              {t(STATUS_I18N_KEYS[s] ?? s)}
            </Typography>
          </Box>
        ))}
      </Box>
    </Box>
  )
}
