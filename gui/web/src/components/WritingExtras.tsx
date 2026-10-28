// 创作管理（企业级重构）：大纲 / 人物卡 / 灵感便签 / 创作者仪表盘 / 多格式导出。
// 挂在辅助写作工作台下的新页签「创作」，各面板按项目隔离。
import { useState, useEffect, useCallback, useRef } from 'react'
import Box from '@mui/material/Box'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import Chip from '@mui/material/Chip'
import IconButton from '@mui/material/IconButton'
import Card from '@mui/material/Card'
import CardContent from '@mui/material/CardContent'
import Grid from '@mui/material/Grid'
import DeleteIcon from '@mui/icons-material/Delete'
import EditIcon from '@mui/icons-material/Edit'
import AddIcon from '@mui/icons-material/Add'
import DownloadIcon from '@mui/icons-material/Download'
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'
import HubIcon from '@mui/icons-material/Hub'
import DescriptionIcon from '@mui/icons-material/Description'
import CodeIcon from '@mui/icons-material/Code'
import ArticleIcon from '@mui/icons-material/Article'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import AssignmentIcon from '@mui/icons-material/Assignment'
import { writingApi, toolsApi, friendlyError } from '../api/client'
import type { WritingProject } from '../types'
import type { OutlineItem, CharacterCard, NoteItem, WritingStats, HookItem, TensionAnalysisResult, GoldenThreeTensionResult, ReaderRetentionResult } from '../api/client'
import { useThemeMode } from '../state/ThemeModeContext'
import { useI18n } from '../state/I18nContext'
import { ink, glassCard } from '../ink'
import CreationRateChart from './charts/CreationRateChart'
import EmotionWaveChart from './charts/EmotionWaveChart'
import RhythmRadarChart from './charts/RhythmRadarChart'
import ReaderRetentionChart from './charts/ReaderRetentionChart'

const OUTLINE_STATUS_COLOR: Record<string, 'default' | 'primary' | 'success'> = {
  planned: 'default',
  writing: 'primary',
  done: 'success',
}

export default function WritingExtras() {
  const { t } = useI18n()
  const [tab, setTab] = useState(0)
  const [projects, setProjects] = useState<WritingProject[] | null>(null)
  const [project, setProject] = useState('')
  const [error, setError] = useState('')

  const projectsReqIdRef = useRef(0)
  const loadProjects = useCallback(() => {
    const cur = ++projectsReqIdRef.current
    writingApi
      .projects()
      .then((ps) => {
        if (cur !== projectsReqIdRef.current) return
        setProjects(ps)
        if (ps.length > 0 && !ps.some((p) => p.name === project)) {
          setProject(ps[0].name)
        }
      })
      .catch((e) => {
        if (cur !== projectsReqIdRef.current) return
        setError(t('extras_err_load_projects', '加载项目失败: {msg}', { msg: friendlyError(e) }))
      })
  }, [project, t])

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
        <TextField
          select
          label={t('extras_project_label')}
          value={project}
          onChange={(e) => setProject(e.target.value)}
          sx={{ minWidth: 220 }}
          size="small"
        >
          {(projects ?? []).map((p) => (
            <MenuItem key={p.id} value={p.name}>
              {p.name}
            </MenuItem>
          ))}
        </TextField>
        <Typography variant="body2" color="text.secondary">
          {t('extras_project_desc')}
        </Typography>
      </Box>
      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
      {projects === null ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={28} /></Box>
      ) : !project ? (
        <Alert severity="info">{t('extras_no_project_alert')}</Alert>
      ) : (
        <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
          <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tab label={t('extras_tab_outline')} />
            <Tab label={t('extras_tab_character')} />
            <Tab label={t('extras_tab_notes')} />
            <Tab label={t('extras_tab_dashboard')} />
            <Tab label={t('extras_tab_export')} />
          </Tabs>
          <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', py: 2 }}>
            {tab === 0 && <OutlinePanel project={project} />}
            {tab === 1 && <CharacterPanel project={project} />}
            {tab === 2 && <NotePanel project={project} />}
            {tab === 3 && <DashboardPanel project={project} />}
            {tab === 4 && <ExportPanel project={project} />}
          </Box>
        </Box>
      )}
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 1. 大纲架构（支持卷章拖拽/上下移重排）
// ---------------------------------------------------------------------------

