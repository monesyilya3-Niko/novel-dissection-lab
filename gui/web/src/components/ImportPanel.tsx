// 导入面板：拖拽 / 选文件（txt），经 multipart 上传到后端。
import { useCallback, useEffect, useRef, useState } from 'react'
import Box from '@mui/material/Box'
import ContextHelpButton from './ContextHelpButton'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Chip from '@mui/material/Chip'
import Divider from '@mui/material/Divider'
import { useApp } from '../state/AppContext'
import { friendlyError, listSamples, listBooks, type SampleInfo, type LibraryBook } from '../api/client'
import { useI18n } from '../state/I18nContext'

interface Props {
  compact?: boolean
}

export default function ImportPanel({ compact }: Props) {
  const { t } = useI18n()
  const { uploadBook, book } = useApp()
  const [dragging, setDragging] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  const doUpload = useCallback(
    async (file: File) => {
      const lower = file.name.toLowerCase()
      // 2026-11-03：后端 text_access.TEXT_SUFFIXES 一直支持 .txt 与 .md，
      // 前端却把 .md 当成不支持拦掉，并给用户「请另存为 .txt」的错误指引。
      if (!lower.endsWith('.txt') && !lower.endsWith('.md')) {
        const ext = lower.includes('.') ? lower.slice(lower.lastIndexOf('.')) : ''
        const knownHints: Record<string, string> = {
          '.pdf': 'analysis_import_pdf_hint',
          '.doc': 'analysis_import_doc_hint',
          '.docx': 'analysis_import_doc_hint',
          '.epub': 'analysis_import_epub_hint',
        }
        const hintKey = ext ? knownHints[ext] : undefined
        if (hintKey) {
          setError(t(hintKey))
        } else {
          setError(t('analysis_import_only_txt'))
        }
        return
      }
      setLoading(true)
      setError(null)
      try {
        await uploadBook(file)
      } catch (e) {
        setError(friendlyError(e))
      } finally {
        setLoading(false)
      }
    },
    [uploadBook, t],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      const file = e.dataTransfer.files?.[0]
      if (!file) return
      void doUpload(file)
    },
    [doUpload],
  )

  const onPick = useCallback(() => {
    fileInput.current?.click()
  }, [])

  const onFileChosen = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      if (file) void doUpload(file)
      e.target.value = ''
    },
    [doUpload],
  )

  return (
    <Box sx={{ p: compact ? 1.5 : 3 }}>
      <input
        ref={fileInput}
        type="file"
        accept=".txt,.md"
        style={{ display: 'none' }}
        onChange={onFileChosen}
      />
      <Box
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        sx={{
          border: '2px dashed',
          borderColor: dragging ? 'primary.main' : 'divider',
          borderRadius: 2,
          p: compact ? 2 : 4,
          textAlign: 'center',
          bgcolor: dragging ? 'rgba(25,118,210,0.06)' : 'transparent',
          cursor: 'pointer',
        }}
        onClick={onPick}
      >
        {loading ? (
          <CircularProgress size={24} />
        ) : (
          <>
            <Typography variant="body1" sx={{ fontWeight: 600 }}>
              {t('analysis_import_title')}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
              {t('analysis_import_drag_hint')}
            </Typography>
          </>
        )}
      </Box>
      {!compact && (
        <Box sx={{ mt: 2 }}>
          <Button variant="contained" onClick={onPick} disabled={loading} fullWidth>
            {t('analysis_import_btn_pick')}
          </Button>
        </Box>
      )}
      {error && (
        <Alert severity="error" sx={{ mt: 1.5 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
      {book && (
        <Alert severity="success" sx={{ mt: 1.5 }}>
          {t('analysis_import_success_prefix')}{book.title}{t('analysis_import_success_middle')}{book.totalChapters}{t('analysis_import_success_suffix')}
          {/* 2026-11-04：空章被过滤（拆书无从分析空正文），但要让用户知道
              少了哪几章，否则「导入 50 章只见 48 章」看起来像丢内容 */}
          {book.skippedEmptyChapters ? (
            <Box component="span" sx={{ display: 'block', mt: 0.5, fontSize: 12, opacity: 0.8 }}>
              {t('analysis_import_skipped_empty',
                  '另有 {n} 个正文为空的章节未导入（空章无法拆书分析）',
                  { n: String(book.skippedEmptyChapters) })}
            </Box>
          ) : null}
        </Alert>
      )}
      {/* 2026-11-23：compact（左侧栏）只保留上传入口；书目与示例放在「导入」主区，
          否则同一屏出现两套一模一样的导入面板与书目列表（默认页重复）。 */}
      {!compact && <LibraryList />}
      {!compact && <SampleList onImported={() => setError(null)} />}
    </Box>
  )
}

/** 内置示例语料列表（一键导入）。 */
function SampleList({ onImported }: { onImported: () => void }) {
  const { t, locale } = useI18n()
  const { importSampleBook } = useApp()
  const [samples, setSamples] = useState<SampleInfo[] | null>(null)
  const [importing, setImporting] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listSamples()
      .then(list => { if (!cancelled) setSamples(list) })
      .catch(() => { if (!cancelled) setSamples([]) })
    return () => { cancelled = true }
  }, [])

  const doImportSample = async (name: string) => {
    setImporting(name)
    setError(null)
    try {
      // 走 AppContext：导入后切换当前书并触发成功提示（与文件上传同一路径）。
      await importSampleBook(name)
      onImported()
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setImporting(null)
    }
  }

  if (!samples || samples.length === 0) return null

  return (
    <Box sx={{ mt: 3 }}>
      <Divider sx={{ mb: 2 }} />
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, flex: 1 }}>
          📦 {t('analysis_sample_title')} <Typography component="span" variant="caption" color="text.secondary">{t('analysis_sample_subtitle')}</Typography>
        </Typography>
        <ContextHelpButton guideKey="analysis" title={t('analysis_sample_help_title')} />
      </Box>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
        {samples.map(s => (
          <Chip
            key={s.name}
            label={`${s.genre} · ${s.chapters} ${locale === 'en-US' ? 'ch.' : '章'}`}
            clickable
            disabled={importing !== null}
            onClick={() => void doImportSample(s.name)}
            icon={importing === s.name ? <CircularProgress size={14} /> : undefined}
            variant="outlined"
            sx={{ '&:hover': { borderColor: 'primary.main' } }}
          />
        ))}
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.25 }}>
        {t(
          'analysis_sample_report_note',
          '示例语料仅用于体验拆书流程，篇幅不足以生成正式万字报告；导入你自己的书即可生成。',
        )}
      </Typography>
      {error && (
        <Alert severity="error" sx={{ mt: 1 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}
    </Box>
  )
}

/** 已导入书目列表（2026-11-03）。

 * 背景：普通工作台此前没有任何「我的书」入口——导入后只能操作刚导入的那本，
 * 刷新页面 book_id 就丢了（正文在服务端内存/状态文件里，前端不知道是哪个）。
 * 后端 /api/book/{id} 本来就能按 id 重载，缺的只是列表。
 */
function LibraryList() {
  const { t } = useI18n()
  const { book, openBook, status } = useApp()
  const [items, setItems] = useState<LibraryBook[]>([])
  const bookId = book?.bookId
  const [loadedOnce, setLoadedOnce] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [openError, setOpenError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    listBooks()
      .then((bs) => {
        if (!cancelled) {
          setItems(bs)
          setError(null)
        }
      })
      .catch((e) => {
        if (!cancelled) setError(friendlyError(e))
      })
      .finally(() => {
        if (!cancelled) setLoadedOnce(true)
      })
    return () => {
      cancelled = true
    }
    // 2026-11-23：分析完成/失败后要重新拉列表，否则「已导入书目」一直显示「待拆」，
    // 直到整页刷新。status?.status 从 running→done/partial/error 时触发。
  }, [bookId, status?.status])

  const doOpen = async (id: string) => {
    setOpenError(null)
    try {
      await openBook(id)
    } catch (e) {
      // 2026-11-23：旧实现 void openBook(...) 把 404 吞掉，用户看到的是“点了没反应”。
      setOpenError(friendlyError(e))
    }
  }

  if (!loadedOnce && items.length === 0) return null
  if (error) {
    return (
      <Alert severity="warning" sx={{ mt: 2 }}>
        {t('analysis_library_load_failed', '书目列表加载失败：')}{error}
      </Alert>
    )
  }
  if (items.length === 0) return null

  return (
    <Box sx={{ mt: 2 }}>
      <Divider sx={{ mb: 1 }} />
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        {t('analysis_library_title', '已导入书目')}（{items.length}）
      </Typography>
      <Box sx={{ maxHeight: 180, overflow: 'auto' }}>
        {items.map((b) => (
          <Box
            key={b.bookId}
            // 2026-11-05：列表项此前只有展示、点不动——用户看到书也切不回去，
            // 刷新页面后 book_id 只剩在这个列表里，等于找不回自己的书。
            onClick={() => { if (book?.bookId !== b.bookId) void doOpen(b.bookId) }}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault()
                if (book?.bookId !== b.bookId) void doOpen(b.bookId)
              }
            }}
            sx={{
              display: 'flex', alignItems: 'center', gap: 1, py: 0.4,
              px: 0.5, borderRadius: 1,
              cursor: book?.bookId === b.bookId ? 'default' : 'pointer',
              '&:hover': { bgcolor: 'action.hover' },
              bgcolor: book?.bookId === b.bookId ? 'action.selected' : 'transparent',
            }}
          >
            <Typography variant="body2" sx={{ flex: 1, fontSize: 13 }} noWrap>
              {b.title}
            </Typography>
            <Chip
              size="small"
              label={b.status === 'done'
                ? t('analysis_library_status_done', '已拆')
                : b.status === 'partial'
                  ? t('analysis_library_status_partial', '部分完成')
                  : b.status === 'error'
                    ? t('analysis_library_status_error', '失败')
                    : t('analysis_library_status_idle', '待拆')}
              color={b.status === 'done' ? 'success' : b.status === 'partial' ? 'warning' : b.status === 'error' ? 'error' : 'default'}
              variant="outlined"
              sx={{ height: 18, fontSize: 11 }}
            />
          </Box>
        ))}
      </Box>
      {openError && (
        <Alert severity="error" sx={{ mt: 1 }} onClose={() => setOpenError(null)}>
          {openError}
        </Alert>
      )}
    </Box>
  )
}
