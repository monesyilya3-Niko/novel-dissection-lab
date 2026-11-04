// 一键分析控制条：题材下拉（必填，来自 /api/genres）+ 「一键分析」按钮 + 任务状态。
import { useEffect, useRef, useState, useMemo } from 'react'
import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Chip from '@mui/material/Chip'
import Typography from '@mui/material/Typography'
import CircularProgress from '@mui/material/CircularProgress'
import FormControl from '@mui/material/FormControl'
import InputLabel from '@mui/material/InputLabel'
import Select from '@mui/material/Select'
import MenuItem from '@mui/material/MenuItem'
import { useApp } from '../state/AppContext'
import { getGenres } from '../api/client'
import { useI18n } from '../state/I18nContext'
import { inferGenreFromFilename } from '../utils/inferGenre'
import type { TaskStatus } from '../types'
import { friendlyError } from '../api/client'
import DisabledTooltipButton from './common/DisabledTooltipButton'

const STATUS_KEYS: Record<TaskStatus, string> = {
  idle: 'analysis_status_idle',
  running: 'analysis_status_running',
  paused: 'analysis_status_paused',
  done: 'analysis_status_done',
  error: 'analysis_status_error',
}

const STATUS_COLOR: Record<TaskStatus, 'default' | 'primary' | 'success' | 'error' | 'warning'> = {
  idle: 'default',
  running: 'primary',
  paused: 'warning',
  done: 'success',
  error: 'error',
}

export interface AnalysisControlBarProps {
  /** 一键分析完成后回调（切到结果页）。 */
  onGoResult: () => void
}

export default function AnalysisControlBar({ onGoResult }: AnalysisControlBarProps) {
  const { t } = useI18n()
  const { book, overview, status, runFullAnalysis } = useApp()
  const [genres, setGenres] = useState<string[]>([])
  const [genre, setGenre] = useState('')
  const [inferredFromFilename, setInferredFromFilename] = useState<string | null>(null)
  // 记录已经自动推断过题材的 bookId：保证「每本书只自动填一次」，
  // 避免重新挂载时覆盖用户手动改过的选择。
  const autoInferredForRef = useRef<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [errorKey, setErrorKey] = useState<string | null>(null)
  const [rawError, setRawError] = useState<string | null>(null)

  // P0-4：题材列表来自后端注册表（与后端校验同源），必填，无"未知"默认值。
  //
  // 依赖说明：effect 里用到书名做题材推断，所以必须把书名纳入依赖——
  // 只依赖 bookId 会让"同一本书改名后重新推断"失效，也是 react-hooks 报
  // missing dependency 的原因。提取成稳定字符串避免以整个 book 对象作依赖
  // （对象引用每次刷新都变，会导致疯狂重跑）。
  const bookId = book?.bookId
  const bookTitleForInfer =
    ((book as unknown as Record<string, unknown> | undefined)?.title as string)
    || ((book as unknown as Record<string, unknown> | undefined)?.name as string)
    || book?.sourcePath
    || ''

  useEffect(() => {
    let cancelled = false
    getGenres()
      .then((list) => {
        if (cancelled) return
        setGenres(list)
        // WS-A3：从文件名自动推断题材（可手动覆盖）。
        // 每本书只自动填一次：否则组件重新挂载（切换工作台再回来）会把用户
        // 手动改过的题材又覆盖回推断值——2026-10-29 复查发现的实际缺陷。
        if (bookId && autoInferredForRef.current !== bookId) {
          const inferred = inferGenreFromFilename(bookTitleForInfer, list)
          if (inferred) {
            autoInferredForRef.current = bookId
            setGenre(inferred)
            setInferredFromFilename(inferred)
          }
        }
      })
      .catch(() => {
        if (!cancelled) setErrorKey('analysis_err_load_genres')
      })
    return () => {
      cancelled = true
    }
  }, [bookId, bookTitleForInfer])

  const taskStatus: TaskStatus = status?.status ?? 'idle'
  const isRunning = taskStatus === 'running'

  const disabledReason = useMemo(() => {
    if (!book) return t('analysis_need_file')
    if (!genre) return t('analysis_need_genre')
    if (overview && !overview.modelConfigured) return t('analysis_need_model')
    return ''
  }, [book, genre, overview, t])

  const isDisabled = busy || isRunning || !genre || Boolean(overview && !overview.modelConfigured)

  const doRun = async () => {
    if (!genre) {
      setErrorKey('analysis_err_select_genre')
      return
    }
    setBusy(true)
    setErrorKey(null)
    setRawError(null)
    try {
      await runFullAnalysis(genre)
      onGoResult()
    } catch (e) {
      // 2026-11-03：此前直接用 e.message，绕过了 friendlyError 的
      // 令牌/体积/符号链接等可操作提示，英文界面下也只会看到后端中文原文。
      setRawError(friendlyError(e))
    } finally {
      setBusy(false)
    }
  }

  const errorMessage = errorKey ? t(errorKey) : rawError

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', py: 0.5 }}>
      {status && (
        <Chip size="small" label={t(STATUS_KEYS[taskStatus] ?? 'analysis_status_idle')} color={STATUS_COLOR[taskStatus]} />
      )}
      {status && (status.done > 0 || status.total > 0) && (
        <Typography variant="caption" color="text.secondary">
          {status.done}/{status.total} {t('analysis_batches_unit')}
        </Typography>
      )}

      {!book ? (
        <Typography variant="caption" color="text.secondary">
          {t('analysis_need_book')}
        </Typography>
      ) : (
        <>
          <FormControl size="small" sx={{ minWidth: 150 }} required>
            <InputLabel id="genre-select-label">{t('analysis_genre_label')}</InputLabel>
            <Select
              labelId="genre-select-label"
              value={genre}
              label={t('analysis_genre_label')}
              onChange={(e) => { setGenre(e.target.value); setInferredFromFilename(null) }}
              sx={{ fontSize: 13 }}
            >
              {genres.map((g) => (
                <MenuItem key={g} value={g} sx={{ fontSize: 13 }}>
                  {g}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {inferredFromFilename && genre === inferredFromFilename && (
            <Chip
              size="small"
              label={t('analysis_genre_auto_hint', undefined, { genre: inferredFromFilename })}
              onDelete={() => setInferredFromFilename(null)}
              sx={{ fontSize: 11 }}
            />
          )}
          <DisabledTooltipButton disabled={isDisabled} disabledReason={disabledReason}>
            <Button
              variant="contained"
              size="small"
              disabled={isDisabled}
              onClick={doRun}
              startIcon={busy ? <CircularProgress size={14} color="inherit" /> : undefined}
            >
              {isRunning ? t('analysis_btn_running') : t('analysis_btn_start')}
            </Button>
          </DisabledTooltipButton>
        </>
      )}

      {errorMessage && (
        <Typography variant="caption" color="error.main">
          {errorMessage}
        </Typography>
      )}
    </Box>
  )
}
