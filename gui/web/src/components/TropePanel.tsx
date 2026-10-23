// TropePanel：桥段库入口（放在「写作」页签内）。
//
// 浏览桥段库 → 按分类筛选 / 按当前题材过滤适用 → 查看详情 →
// 一键把桥段骨架写入「写作要点」（情节任务），不用手打复制。
import { useEffect, useMemo, useState } from 'react'
import Box from '@mui/material/Box'
import Alert from '@mui/material/Alert'
import Button from '@mui/material/Button'
import Checkbox from '@mui/material/Checkbox'
import Chip from '@mui/material/Chip'
import CircularProgress from '@mui/material/CircularProgress'
import FormControlLabel from '@mui/material/FormControlLabel'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemText from '@mui/material/ListItemText'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import TextField from '@mui/material/TextField'
import Typography from '@mui/material/Typography'
import { tropeApi, friendlyError } from '../api/client'
import type { Trope } from '../types'
import { ink } from '../ink'
import { useI18n } from '../state/I18nContext'

const ALL_CATEGORY_KEY = '__all__'

interface TropePanelProps {
  /** 把文本追加到「写作要点」（GeneratePanel 的 task state）。 */
  onInsert: (text: string) => void
  /** 当前题材（voice 的 genre），用于「只看当前题材适用」过滤。 */
  currentGenre?: string
  /** 写作要点当前文本：用于防止同一桥段重复写入（命中身份标记即视为已写入）。 */
  taskText?: string
}

/** 桥段 → 可直接拼进写作要点的紧凑文本。
 *
 * 首行固定为桥段名标记 ``【name】``：一是让用户在写作要点里一眼看出这段
 * 骨架来自哪个桥段；二是作为防重复写入的身份锚（见 TropePanel 的去重逻辑）。
 */
export function tropeToTaskText(t: Trope): string {
  const lines = [`【${t.name}】`]
  const s = t.skeleton
  if (s) {
    if (s.setup) lines.push(`铺垫：${s.setup}`)
    if (s.escalation?.length) {
      lines.push(`激化：${s.escalation.map((e, i) => `${i + 1}）${e}`).join('')}`)
    }
    if (s.payoff) lines.push(`引爆：${s.payoff}`)
    if (s.aftermath) lines.push(`余波：${s.aftermath}`)
  }
  if (t.parameters?.length) {
    const ps = t.parameters
      .map((p) => `${p.name}（${(p.options ?? []).join('/')}）`)
      .join('；')
    lines.push(`可调参数：${ps}`)
  }
  return lines.join('\n')
}

/** 桥段在写作要点中的身份标记（与 tropeToTaskText 首行一致）。 */
export function tropeTaskMarker(t: Trope): string {
  return `【${t.name}】`
}