function OutlinePanel({ project }: { project: string }) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()
  const [items, setItems] = useState<OutlineItem[] | null>(null)
  const [error, setError] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<OutlineItem | null>(null)
  const [kind, setKind] = useState('chapter')
  const [title, setTitle] = useState('')
  const [summary, setSummary] = useState('')
  const [status, setStatus] = useState('planned')

  const [templateOpen, setTemplateOpen] = useState(false)
  const [templates, setTemplates] = useState<HookItem[]>([])
  const [templateLoading, setTemplateLoading] = useState(false)
  const [selectedHook, setSelectedHook] = useState<HookItem | null>(null)
  const [isReordering, setIsReordering] = useState(false)
  const [isApplyingTemplate, setIsApplyingTemplate] = useState(false)
  const reqIdRef = useRef(0)

  const kindLabel = (k: string) => (k === 'volume' ? t('extras_outline_volume') : t('extras_outline_chapter'))
  const statusLabel = (s: string) => {
    if (s === 'planned') return t('extras_outline_status_planned')
    if (s === 'writing') return t('extras_outline_status_writing')
    if (s === 'done') return t('extras_outline_status_done')
    return s
  }

  const openHookTemplateDialog = async () => {
    setTemplateOpen(true)
    if (templates.length === 0) {
      setTemplateLoading(true)
      try {
        const res = await toolsApi.getHooks()
        setTemplates(res.hooks || [])
        if (res.hooks && res.hooks.length > 0) {
          setSelectedHook(res.hooks[0])
        }
      } catch (e) {
        setError(t('extras_err_load_templates', '加载开篇模板失败: {msg}', { msg: friendlyError(e) }))
      } finally {
        setTemplateLoading(false)
      }
    }
  }

  const doApplyTemplate = async () => {
    if (!selectedHook || isApplyingTemplate) return
    setError('')
    setIsApplyingTemplate(true)
    const createdIds: number[] = []
    try {
      const baseOrder = (items ?? []).length
      const r1 = await writingApi.createOutline({
        project,
        kind: 'chapter',
        title: t('extras_template_ch1_title', '第1章：{name}（首章生死危机）', { name: selectedHook.name }),
        summary: t('extras_template_ch1_summary', '【前300字钩子】\n{first300Words}\n\n【第一章节拍】\n{beat}', { first300Words: selectedHook.first300Words, beat: selectedHook.chapter1Beat }),
        status: 'planned',
        sort_order: baseOrder,
      })
      if (r1 && typeof (r1 as any).id === 'number') createdIds.push((r1 as any).id)
      const r2 = await writingApi.createOutline({
        project,
        kind: 'chapter',
        title: t('extras_template_ch2_title', '第2章：{name}（压迫激化与转机）', { name: selectedHook.name }),
        summary: t('extras_template_ch2_summary', '【第二章节拍】\n{beat}', { beat: selectedHook.chapter2Beat }),
        status: 'planned',
        sort_order: baseOrder + 1,
      })
      if (r2 && typeof (r2 as any).id === 'number') createdIds.push((r2 as any).id)
      const r3 = await writingApi.createOutline({
        project,
        kind: 'chapter',
        title: t('extras_template_ch3_title', '第3章：{name}（首爽破局与爽点兑现）', { name: selectedHook.name }),
        summary: t('extras_template_ch3_summary', '【第三章节拍】\n{beat}', { beat: selectedHook.chapter3Beat }),
        status: 'planned',
        sort_order: baseOrder + 2,
      })
      if (r3 && typeof (r3 as any).id === 'number') createdIds.push((r3 as any).id)
      setTemplateOpen(false)
      load()
    } catch (e) {
      for (const id of createdIds) {
        try { await writingApi.deleteOutline(id) } catch { /* best-effort rollback */ }
      }
      if (createdIds.length > 0) {
        setError(t('extras_err_apply_template_rollback', '应用黄金三章模板失败，已回滚 {count} 条已创建的大纲: {msg}', { count: createdIds.length, msg: friendlyError(e) }))
        load()
      } else {
        setError(t('extras_err_apply_template', '应用黄金三章模板失败: {msg}', { msg: friendlyError(e) }))
      }
    } finally {
      setIsApplyingTemplate(false)
    }
  }

  const load = useCallback(() => {
    const cur = ++reqIdRef.current
    writingApi
      .outlines(project)
      .then((res) => {
        if (cur !== reqIdRef.current) return
        setItems(res)
      })
      .catch((e) => {
        if (cur !== reqIdRef.current) return
        setError(t('extras_err_load_outlines', '加载大纲失败: {msg}', { msg: friendlyError(e) }))
      })
  }, [project, t])

  useEffect(() => {
    load()
  }, [load])

  const openCreate = () => {
    setEditing(null)
    setKind('chapter')
    setTitle('')
    setSummary('')
    setStatus('planned')
    setDialogOpen(true)
  }

  const openEdit = (it: OutlineItem) => {
    setEditing(it)
    setKind(it.kind)
    setTitle(it.title)
    setSummary(it.summary)
    setStatus(it.status)
    setDialogOpen(true)
  }

  const doSave = async () => {
    if (!title.trim()) {
      setError(t('extras_err_title_required', '标题不能为空'))
      return
    }
    setError('')
    try {
      if (editing) {
        await writingApi.updateOutline(editing.id, { kind, title: title.trim(), summary, status })
      } else {
        await writingApi.createOutline({ project, kind, title: title.trim(), summary, status, sort_order: (items ?? []).length })
      }
      setDialogOpen(false)
      load()
    } catch (e) {
      setError(t('extras_err_save_failed', '保存失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  const doDelete = async (id: number) => {
    if (!window.confirm(t('extras_confirm_delete_outline', '确定删除这条大纲吗？'))) return
    try {
      await writingApi.deleteOutline(id)
      load()
    } catch (e) {
      setError(t('extras_err_delete_failed', '删除失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  const doToggleStatus = async (it: OutlineItem) => {
    const order = ['planned', 'writing', 'done']
    const next = order[(order.indexOf(it.status) + 1) % order.length]
    try {
      await writingApi.updateOutline(it.id, { status: next })
      load()
    } catch (e) {
      setError(t('extras_err_update_status_failed', '更新状态失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  const doMove = async (index: number, direction: 'up' | 'down') => {
    if (isReordering) return
    const list = items ?? []
    const targetIndex = direction === 'up' ? index - 1 : index + 1
    if (targetIndex < 0 || targetIndex >= list.length) return
    const prevItems = list
    const newItems = [...list]
    const temp = newItems[index]
    newItems[index] = newItems[targetIndex]
    newItems[targetIndex] = temp
    setItems(newItems)
    setIsReordering(true)
    try {
      await writingApi.reorderOutlines(project, newItems.map((it) => it.id))
      load()
    } catch (e) {
      setItems(prevItems)
      setError(t('extras_err_reorder_failed', '重排序失败: {msg}', { msg: friendlyError(e) }))
    } finally {
      setIsReordering(false)
    }
  }

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box sx={{ display: 'flex', gap: 1.5 }}>
          <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
            {t('extras_outline_add_btn')}
          </Button>
          <Button variant="outlined" color="primary" onClick={openHookTemplateDialog}>
            {t('extras_outline_hook_template_btn')}
          </Button>
        </Box>
        <Typography variant="caption" color="text.secondary">
          共 {(items ?? []).filter((i) => i.kind === 'volume').length} {t('extras_outline_volume')} / {(items ?? []).filter((i) => i.kind === 'chapter').length} {t('extras_outline_chapter')} ｜ {t('extras_outline_reorder_hint', '支持上下微移原子重排')}
        </Typography>
      </Box>

      {items === null ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={28} /></Box>
      ) : items.length === 0 ? (
        <Paper elevation={0} sx={{ p: 4, textAlign: 'center', ...glassCard(isDark) }}>
          <Typography color="text.secondary">{t('extras_outline_empty')}</Typography>
        </Paper>
      ) : (
        items.map((it, idx) => {
          const isVolume = it.kind === 'volume'
          return (
            <Paper
              key={it.id}
              elevation={0}
              sx={{
                p: 2,
                mb: 1.5,
                ...glassCard(isDark),
                borderLeft: isVolume ? '4px solid #2563EB' : `1px solid ${isDark ? ink.nightLine : ink.hairline}`,
                ml: isVolume ? 0 : 2,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  label={kindLabel(it.kind)}
                  size="small"
                  color={isVolume ? 'primary' : 'default'}
                  variant={isVolume ? 'filled' : 'outlined'}
                />
                <Typography variant="subtitle1" sx={{ flex: 1, fontWeight: isVolume ? 700 : 600 }}>
                  {it.title}
                </Typography>
                <Chip
                  label={statusLabel(it.status)}
                  size="small"
                  color={OUTLINE_STATUS_COLOR[it.status] ?? 'default'}
                  onClick={() => doToggleStatus(it)}
                  sx={{ cursor: 'pointer' }}
                  title={t("extras_action_toggle_status", "点击切换状态")}
                />
                <IconButton
                  size="small"
                  disabled={idx === 0 || isReordering}
                  onClick={() => doMove(idx, 'up')}
                  title={t("extras_action_move_up", "上移")}
                  aria-label={t('extras_outline_move_up_aria', '上移')}
                >
                  <ArrowUpwardIcon fontSize="small" />
                </IconButton>
                <IconButton
                  size="small"
                  disabled={idx === (items ?? []).length - 1 || isReordering}
                  onClick={() => doMove(idx, 'down')}
                  title={t("extras_action_move_down", "下移")}
                  aria-label={t('extras_outline_move_down_aria', '下移')}
                >
                  <ArrowDownwardIcon fontSize="small" />
                </IconButton>
                <IconButton size="small" onClick={() => openEdit(it)} title={t("extras_action_edit", "编辑")} aria-label={t('extras_action_edit_aria', '编辑')}>
                  <EditIcon fontSize="small" />
                </IconButton>
                <IconButton size="small" onClick={() => doDelete(it.id)} title={t("extras_action_delete", "删除")} aria-label={t('extras_action_delete_aria', '删除')}>
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Box>
              {it.summary && (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1, whiteSpace: 'pre-wrap', pl: 0.5 }}>
                  {it.summary}
                </Typography>
              )}
            </Paper>
          )
        })
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? t('extras_outline_edit_title') : t('extras_outline_new_title')}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField select label={t('extras_outline_kind')} value={kind} onChange={(e) => setKind(e.target.value)}>
            <MenuItem value="volume">{t('extras_outline_kind_volume')}</MenuItem>
            <MenuItem value="chapter">{t('extras_outline_kind_chapter')}</MenuItem>
          </TextField>
          <TextField label={t('extras_outline_item_title')} value={title} onChange={(e) => setTitle(e.target.value)} fullWidth />
          <TextField
            label={t('extras_outline_summary')}
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            fullWidth
            multiline
            rows={4}
            placeholder={t('extras_outline_summary_ph')}
          />
          <TextField select label={t('extras_outline_status')} value={status} onChange={(e) => setStatus(e.target.value)}>
            <MenuItem value="planned">{t('extras_outline_status_planned')}</MenuItem>
            <MenuItem value="writing">{t('extras_outline_status_writing')}</MenuItem>
            <MenuItem value="done">{t('extras_outline_status_done')}</MenuItem>
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t('action_cancel')}</Button>
          <Button variant="contained" onClick={doSave}>{t('action_save')}</Button>
        </DialogActions>
      </Dialog>

      {/* 引用黄金三章开篇模板弹窗 */}
      <Dialog
        open={templateOpen}
        onClose={() => setTemplateOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', pb: 1 }}>
          <Typography component="span" variant="h6" fontWeight={700}>
            {t('extras_outline_template_dialog_title')}
          </Typography>
          <Typography component="span" variant="caption" color="text.secondary">
            {t('extras_outline_template_dialog_subtitle')}
          </Typography>
        </DialogTitle>
        <DialogContent dividers sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {templateLoading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress size={32} />
            </Box>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                select
                label={t('extras_outline_template_select')}
                value={selectedHook?.id || ''}
                onChange={(e) => {
                  const target = templates.find((tmp) => tmp.id === e.target.value)
                  if (target) setSelectedHook(target)
                }}
                fullWidth
              >
                {templates.map((tmpl) => (
                  <MenuItem key={tmpl.id} value={tmpl.id}>
                    [{tmpl.genre}] {tmpl.name}
                  </MenuItem>
                ))}
              </TextField>

              {selectedHook && (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                  <Paper variant="outlined" sx={{ p: 1.5, bgcolor: 'action.hover' }}>
                    <Typography variant="subtitle2" color="primary" fontWeight={700} gutterBottom>
                      {t('extras_outline_template_first300')}
                    </Typography>
                    <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
                      {selectedHook.first300Words}
                    </Typography>
                  </Paper>

                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" fontWeight={700} color="text.primary" gutterBottom>
                      {t('extras_outline_template_beat1')}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                      {selectedHook.chapter1Beat}
                    </Typography>
                  </Paper>

                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" fontWeight={700} color="text.primary" gutterBottom>
                      {t('extras_outline_template_beat2')}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                      {selectedHook.chapter2Beat}
                    </Typography>
                  </Paper>

                  <Paper variant="outlined" sx={{ p: 1.5 }}>
                    <Typography variant="subtitle2" fontWeight={700} color="text.primary" gutterBottom>
                      {t('extras_outline_template_beat3')}
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ lineHeight: 1.7 }}>
                      {selectedHook.chapter3Beat}
                    </Typography>
                  </Paper>
                </Box>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTemplateOpen(false)}>{t('action_cancel')}</Button>
          <Button
            variant="contained"
            color="primary"
            onClick={doApplyTemplate}
            disabled={!selectedHook || isApplyingTemplate}
          >
            {isApplyingTemplate ? t('extras_tension_analyzing', '应用中…') : t('extras_outline_template_apply')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 2. 人物卡与关系网
// ---------------------------------------------------------------------------

function CharacterPanel({ project }: { project: string }) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()
  const [items, setItems] = useState<CharacterCard[] | null>(null)
  const [error, setError] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<CharacterCard | null>(null)
  const [name, setName] = useState('')
  const [role, setRole] = useState('')
  const [description, setDescription] = useState('')
  const [camp, setCamp] = useState('主角阵营')
  const [relationTarget, setRelationTarget] = useState('')
  const [relationType, setRelationType] = useState('同盟')
  const reqIdRef = useRef(0)

  const load = useCallback(() => {
    const cur = ++reqIdRef.current
    writingApi
      .characters(project)
      .then((res) => {
        if (cur !== reqIdRef.current) return
        setItems(res)
      })
      .catch((e) => {
        if (cur !== reqIdRef.current) return
        setError(t('extras_err_load_characters', '加载人物卡失败: {msg}', { msg: friendlyError(e) }))
      })
  }, [project, t])

  useEffect(() => {
    load()
  }, [load])

  const openCreate = () => {
    setEditing(null)
    setName('')
    setRole('')
    setDescription('')
    setCamp('主角阵营')
    setRelationTarget('')
    setRelationType('同盟')
    setDialogOpen(true)
  }

  const handleRandomName = async () => {
    try {
      const res = await toolsApi.generateNames({ kind: 'character', count: 1 })
      if (res.names && res.names.length > 0) {
        setName(res.names[0])
      }
    } catch (e) {
      setError(t('extras_err_random_name_failed', '随机起名失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  const openEdit = (it: CharacterCard) => {
    setEditing(it)
    setName(it.name)
    setRole(it.role)
    setDescription(it.description)
    try {
      const extraObj = JSON.parse(it.extra || '{}')
      setCamp(extraObj.camp || '主角阵营')
      setRelationTarget(extraObj.relationTarget || '')
      setRelationType(extraObj.relationType || '同盟')
    } catch {
      setCamp('主角阵营')
      setRelationTarget('')
      setRelationType('同盟')
    }
    setDialogOpen(true)
  }

  const doSave = async () => {
    if (!name.trim()) {
      setError(t('extras_err_name_required', '姓名不能为空'))
      return
    }
    setError('')
    const extraData = {
      camp,
      relationTarget: relationTarget.trim(),
      relationType: relationType.trim(),
    }
    try {
      if (editing) {
        await writingApi.updateCharacter(editing.id, {
          name: name.trim(),
          role,
          description,
          extra: extraData,
        })
      } else {
        await writingApi.createCharacter({
          project,
          name: name.trim(),
          role,
          description,
          extra: extraData,
        })
      }
      setDialogOpen(false)
      load()
    } catch (e) {
      setError(t('extras_err_save_failed', '保存失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  const doDelete = async (id: number) => {
    if (!window.confirm(t('extras_confirm_delete_character', '确定删除这张人物卡吗？'))) return
    try {
      await writingApi.deleteCharacter(id)
      load()
    } catch (e) {
      setError(t('extras_err_delete_failed', '删除失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          {t('extras_char_add_btn')}
        </Button>
        <Typography variant="caption" color="text.secondary">
          {t('extras_char_subtitle_count', '当前共 {count} 位角色 ｜ {hint}', { count: (items ?? []).length, hint: t('extras_char_subtitle', '支持人物阵营与人物关系网络关联') })}
        </Typography>
      </Box>

      {items === null ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={28} /></Box>
      ) : items.length === 0 ? (
        <Paper elevation={0} sx={{ p: 4, textAlign: 'center', ...glassCard(isDark) }}>
          <Typography color="text.secondary">{t('extras_char_empty')}</Typography>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {items!.map((it) => {
            let extraObj: any = {}
            try {
              extraObj = JSON.parse(it.extra || '{}')
            } catch {
              extraObj = {}
            }
            return (
              <Grid item xs={12} sm={6} md={4} key={it.id}>
                <Card elevation={0} sx={{ height: '100%', ...glassCard(isDark) }}>
                  <CardContent>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Typography variant="h6" fontWeight={700} sx={{ flex: 1 }}>
                        {it.name}
                      </Typography>
                      {it.role && <Chip label={it.role} size="small" color="primary" variant="outlined" />}
                      <IconButton size="small" onClick={() => openEdit(it)} title={t("extras_action_edit", "编辑")} aria-label={t('extras_action_edit_aria', '编辑')}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                      <IconButton size="small" onClick={() => doDelete(it.id)} title={t("extras_action_delete", "删除")} aria-label={t('extras_action_delete_aria', '删除')}>
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Box>

                    {extraObj.camp && (
                      <Box sx={{ mb: 1 }}>
                        <Chip
                          label={extraObj.camp}
                          size="small"
                          sx={{
                            fontSize: 11,
                            bgcolor: (extraObj.camp.includes('反派') || extraObj.camp.toLowerCase().includes('antagonist')) ? 'rgba(220,38,38,0.1)' : 'rgba(37,99,235,0.1)',
                            color: (extraObj.camp.includes('反派') || extraObj.camp.toLowerCase().includes('antagonist')) ? '#DC2626' : '#2563EB',
                          }}
                        />
                      </Box>
                    )}

                    {extraObj.relationTarget && (
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 1.5 }}>
                        <HubIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                        <Typography variant="caption" color="text.secondary">
                          {t('extras_char_relation_prefix', '关系：与 ')}<b>{extraObj.relationTarget}</b>{t('extras_char_relation_middle', ' 为 ') + '['}{extraObj.relationType || t('extras_char_relation_default', '关联')}]
                        </Typography>
                      </Box>
                    )}

                    {it.description && (
                      <Typography variant="body2" color="text.secondary" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                        {it.description}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            )
          })}
        </Grid>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? t('extras_char_edit_title') : t('extras_char_new_title')}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
            <TextField label={t('extras_char_name')} value={name} onChange={(e) => setName(e.target.value)} fullWidth />
            <Button
              variant="outlined"
              onClick={handleRandomName}
              sx={{ minWidth: 96, height: 40, whiteSpace: 'nowrap' }}
            >
              {t('extras_char_random_name')}
            </Button>
          </Box>
          <TextField
            label={t('extras_char_role')}
            value={role}
            onChange={(e) => setRole(e.target.value)}
            fullWidth
            placeholder={t('extras_char_role_ph')}
          />
          <TextField select label={t('extras_char_camp')} value={camp} onChange={(e) => setCamp(e.target.value)} fullWidth>
            <MenuItem value="主角阵营">{t('extras_char_camp_protagonist')}</MenuItem>
            <MenuItem value="反派宿敌">{t('extras_char_camp_antagonist')}</MenuItem>
            <MenuItem value="中立势力">{t('extras_char_camp_neutral')}</MenuItem>
            <MenuItem value="宗门高层">{t('extras_char_camp_sect')}</MenuItem>
            <MenuItem value="世外高人">{t('extras_char_camp_hermit')}</MenuItem>
          </TextField>
          <Box sx={{ display: 'flex', gap: 1.5 }}>
            <TextField
              label={t('extras_char_rel_target')}
              value={relationTarget}
              onChange={(e) => setRelationTarget(e.target.value)}
              sx={{ flex: 1 }}
              placeholder={t('extras_char_rel_target_ph')}
            />
            <TextField
              label={t('extras_char_rel_type')}
              value={relationType}
              onChange={(e) => setRelationType(e.target.value)}
              sx={{ width: 140 }}
              placeholder={t('extras_char_rel_type_ph')}
            />
          </Box>
          <TextField
            label={t('extras_char_desc')}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            fullWidth
            multiline
            rows={5}
            placeholder={t('extras_char_desc_ph')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t('action_cancel')}</Button>
          <Button variant="contained" onClick={doSave}>{t('action_save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 3. 灵感便签
// ---------------------------------------------------------------------------

function NotePanel({ project }: { project: string }) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()
  const [items, setItems] = useState<NoteItem[] | null>(null)
  const [error, setError] = useState('')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editing, setEditing] = useState<NoteItem | null>(null)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const reqIdRef = useRef(0)

  const load = useCallback(() => {
    const cur = ++reqIdRef.current
    writingApi
      .notes(project)
      .then((res) => {
        if (cur !== reqIdRef.current) return
        setItems(res)
      })
      .catch((e) => {
        if (cur !== reqIdRef.current) return
        setError(t('extras_err_load_notes', '加载便签失败: {msg}', { msg: friendlyError(e) }))
      })
  }, [project, t])

  useEffect(() => {
    load()
  }, [load])

  const openCreate = () => {
    setEditing(null)
    setTitle('')
    setContent('')
    setDialogOpen(true)
  }

  const openEdit = (it: NoteItem) => {
    setEditing(it)
    setTitle(it.title)
    setContent(it.content)
    setDialogOpen(true)
  }

  const doSave = async () => {
    if (!title.trim() && !content.trim()) {
      setError(t('extras_err_title_content_empty', '标题与内容不能同时为空'))
      return
    }
    setError('')
    try {
      if (editing) {
        await writingApi.updateNote(editing.id, { title, content })
      } else {
        await writingApi.createNote({ project, title, content })
      }
      setDialogOpen(false)
      load()
    } catch (e) {
      setError(t('extras_err_save_failed', '保存失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  const doDelete = async (id: number) => {
    if (!window.confirm(t('extras_confirm_delete_note', '确定删除这条便签吗？'))) return
    try {
      await writingApi.deleteNote(id)
      load()
    } catch (e) {
      setError(t('extras_err_delete_failed', '删除失败: {msg}', { msg: friendlyError(e) }))
    }
  }

  return (
    <Box>
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}
      <Box sx={{ mb: 2 }}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openCreate}>
          {t('extras_note_add_btn')}
        </Button>
      </Box>
      {items === null ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}><CircularProgress size={28} /></Box>
      ) : items.length === 0 ? (
        <Paper elevation={0} sx={{ p: 4, textAlign: 'center', ...glassCard(isDark) }}>
          <Typography color="text.secondary">{t('extras_note_empty')}</Typography>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {items!.map((it) => (
            <Grid item xs={12} sm={6} md={4} key={it.id}>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  height: '100%',
                  cursor: 'pointer',
                  ...glassCard(isDark),
                  display: 'flex',
                  flexDirection: 'column',
                }}
                onClick={() => openEdit(it)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openEdit(it) } }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Typography variant="subtitle1" fontWeight={700} sx={{ flex: 1 }}>
                    {it.title || t('extras_note_untitled')}
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={(e) => {
                      e.stopPropagation()
                      doDelete(it.id)
                    }}
                    title={t("extras_action_delete", "删除")}
                    aria-label={t('extras_action_delete_aria', '删除')}
                  >
                    <DeleteIcon fontSize="small" />
                  </IconButton>
                </Box>
                {it.content && (
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{
                      whiteSpace: 'pre-wrap',
                      display: '-webkit-box',
                      WebkitLineClamp: 4,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                      lineHeight: 1.6,
                    }}
                  >
                    {it.content}
                  </Typography>
                )}
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? t('extras_note_edit_title') : t('extras_note_new_title')}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <TextField label={t('extras_note_title')} value={title} onChange={(e) => setTitle(e.target.value)} fullWidth />
          <TextField
            label={t('extras_note_content')}
            value={content}
            onChange={(e) => setContent(e.target.value)}
            fullWidth
            multiline
            rows={6}
            placeholder={t('extras_note_content_ph')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>{t('action_cancel')}</Button>
          <Button variant="contained" onClick={doSave}>{t('action_save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 4. 创作者仪表盘（字数速率折线 + 情绪起伏波形 + 爽点节奏雷达）
// ---------------------------------------------------------------------------

function DashboardPanel({ project }: { project: string }) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()
  const [stats, setStats] = useState<WritingStats | null>(null)
  const [error, setError] = useState('')
  const [days, setDays] = useState(30)

  // 黄金三章与章节张力动态比对
  const [benchmark, setBenchmark] = useState<'classic' | 'fast_hook' | 'steady' | 'face_slap'>('classic')
  const [tensionResult, setTensionResult] = useState<TensionAnalysisResult | null>(null)
  const [tensionLoading, setTensionLoading] = useState(false)
  const [showTensionDialog, setShowTensionDialog] = useState(false)
  const [draftInput, setDraftInput] = useState('')

  // 黄金三章连环多章比对
  const [goldenThreeBm, setGoldenThreeBm] = useState<'classic' | 'upgrade_shuangwen' | 'fast_hook' | 'suspense_mystery'>('classic')
  const [goldenThreeResult, setGoldenThreeResult] = useState<GoldenThreeTensionResult | null>(null)
  const [goldenThreeLoading, setGoldenThreeLoading] = useState(false)
  const [showGoldenThreeDialog, setShowGoldenThreeDialog] = useState(false)
  const [ch1Input, setCh1Input] = useState('')
  const [ch2Input, setCh2Input] = useState('')
  const [ch3Input, setCh3Input] = useState('')

  // 商业网文读者留存流失预测（与黄金三章共用三章草稿输入）
  const [retentionBm, setRetentionBm] = useState<'classic' | 'upgrade_shuangwen' | 'fast_hook' | 'suspense_mystery'>('classic')
  const [retentionResult, setRetentionResult] = useState<ReaderRetentionResult | null>(null)
  const [retentionLoading, setRetentionLoading] = useState(false)
  const [showRetentionDialog, setShowRetentionDialog] = useState(false)
  const tensionSeqRef = useRef(0)
  const goldenThreeSeqRef = useRef(0)
  const retentionSeqRef = useRef(0)
  const statsReqIdRef = useRef(0)

  const load = useCallback(() => {
    const cur = ++statsReqIdRef.current
    writingApi
      .stats(project, days)
      .then((res) => {
        if (cur !== statsReqIdRef.current) return
        setStats(res)
      })
      .catch((e) => {
        if (cur !== statsReqIdRef.current) return
        setError(t('extras_err_load_dashboard', '加载仪表盘统计失败: {msg}', { msg: friendlyError(e) }))
      })
  }, [project, days, t])

  useEffect(() => {
    tensionSeqRef.current++
    goldenThreeSeqRef.current++
    retentionSeqRef.current++
    setTensionResult(null)
    setGoldenThreeResult(null)
    setRetentionResult(null)
  }, [project])

  useEffect(() => {
    load()
  }, [load])

  const runTensionAnalysis = async (text: string, bm = benchmark) => {
    if (!text.trim()) return
    const capturedSeq = ++tensionSeqRef.current
    setTensionLoading(true)
    try {
      const res = await writingApi.analyzeTension({
        text,
        benchmark: bm,
      })
      if (capturedSeq !== tensionSeqRef.current) return
      setTensionResult(res)
      setShowTensionDialog(false)
    } catch (e) {
      if (capturedSeq !== tensionSeqRef.current) return
      setError(t('extras_err_tension_failed', '张力分析失败: {msg}', { msg: friendlyError(e) }))
    } finally {
      if (capturedSeq === tensionSeqRef.current) setTensionLoading(false)
    }
  }

  const runGoldenThreeAnalysis = async (
    ch1 = ch1Input,
    ch2 = ch2Input,
    ch3 = ch3Input,
    bm = goldenThreeBm,
  ) => {
    const chapters = [ch1, ch2, ch3].filter((c) => c.trim().length > 0)
    if (chapters.length === 0) return
    const capturedSeq = ++goldenThreeSeqRef.current
    setGoldenThreeLoading(true)
    try {
      const res = await writingApi.analyzeGoldenThreeTension({
        chapters,
        benchmark: bm,
        points_per_chapter: 10,
      })
      if (capturedSeq !== goldenThreeSeqRef.current) return
      setGoldenThreeResult(res)
      setShowGoldenThreeDialog(false)
    } catch (e) {
      if (capturedSeq !== goldenThreeSeqRef.current) return
      setError(t('extras_err_golden_three_failed', '黄金三章比对失败: {msg}', { msg: friendlyError(e) }))
    } finally {
      if (capturedSeq === goldenThreeSeqRef.current) setGoldenThreeLoading(false)
    }
  }

  const runReaderRetention = async (
    ch1 = ch1Input,
    ch2 = ch2Input,
    ch3 = ch3Input,
    bm = retentionBm,
  ) => {
    const chapters = [ch1, ch2, ch3].filter((c) => c.trim().length > 0)
    if (chapters.length === 0) return
    const capturedSeq = ++retentionSeqRef.current
    setRetentionLoading(true)
    try {
      const res = await writingApi.estimateReaderRetention({
        chapters,
        benchmark: bm,
        points_per_chapter: 10,
      })
      if (capturedSeq !== retentionSeqRef.current) return
      setRetentionResult(res)
      setShowRetentionDialog(false)
    } catch (e) {
      if (capturedSeq !== retentionSeqRef.current) return
      setError(t('extras_err_retention_failed', '读者留存测算失败: {msg}', { msg: friendlyError(e) }))
    } finally {
      if (capturedSeq === retentionSeqRef.current) setRetentionLoading(false)
    }
  }

  const handleBenchmarkChange = (bm: 'classic' | 'fast_hook' | 'steady' | 'face_slap') => {
    setBenchmark(bm)
    if (draftInput.trim()) {
      runTensionAnalysis(draftInput, bm)
    }
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" fontWeight={700}>
          {t('extras_dash_title')}
        </Typography>
        <TextField
          select
          label={t('extras_dash_timespan')}
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          size="small"
          sx={{ minWidth: 130 }}
        >
          <MenuItem value={7}>{t('extras_dash_7days')}</MenuItem>
          <MenuItem value={30}>{t('extras_dash_30days')}</MenuItem>
          <MenuItem value={90}>{t('extras_dash_90days')}</MenuItem>
        </TextField>
      </Box>

      {!stats ? (
        <Typography color="text.secondary">{t('extras_dash_loading')}</Typography>
      ) : (
        <>
          {/* 四大指标卡 */}
          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Card elevation={0} sx={glassCard(isDark)}>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={600}>{t('extras_dash_today_words')}</Typography>
                  <Typography variant="h4" fontWeight={800} sx={{ color: '#2563EB', my: 0.5 }}>
                    {stats.todayWords.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">{t('extras_dash_words_unit')}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card elevation={0} sx={glassCard(isDark)}>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={600}>{t('extras_dash_total_words')}</Typography>
                  <Typography variant="h4" fontWeight={800} sx={{ color: '#059669', my: 0.5 }}>
                    {stats.totalWords.toLocaleString()}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">{stats.totalChapters} {t('extras_dash_chapters_unit')}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card elevation={0} sx={glassCard(isDark)}>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={600}>{t('extras_dash_streak')}</Typography>
                  <Typography variant="h4" fontWeight={800} sx={{ color: '#D97706', my: 0.5 }}>
                    {stats.streakDays}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">{t('extras_dash_streak_unit')}</Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Card elevation={0} sx={glassCard(isDark)}>
                <CardContent>
                  <Typography variant="caption" color="text.secondary" fontWeight={600}>{t('extras_dash_today_chapters')}</Typography>
                  <Typography variant="h4" fontWeight={800} sx={{ color: '#8B5CF6', my: 0.5 }}>
                    {stats.todayChapters}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">{t('extras_dash_chapters_done')}</Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          {/* 创作速率与字数走势折线图 */}
          <Paper elevation={0} sx={{ p: 2.5, ...glassCard(isDark) }}>
            <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 1.5 }}>
              {t('extras_dash_creation_chart_title')}
            </Typography>
            <CreationRateChart data={stats.history} height={260} />
          </Paper>

          {/* 情绪起伏波形图 + 爽点节奏雷达图 */}
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 2.5, height: '100%', ...glassCard(isDark) }}>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1, flexWrap: 'wrap', gap: 1 }}>
                  <Typography variant="subtitle1" fontWeight={700}>
                    {t('extras_dash_wave_chart_title')}
                  </Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <TextField
                      select
                      size="small"
                      value={benchmark}
                      onChange={(e) => handleBenchmarkChange(e.target.value as any)}
                      sx={{ minWidth: 130 }}
                      label={t('extras_dash_benchmark')}
                    >
                      <MenuItem value="classic">{t('extras_dash_bm_classic')}</MenuItem>
                      <MenuItem value="fast_hook">{t('extras_dash_bm_fast_hook')}</MenuItem>
                      <MenuItem value="steady">{t('extras_dash_bm_steady')}</MenuItem>
                      <MenuItem value="face_slap">{t('extras_dash_bm_face_slap')}</MenuItem>
                    </TextField>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => setShowTensionDialog(true)}
                    >
                      {t('extras_dash_btn_analyze')}
                    </Button>
                    <Button
                      variant="outlined"
                      color="secondary"
                      size="small"
                      onClick={() => setShowGoldenThreeDialog(true)}
                    >
                      {t('extras_golden_three_btn', '黄金三章连环比对')}
                    </Button>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => setShowRetentionDialog(true)}
                    >
                      {t('extras_retention_btn', '读者留存预测')}
                    </Button>
                  </Box>
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                  {t('extras_dash_wave_subtitle', '监测剧情平淡期与高潮爆发期，红线为章节实测，虚线为神作对标基准')}
                </Typography>
                {goldenThreeResult && (
                  <Box sx={{ mb: 1.5, p: 1.5, borderRadius: 1.5, bgcolor: isDark ? 'rgba(225, 29, 72, 0.08)' : 'rgba(225, 29, 72, 0.04)', border: '1px solid rgba(225, 29, 72, 0.2)' }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1, flexWrap: 'wrap', gap: 1 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Chip
                          size="small"
                          label={goldenThreeResult.verdictTitle}
                          color={goldenThreeResult.verdict === 'EXCELLENT' ? 'success' : goldenThreeResult.verdict === 'WARNING_DROP' ? 'error' : 'warning'}
                          sx={{ fontWeight: 600 }}
                        />
                        <Chip
                          size="small"
                          label={t('extras_golden_three_combined_fit', '综合拟合度: {score}%', { score: goldenThreeResult.combinedAlignmentScore })}
                          variant="outlined"
                        />
                        <Chip
                          size="small"
                          label={t('extras_golden_three_cliff_rating', '断章评级: {rating}', { rating: goldenThreeResult.cliffhangerRating })}
                          variant="outlined"
                        />
                      </Box>
                      <Button size="small" onClick={() => setGoldenThreeResult(null)}>
                        {t('extras_golden_three_back_single', '返回单章')}
                      </Button>
                    </Box>
                    {goldenThreeResult.handoffs.length > 0 && (
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                        {goldenThreeResult.handoffs.map((h, i) => (
                          <Chip
                            key={i}
                            size="small"
                            label={t('extras_golden_three_handoff_chip', '第{from}章→第{to}章: {status} (落差{drop}分)', { from: h.fromChapter, to: h.toChapter, status: h.status === 'CLIFF_DROP' ? t('extras_golden_three_status_cliff', '⚠️断崖失速') : h.status === 'SMOOTH' ? t('extras_golden_three_status_smooth', '✅平滑承接') : h.status, drop: h.drop })}
                            color={h.status === 'CLIFF_DROP' ? 'error' : h.status === 'SMOOTH' ? 'success' : 'default'}
                            variant="outlined"
                          />
                        ))}
                      </Box>
                    )}
                  </Box>
                )}
                {!goldenThreeResult && tensionResult && (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1, flexWrap: 'wrap' }}>
                    <Chip
                      size="small"
                      label={t('extras_tension_bm_fit', '标杆拟合度: {score}%', { score: tensionResult.benchmarkAlignmentScore })}
                      color={tensionResult.benchmarkAlignmentScore >= 75 ? 'success' : 'primary'}
                      variant="outlined"
                    />
                    <Chip
                      size="small"
                      label={t('extras_tension_climax', '最高潮: {seg} ({score}分)', { seg: tensionResult.climaxSegment, score: tensionResult.maxTension })}
                      sx={{ bgcolor: 'rgba(225, 29, 72, 0.1)', color: '#E11D48', fontWeight: 600 }}
                    />
                    <Chip
                      size="small"
                      label={t('extras_tension_avg_var', '均值: {avg} ｜ 波动: ±{variance}', { avg: tensionResult.avgTension, variance: tensionResult.tensionVariance })}
                      variant="outlined"
                    />
                  </Box>
                )}
                <Box sx={{ position: 'relative' }}>
                  {(tensionLoading || goldenThreeLoading || retentionLoading) && (
                    <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'rgba(255,255,255,0.55)', zIndex: 1, borderRadius: 1 }}>
                      <CircularProgress size={36} />
                    </Box>
                  )}
                  <Box sx={{ opacity: (tensionLoading || goldenThreeLoading || retentionLoading) ? 0.4 : 1, transition: 'opacity 0.2s' }}>
                    <EmotionWaveChart
                      height={240}
                      tensionPoints={
                    goldenThreeResult
                      ? goldenThreeResult.combinedCurve
                      : tensionResult
                        ? tensionResult.tensionCurve
                        : undefined
                  }
                  benchmarkPoints={
                    goldenThreeResult
                      ? goldenThreeResult.combinedBenchmarkCurve
                      : tensionResult
                        ? tensionResult.benchmarkCurve
                        : undefined
                  }
                  benchmarkName={
                    goldenThreeResult
                      ? goldenThreeResult.benchmarkName
                      : tensionResult?.benchmarkName
                  }
                  labels={
                    goldenThreeResult
                      ? goldenThreeResult.chaptersMetrics.flatMap((m) => m.segments)
                      : tensionResult?.segments
                  }
                    />
                  </Box>
                </Box>
                {goldenThreeResult && goldenThreeResult.recommendations.length > 0 && (
                  <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 1.5, bgcolor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }}>
                    <Typography variant="caption" fontWeight={700} sx={{ display: 'block', mb: 0.5, color: '#E11D48' }}>
                      {t('extras_golden_three_expert_advice', '黄金三章专家修改建议：')}
                    </Typography>
                    {goldenThreeResult.recommendations.map((rec, i) => (
                      <Typography key={i} variant="caption" sx={{ display: 'block', color: 'text.secondary', mb: 0.5 }}>
                        {rec}
                      </Typography>
                    ))}
                  </Box>
                )}
                {!goldenThreeResult && tensionResult?.pacingFeedback && tensionResult.pacingFeedback.length > 0 && (
                  <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 1.5, bgcolor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }}>
                    {tensionResult.pacingFeedback.map((f, i) => (
                      <Typography key={i} variant="caption" sx={{ display: 'block', color: 'text.secondary', mb: 0.5 }}>
                        {f}
                      </Typography>
                    ))}
                  </Box>
                )}
              </Paper>
            </Grid>
            <Grid item xs={12} md={6}>
              <Paper elevation={0} sx={{ p: 2.5, height: '100%', ...glassCard(isDark) }}>
                <Typography variant="subtitle1" fontWeight={700} sx={{ mb: 0.5 }}>
                  {t('extras_dash_radar_title')}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
                  {t('extras_dash_radar_subtitle')}
                </Typography>
                <RhythmRadarChart height={240} />
              </Paper>
            </Grid>

            {/* 商业成色与读者留存全景（读者留存预测结果） */}
            {retentionResult && (
              <Grid item xs={12}>
                <Paper elevation={0} sx={{ p: 2.5, ...glassCard(isDark) }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 1, mb: 1 }}>
                    <Typography variant="subtitle1" fontWeight={700}>
                      {t('extras_retention_result_title', '商业成色与读者留存全景')}
                    </Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                      <Chip
                        size="small"
                        color={retentionResult.overallGrade === 'S' ? 'success' : retentionResult.overallGrade === 'A' ? 'primary' : retentionResult.overallGrade === 'B' ? 'warning' : 'error'}
                        label={t('extras_retention_grade_label', '综合评级 {grade} · {desc}', { grade: retentionResult.overallGrade, desc: retentionResult.gradeDescription })}
                        sx={{ fontWeight: 600 }}
                      />
                      <Chip
                        size="small"
                        variant="outlined"
                        label={`${t('extras_retention_final_rate', '终局预计留存率')}: ${retentionResult.finalRetentionRate}%`}
                      />
                      <Chip
                        size="small"
                        variant="outlined"
                        label={`${t('extras_retention_total_churn', '累计流失漏斗')}: ${retentionResult.totalDropPct}%`}
                      />
                      <Button size="small" onClick={() => setRetentionResult(null)}>
                        {t('action_close', '关闭')}
                      </Button>
                    </Box>
                  </Box>
                  <Box sx={{ position: 'relative' }}>
                    {retentionLoading && (
                      <Box sx={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'rgba(255,255,255,0.55)', zIndex: 1, borderRadius: 1 }}>
                        <CircularProgress size={36} />
                      </Box>
                    )}
                    <Box sx={{ opacity: retentionLoading ? 0.4 : 1, transition: 'opacity 0.2s' }}>
                      <ReaderRetentionChart
                        retentionCurve={retentionResult.retentionCurve}
                    hotspots={retentionResult.dropoffHotspots}
                    height={280}
                      />
                    </Box>
                  </Box>
                  {retentionResult.dropoffHotspots.length > 0 && (
                    <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 1.5, bgcolor: isDark ? 'rgba(225, 29, 72, 0.06)' : 'rgba(225, 29, 72, 0.03)' }}>
                      <Typography variant="caption" fontWeight={700} sx={{ display: 'block', mb: 0.5, color: '#E11D48' }}>
                        {t('extras_retention_hotspots_title', '弃读跳出高危风险点与挽留改法')}：
                      </Typography>
                      {retentionResult.dropoffHotspots.map((h, i) => (
                        <Typography key={i} variant="caption" sx={{ display: 'block', color: 'text.secondary', mb: 0.5 }}>
                          {t('extras_retention_hotspot_item', '[{level}] {label}（预估跳出 {pct}%）：{reason} → {fix}', { level: h.riskLevel, label: h.segmentLabel, pct: h.estimatedDropPct, reason: h.reason, fix: h.fixSuggestion })}
                        </Typography>
                      ))}
                    </Box>
                  )}
                  {retentionResult.retentionAdvice.length > 0 && (
                    <Box sx={{ mt: 1.5, p: 1.5, borderRadius: 1.5, bgcolor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }}>
                      <Typography variant="caption" fontWeight={700} sx={{ display: 'block', mb: 0.5 }}>
                        {t('extras_retention_advice_title', '战略防跳出与留存优化建议')}：
                      </Typography>
                      {retentionResult.retentionAdvice.map((a, i) => (
                        <Typography key={i} variant="caption" sx={{ display: 'block', color: 'text.secondary', mb: 0.5 }}>
                          {a}
                        </Typography>
                      ))}
                    </Box>
                  )}
                </Paper>
              </Grid>
            )}
          </Grid>
        </>
      )}

      {/* 黄金三章连环多章比对弹窗 */}
      <Dialog open={showGoldenThreeDialog} onClose={() => setShowGoldenThreeDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('extras_golden_three_dialog_title', '黄金三章张力曲线重叠比对')}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {t('extras_golden_three_dialog_desc', '连环测算网络小说前三章张力波形，与商业神作标杆对齐，精准检测中段失速、首章吸睛度与章末断章悬念。')}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              select
              size="small"
              value={goldenThreeBm}
              onChange={(e) => setGoldenThreeBm(e.target.value as any)}
              sx={{ minWidth: 220 }}
              label={t('extras_benchmark_label', '商业神作标杆类型')}
            >
              <MenuItem value="classic">{t('extras_benchmark_classic', '经典商业递进三章标杆')}</MenuItem>
              <MenuItem value="upgrade_shuangwen">{t('extras_benchmark_upgrade', '升级爽文逆袭打脸标杆')}</MenuItem>
              <MenuItem value="fast_hook">{t('extras_benchmark_fast_hook', '快穿生死时速高压标杆')}</MenuItem>
              <MenuItem value="suspense_mystery">{t('extras_benchmark_suspense', '悬疑无限流惊悚标杆')}</MenuItem>
            </TextField>
          </Box>
          <TextField
            label={t('extras_golden_three_ch1', '第一章：开篇危机与入局')}
            multiline
            rows={4}
            value={ch1Input}
            onChange={(e) => setCh1Input(e.target.value)}
            placeholder={t('extras_golden_three_ch1_ph', '粘贴第 1 章正文草稿（前 30% 快速入局，章末留下微悬念钩子）……')}
            fullWidth
          />
          <TextField
            label={t('extras_golden_three_ch2', '第二章：承接升级防失速')}
            multiline
            rows={4}
            value={ch2Input}
            onChange={(e) => setCh2Input(e.target.value)}
            placeholder={t('extras_golden_three_ch2_ph', '粘贴第 2 章正文草稿（防中段失速塌陷，金手指与核心危机介入展开）……')}
            fullWidth
          />
          <TextField
            label={t('extras_golden_three_ch3', '第三章：首轮高潮与断章')}
            multiline
            rows={4}
            value={ch3Input}
            onChange={(e) => setCh3Input(e.target.value)}
            placeholder={t('extras_golden_three_ch3_ph', '粘贴第 3 章正文草稿（首卷爆发高潮与爽点释放，末尾强断章钩子）……')}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button
            size="small"
            onClick={() => {
              const sampleCh1 = '寒冬深夜，刺骨杀机骤起！\n黑衣刺客长刀撕裂长空，狠厉劈向少年头颅！“受死吧！”\n狂暴刀芒带着刺耳呼啸，鲜血瞬间染红青石砖。少年目眦欲裂，咬牙翻滚！\n身后的巨石崩裂成无数碎块，剧毒烟雾弥漫四周！生死一线，少年怀中神秘断玉突然迸发耀眼红芒！'
              const sampleCh2 = '断玉散发灼热高温，一股狂暴暖流瞬间涌入少年四肢百骸！\n刺客惊疑不定：“上古至宝？交出来饶你不死！”\n少年咬紧牙关，趁势翻身跃起，借着狂暴灵力一掌拍向刺客胸膛！\n轰！刺客被震退三步，嘴角溢血，眼中贪婪更盛：“好小子，今日你插翅难飞！”'
              const sampleCh3 = '“狂妄之徒，给我纳命来！”刺客怒吼，拔出背后淬毒短匕全力扑杀！\n生死刹那，少年眼神骤冷，断玉中猛然觉醒上古无上剑意！\n嗤啦！剑气如惊雷破空，瞬间贯穿刺客咽喉！反派轰然倒地，全场震撼死寂！\n少年拔出长剑，正欲喘息，长街尽头却突现数道更加可怖的黑袍身影，杀气封锁全城！'
              setCh1Input(sampleCh1)
              setCh2Input(sampleCh2)
              setCh3Input(sampleCh3)
              runGoldenThreeAnalysis(sampleCh1, sampleCh2, sampleCh3)
            }}
          >
            {t('extras_golden_three_sample_btn', '载入示范三章范例')}
          </Button>
          <Button onClick={() => setShowGoldenThreeDialog(false)}>{t('action_cancel')}</Button>
          <Button
            variant="contained"
            color="secondary"
            disabled={(!ch1Input.trim() && !ch2Input.trim() && !ch3Input.trim()) || goldenThreeLoading}
            onClick={() => runGoldenThreeAnalysis()}
          >
            {goldenThreeLoading ? t('extras_tension_analyzing', '分析中…') : t('extras_golden_three_start_btn', '开始三章联合比对')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 读者留存流失预测弹窗（与黄金三章共用三章草稿） */}
      <Dialog open={showRetentionDialog} onClose={() => setShowRetentionDialog(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('extras_retention_dialog_title', '商业网文读者留存流失预测模型')}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {t('extras_retention_dialog_desc', '基于前三章细粒度情绪张力、首章入局刺激、平淡注水期漏斗、跨章过渡断崖与末尾留钩，量化推导各章节读者留存衰减曲线并精准定位跳出高危点。')}
          </Typography>
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
            <TextField
              select
              size="small"
              value={retentionBm}
              onChange={(e) => setRetentionBm(e.target.value as any)}
              sx={{ minWidth: 220 }}
              label={t('extras_benchmark_label', '商业神作标杆类型')}
            >
              <MenuItem value="classic">{t('extras_benchmark_classic', '经典商业递进三章标杆')}</MenuItem>
              <MenuItem value="upgrade_shuangwen">{t('extras_benchmark_upgrade', '升级爽文逆袭打脸标杆')}</MenuItem>
              <MenuItem value="fast_hook">{t('extras_benchmark_fast_hook', '快穿生死时速高压标杆')}</MenuItem>
              <MenuItem value="suspense_mystery">{t('extras_benchmark_suspense', '悬疑无限流惊悚标杆')}</MenuItem>
            </TextField>
          </Box>
          <TextField
            label={t('extras_golden_three_ch1', '第一章：开篇危机与入局')}
            multiline
            rows={4}
            value={ch1Input}
            onChange={(e) => setCh1Input(e.target.value)}
            placeholder={t('extras_golden_three_ch1_ph', '粘贴第 1 章正文草稿（前 30% 快速入局，章末留下微悬念钩子）……')}
            fullWidth
          />
          <TextField
            label={t('extras_golden_three_ch2', '第二章：承接升级防失速')}
            multiline
            rows={4}
            value={ch2Input}
            onChange={(e) => setCh2Input(e.target.value)}
            placeholder={t('extras_golden_three_ch2_ph', '粘贴第 2 章正文草稿（防中段失速塌陷，金手指与核心危机介入展开）……')}
            fullWidth
          />
          <TextField
            label={t('extras_golden_three_ch3', '第三章：首轮高潮与断章')}
            multiline
            rows={4}
            value={ch3Input}
            onChange={(e) => setCh3Input(e.target.value)}
            placeholder={t('extras_golden_three_ch3_ph', '粘贴第 3 章正文草稿（首卷爆发高潮与爽点释放，末尾强断章钩子）……')}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button
            size="small"
            onClick={() => {
              const sampleCh1 = '寒冬深夜，刺骨杀机骤起！\n黑衣刺客长刀撕裂长空，狠厉劈向少年头颅！“受死吧！”\n狂暴刀芒带着刺耳呼啸，鲜血瞬间染红青石砖。少年目眦欲裂，咬牙翻滚！\n身后的巨石崩裂成无数碎块，剧毒烟雾弥漫四周！生死一线，少年怀中神秘断玉突然迸发耀眼红芒！'
              const sampleCh2 = '断玉散发灼热高温，一股狂暴暖流瞬间涌入少年四肢百骸！\n刺客惊疑不定：“上古至宝？交出来饶你不死！”\n少年咬紧牙关，趁势翻身跃起，借着狂暴灵力一掌拍向刺客胸膛！\n轰！刺客被震退三步，嘴角溢血，眼中贪婪更盛：“好小子，今日你插翅难飞！”'
              const sampleCh3 = '“狂妄之徒，给我纳命来！”刺客怒吼，拔出背后淬毒短匕全力扑杀！\n生死刹那，少年眼神骤冷，断玉中猛然觉醒上古无上剑意！\n嗤啦！剑气如惊雷破空，瞬间贯穿刺客咽喉！反派轰然倒地，全场震撼死寂！\n少年拔出长剑，正欲喘息，长街尽头却突现数道更加可怖的黑袍身影，杀气封锁全城！'
              setCh1Input(sampleCh1)
              setCh2Input(sampleCh2)
              setCh3Input(sampleCh3)
              runReaderRetention(sampleCh1, sampleCh2, sampleCh3)
            }}
          >
            {t('extras_retention_sample_high', '载入示范高留存三章 (S/A级)')}
          </Button>
          <Button
            size="small"
            onClick={() => {
              const sampleCh1 = '清晨的阳光洒进教室，同学们安静地早读。他翻开课本，按照顺序温习了昨天的知识点，整理了课堂笔记。课间休息时，他去走廊接了一杯温水，看了一会儿窗外的梧桐树，然后回到座位继续预习。'
              const sampleCh2 = '午饭过后，大家依次回到教室午休。他先整理好桌面，把文具摆放整齐，随后趴在桌上休息了半小时。下午的课程按时开始，老师讲述新的内容，他认真听讲并做了记录，没有遇到什么困难。'
              const sampleCh3 = '放学后，他步行回家，路上买了一些文具，顺便在小区门口看了看公告栏。晚饭后，他复习了两个小时，把当天的作业按时完成，然后收拾好书桌，洗漱之后就按时休息了。'
              setCh1Input(sampleCh1)
              setCh2Input(sampleCh2)
              setCh3Input(sampleCh3)
              runReaderRetention(sampleCh1, sampleCh2, sampleCh3)
            }}
          >
            {t('extras_retention_sample_drop', '载入示范断崖失速三章 (高危跳出)')}
          </Button>
          <Button onClick={() => setShowRetentionDialog(false)}>{t('action_cancel')}</Button>
          <Button
            variant="contained"
            disabled={(!ch1Input.trim() && !ch2Input.trim() && !ch3Input.trim()) || retentionLoading}
            onClick={() => runReaderRetention()}
          >
            {retentionLoading ? t('extras_tension_analyzing', '分析中…') : t('extras_retention_start_btn', '开始读者留存测算')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* 章节草稿张力测算弹窗 */}
      <Dialog open={showTensionDialog} onClose={() => setShowTensionDialog(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('extras_tension_dialog_title', '测算章节情绪张力波形')}</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, pt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            {t('extras_tension_dialog_desc', '粘贴当前正在创作的章节草稿，系统将通过冲突关键词、标点短句节奏、人物对峙与感官微表情，计算整章情绪起伏波形并与标杆对齐。')}
          </Typography>
          <TextField
            label={t('extras_tension_draft_label', '章节正文草稿')}
            multiline
            rows={8}
            value={draftInput}
            onChange={(e) => setDraftInput(e.target.value)}
            placeholder={t('extras_tension_draft_ph', '粘贴本章草稿内容……（建议 1,000 字以上以获得更精准波形）')}
            fullWidth
          />
        </DialogContent>
        <DialogActions>
          <Button
            size="small"
            onClick={() => {
              const sample = '寒风呼啸，江水刺骨冰冷。红围巾在夜色中如鲜血翻飞！少年毫不犹豫甩开外套跃入刺骨冰江！\n“救命！”呼救声微弱颤抖，水花狂暴激荡。他咬紧牙关，在生死边缘拉回了下沉的躯体！\n岸边警笛骤鸣，众人骇然围拢。危机暂退，两人精疲力竭倒在雪地中，大口喘息。'
              setDraftInput(sample)
              runTensionAnalysis(sample)
            }}
          >
            {t('extras_tension_sample_btn', '填入示范高潮草稿')}
          </Button>
          <Button onClick={() => setShowTensionDialog(false)}>{t('action_cancel')}</Button>
          <Button
            variant="contained"
            disabled={!draftInput.trim() || tensionLoading}
            onClick={() => runTensionAnalysis(draftInput)}
          >
            {tensionLoading ? t('extras_tension_analyzing', '分析中…') : t('extras_tension_start_btn', '开始比对')}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 5. 规范多格式导出（Word / Markdown / TXT）
// ---------------------------------------------------------------------------

function ExportPanel({ project }: { project: string }) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)

  const handleExport = async (format: 'docx' | 'epub' | 'shunn' | 'md' | 'txt') => {
    setError('')
    setInfo('')
    setExportingFormat(format)
    try {
      const res = await writingApi.export(project, format)
      if ((format === 'docx' || format === 'epub') && res.contentBase64) {
        // Base64 解码为二进制 Blob
        const byteCharacters = atob(res.contentBase64)
        const byteNumbers = new Array(byteCharacters.length)
        for (let i = 0; i < byteCharacters.length; i++) {
          byteNumbers[i] = byteCharacters.charCodeAt(i)
        }
        const byteArray = new Uint8Array(byteNumbers)
        const mimeType =
          format === 'epub'
            ? 'application/epub+zip'
            : 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        const blob = new Blob([byteArray], { type: mimeType })
        triggerDownload(blob, res.filename)
      } else {
        // 纯文本 / Markdown / Shunn 文稿
        const blob = new Blob([res.content || ''], { type: 'text/plain;charset=utf-8' })
        triggerDownload(blob, res.filename)
      }
      setInfo(t('extras_export_success', '成功导出 {chapters} 章、约 {words} 字：{filename}', { chapters: res.chapters, words: res.words.toLocaleString(), filename: res.filename }))
    } catch (e) {
      setError(t('extras_export_error', '导出失败: {error}', { error: friendlyError(e) }))
    } finally {
      setExportingFormat(null)
    }
  }

  const triggerDownload = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2.5 }}>
      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}
      {info && <Alert severity="success" onClose={() => setInfo('')}>{info}</Alert>}

      <Box>
        <Typography variant="h6" fontWeight={700}>
          {t('extras_export_title')}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t('extras_export_desc')}
        </Typography>
      </Box>

      <Grid container spacing={2.5}>
        {/* Word docx 导出卡 */}
        <Grid item xs={12} sm={6} md={4}>
          <Paper elevation={0} sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', ...glassCard(isDark) }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
              <DescriptionIcon sx={{ color: '#2563EB', fontSize: 28 }} />
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>{t('extras_export_docx_title')}</Typography>
                <Typography variant="caption" color="text.secondary">{t('extras_export_docx_tag')}</Typography>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1, mb: 2, lineHeight: 1.6 }}>
              {t('extras_export_docx_desc')}
            </Typography>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('docx')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'docx' ? t('extras_exporting_docx', '生成 docx 中…') : t('extras_export_docx_btn')}
            </Button>
          </Paper>
        </Grid>

        {/* EPUB 3.0 电子书导出卡 */}
        <Grid item xs={12} sm={6} md={4}>
          <Paper elevation={0} sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', ...glassCard(isDark) }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
              <MenuBookIcon sx={{ color: '#7C3AED', fontSize: 28 }} />
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>{t('extras_export_epub_title')}</Typography>
                <Typography variant="caption" color="text.secondary">{t('extras_export_epub_tag')}</Typography>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1, mb: 2, lineHeight: 1.6 }}>
              {t('extras_export_epub_desc')}
            </Typography>
            <Button
              variant="contained"
              sx={{ bgcolor: '#7C3AED', '&:hover': { bgcolor: '#6D28D9' } }}
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('epub')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'epub' ? t('extras_exporting_epub', '打包 epub 中…') : t('extras_export_epub_btn')}
            </Button>
          </Paper>
        </Grid>

        {/* William Shunn 标准投稿文稿 */}
        <Grid item xs={12} sm={6} md={4}>
          <Paper elevation={0} sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', ...glassCard(isDark) }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
              <AssignmentIcon sx={{ color: '#0284C7', fontSize: 28 }} />
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>{t('extras_export_shunn_title')}</Typography>
                <Typography variant="caption" color="text.secondary">{t('extras_export_shunn_tag')}</Typography>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1, mb: 2, lineHeight: 1.6 }}>
              {t('extras_export_shunn_desc')}
            </Typography>
            <Button
              variant="outlined"
              color="info"
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('shunn')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'shunn' ? t('extras_exporting_shunn', '生成文稿中…') : t('extras_export_shunn_btn')}
            </Button>
          </Paper>
        </Grid>

        {/* Markdown md 导出卡 */}
        <Grid item xs={12} sm={6} md={6}>
          <Paper elevation={0} sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', ...glassCard(isDark) }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
              <CodeIcon sx={{ color: '#059669', fontSize: 28 }} />
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>{t('extras_export_md_title')}</Typography>
                <Typography variant="caption" color="text.secondary">{t('extras_export_md_tag')}</Typography>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1, mb: 2, lineHeight: 1.6 }}>
              {t('extras_export_md_desc')}
            </Typography>
            <Button
              variant="outlined"
              color="success"
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('md')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'md' ? t('extras_exporting_md', '生成 md 中…') : t('extras_export_md_btn')}
            </Button>
          </Paper>
        </Grid>

        {/* TXT 导出卡 */}
        <Grid item xs={12} sm={6} md={6}>
          <Paper elevation={0} sx={{ p: 3, height: '100%', display: 'flex', flexDirection: 'column', ...glassCard(isDark) }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1.5 }}>
              <ArticleIcon sx={{ color: '#D97706', fontSize: 28 }} />
              <Box>
                <Typography variant="subtitle1" fontWeight={700}>{t('extras_export_txt_title')}</Typography>
                <Typography variant="caption" color="text.secondary">{t('extras_export_txt_tag')}</Typography>
              </Box>
            </Box>
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1, mb: 2, lineHeight: 1.6 }}>
              {t('extras_export_txt_desc')}
            </Typography>
            <Button
              variant="outlined"
              color="warning"
              startIcon={<DownloadIcon />}
              onClick={() => handleExport('txt')}
              disabled={!!exportingFormat}
            >
              {exportingFormat === 'txt' ? t('extras_exporting_txt', '拼接 txt 中…') : t('extras_export_txt_btn')}
            </Button>
          </Paper>
        </Grid>
      </Grid>
    </Box>
  )
}