export default function TropePanel({ onInsert, currentGenre, taskText }: TropePanelProps) {
  const { t } = useI18n()
  const [tropes, setTropes] = useState<Trope[]>([])
  const [totalCount, setTotalCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [category, setCategory] = useState(ALL_CATEGORY_KEY)
  const [keyword, setKeyword] = useState('')
  const [onlyApplicable, setOnlyApplicable] = useState(false)
  const [selectedId, setSelectedId] = useState('')

  useEffect(() => {
    tropeApi
      .list()
      .then((r) => {
        setTropes(r.tropes ?? [])
        setTotalCount(r.total_count ?? 0)
        setLoading(false)
      })
      .catch((e) => {
        setError(friendlyError(e))
        setLoading(false)
      })
  }, [])

  const categories = useMemo(() => {
    const s = new Set(tropes.map((t) => t.category).filter(Boolean))
    return [ALL_CATEGORY_KEY, ...Array.from(s)]
  }, [tropes])

  /** 关键词命中的文本面：桥段名 / 分类 / 骨架四段 / 可调参数名。 */
  function tropeSearchHaystack(t: Trope): string {
    const parts: string[] = [t.name ?? '', t.category ?? '']
    const s = t.skeleton
    if (s) {
      parts.push(s.setup ?? '', s.payoff ?? '', s.aftermath ?? '')
      parts.push(...(s.escalation ?? []))
    }
    parts.push(...(t.parameters ?? []).map((p) => p.name ?? ''))
    parts.push(...(t.commonFailures ?? []))
    return parts.join('\n').toLowerCase()
  }

  const filtered = useMemo(() => {
    const kw = keyword.trim().toLowerCase()
    return tropes.filter((tr) => {
      if (category !== ALL_CATEGORY_KEY && tr.category !== category) return false
      if (onlyApplicable && currentGenre) {
        const ag = tr.applicableGenres ?? []
        if (!ag.includes(currentGenre)) return false
      }
      if (kw && !tropeSearchHaystack(tr).includes(kw)) return false
      return true
    })
  }, [tropes, category, onlyApplicable, currentGenre, keyword])

const selected = tropes.find((t) => t.id === selectedId)?? null

/** 该桥段是否已在写作要点中（按身份标记判定，防重复写入）。 */
const alreadyInserted = !!selected && !!taskText && taskText.includes(tropeTaskMarker(selected))

const doInsert = () => {
if (!selected || alreadyInserted) return
onInsert(tropeToTaskText(selected))
}

  return (
    <Paper sx={{ p: 2, mb: 2, backgroundColor: ink.surface }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Typography variant="subtitle1">{t('trope_title', '桥段库 · 找灵感')}</Typography>
        <Chip size="small" label={t('trope_count', '{n} 条', { n: totalCount })} />
        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
          {t('trope_subtitle', '灵感枯竭时翻一翻：选一条桥段，一键写入下面的「写作要点」。')}
        </Typography>
      </Box>

      {loading && <CircularProgress size={20} />}
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}

      {!loading && !error && (
        <>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap', mb: 1 }}>
            <TextField
              select
              size="small"
              label={t('trope_category', '分类')}
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              sx={{ minWidth: 140 }}
            >
              {categories.map((c) => (
                <MenuItem key={c} value={c}>
                  {c === ALL_CATEGORY_KEY ? t('trope_cat_all', '全部') : c}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label={t('trope_search', '搜索桥段')}
              placeholder={t('trope_search_ph', '关键词：名称 / 骨架 / 参数')}
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
              sx={{ minWidth: 200 }}
            />
            <FormControlLabel
              control={
                <Checkbox
                  size="small"
                  checked={onlyApplicable}
                  onChange={(e) => setOnlyApplicable(e.target.checked)}
                  disabled={!currentGenre}
                />
              }
              label={
                currentGenre
                  ? t('trope_applicable_only', '只看当前题材适用（{g}）', { g: currentGenre })
                  : t('trope_applicable_unrecognized', '只看当前题材适用（未识别到题材）')
              }
            />
            <Typography variant="caption" color="text.secondary">
              {t('trope_stat_filtered', '{filtered} / {total} 条', {
                filtered: filtered.length,
                total: tropes.length,
              })}
            </Typography>
          </Box>

          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <List
              dense
              sx={{
                width: 280,
                maxWidth: '100%',
                maxHeight: 320,
                overflowY: 'auto',
                border: `1px solid ${ink.hairline}`,
                borderRadius: 1,
              }}
            >
              {filtered.map((tr) => (
                <ListItemButton
                  key={tr.id}
                  selected={tr.id === selectedId}
                  onClick={() => setSelectedId(tr.id)}
                >
                  <ListItemText
                    primary={tr.name}
                    secondary={tr.category}
                    primaryTypographyProps={{ variant: 'body2' }}
                  />
                </ListItemButton>
              ))}
              {filtered.length === 0 && (
                <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
                  {t('trope_empty', '没有符合筛选的桥段，换个分类或关键词试试。')}
                </Typography>
              )}
            </List>

            <Box sx={{ flex: 1, minWidth: 260 }}>
              {!selected ? (
                <Typography variant="body2" color="text.secondary" sx={{ pt: 1 }}>
                  {t('trope_select_hint', '点左侧任意桥段查看骨架（含铺垫→激化→引爆→余波四段式与可调参数）。')}
                </Typography>
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                    <Typography variant="subtitle2">{selected.name}</Typography>
                    <Chip size="small" label={selected.category} />
                    {selected.genreScope && selected.genreScope !== 'universal' && (
                      <Chip size="small" label={selected.genreScope} color="info" />
                    )}
                  </Box>
                  {selected.skeleton?.setup && (
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <b>{t('trope_setup', '铺垫：')}</b>{selected.skeleton.setup}
                    </Typography>
                  )}
                  {selected.skeleton?.escalation && selected.skeleton.escalation.length > 0 && (
                    <Box sx={{ mb: 1 }}>
                      <Typography variant="body2"><b>{t('trope_escalation', '激化：')}</b></Typography>
                      {selected.skeleton.escalation.map((e, i) => (
                        <Typography key={i} variant="body2" sx={{ pl: 2 }}>
                          {i + 1}）{e}
                        </Typography>
                      ))}
                    </Box>
                  )}
                  {selected.skeleton?.payoff && (
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <b>{t('trope_payoff', '引爆：')}</b>{selected.skeleton.payoff}
                    </Typography>
                  )}
                  {selected.skeleton?.aftermath && (
                    <Typography variant="body2" sx={{ mb: 1 }}>
                      <b>{t('trope_aftermath', '余波：')}</b>{selected.skeleton.aftermath}
                    </Typography>
                  )}
                  {selected.parameters && selected.parameters.length > 0 && (
                    <Typography variant="body2" sx={{ mb: 1 }} color="text.secondary">
                      {t('trope_parameters', '可调参数：')}
                      {selected.parameters.map((p) => `${p.name}（${(p.options ?? []).join('/')}）`).join('；')}
                    </Typography>
                  )}
                  {selected.commonFailures && selected.commonFailures.length > 0 && (
                    <Typography variant="body2" sx={{ mb: 1 }} color="warning.main">
                      {t('trope_failures', '常见翻车：')}
                      {selected.commonFailures.join('；')}
                    </Typography>
                  )}
                  <Button
                    variant="contained"
                    size="small"
                    onClick={doInsert}
                    disabled={alreadyInserted}
                    sx={{ mt: 1 }}
                  >
                    {alreadyInserted ? t('trope_btn_already', '已在写作要点中') : t('trope_btn_insert', '写入写作要点')}
                  </Button>
                  {alreadyInserted && (
                    <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                      {t('trope_already_hint', '该桥段已写入写作要点，无需重复添加。')}
                    </Typography>
                  )}
                </>
              )}
            </Box>
          </Box>
        </>
      )}
    </Paper>
  )
}
