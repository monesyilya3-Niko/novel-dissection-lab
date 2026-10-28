// 命令面板 (Cmd+K)：全局快速跳转与操作。「墨」设计系统 v3 — WS-A5 Discoverability (~30 commands)。
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Dialog from '@mui/material/Dialog'
import Box from '@mui/material/Box'
import TextField from '@mui/material/TextField'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import InputAdornment from '@mui/material/InputAdornment'
import SearchIcon from '@mui/icons-material/Search'
import HomeIcon from '@mui/icons-material/Home'
import InsightsIcon from '@mui/icons-material/Insights'
import EditNoteIcon from '@mui/icons-material/EditNote'
import FactCheckIcon from '@mui/icons-material/FactCheck'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import TuneIcon from '@mui/icons-material/Tune'
import SettingsIcon from '@mui/icons-material/Settings'
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
import DarkModeIcon from '@mui/icons-material/DarkMode'
import LightModeIcon from '@mui/icons-material/LightMode'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import AddIcon from '@mui/icons-material/Add'
import PersonIcon from '@mui/icons-material/Person'
import MenuBookIcon from '@mui/icons-material/MenuBook'
import ViewModuleIcon from '@mui/icons-material/ViewModule'
import BiotechIcon from '@mui/icons-material/Biotech'
import PaletteIcon from '@mui/icons-material/Palette'
import ExtensionIcon from '@mui/icons-material/Extension'
import StyleIcon from '@mui/icons-material/Style'
import AssessmentIcon from '@mui/icons-material/Assessment'
import DashboardCustomizeIcon from '@mui/icons-material/DashboardCustomize'
import TranslateIcon from '@mui/icons-material/Translate'
import { useApp } from '../state/AppContext'
import { useThemeMode } from '../state/ThemeModeContext'
import { useUiModeOptional } from '../state/UiModeContext'
import { useI18n } from '../state/I18nContext'
import type { WorkbenchKey } from '../layout/WorkbenchNav'
import type { AssetKind } from '../types'

interface CommandItem {
  id: string
  label: string
  hint?: string
  icon: React.ReactNode
  group: string
  keywords?: string
  run: () => void
}

interface WorkbenchMetaItem {
  key: WorkbenchKey
  labelToken: string
  defaultLabel: string
  icon: React.ReactNode
  keywords: string
}

// ---------------------------------------------------------------------------
// Helpers for deep navigation (window-event bridge so sub-views can react)
// ---------------------------------------------------------------------------

function emitAssetFilter(kind: AssetKind) {
  window.dispatchEvent(new CustomEvent('novellab:asset-filter', { detail: { kind } }))
}

function emitWritingAction(action: string) {
  window.dispatchEvent(new CustomEvent('novellab:writing-action', { detail: { action } }))
}

function emitAnalysisTab(tab: string) {
  window.dispatchEvent(new CustomEvent('novellab:analysis-tab', { detail: { tab } }))
}

// ---------------------------------------------------------------------------
// Workbench meta (10 nav items) — unchanged
// ---------------------------------------------------------------------------

const WORKBENCH_META: WorkbenchMetaItem[] = [
  { key: 'home', labelToken: 'cmd_nav_home', defaultLabel: '首页', icon: <HomeIcon fontSize="small" />, keywords: 'home 首页 概览 dashboard' },
  { key: 'analysis', labelToken: 'cmd_nav_analysis', defaultLabel: '分析拆书', icon: <InsightsIcon fontSize="small" />, keywords: 'analysis 分析 拆书 book deconstruction' },
  { key: 'writing', labelToken: 'cmd_nav_writing', defaultLabel: '辅助写作 (沉浸创作室与工坊)', icon: <EditNoteIcon fontSize="small" />, keywords: 'writing 写作 创作室 studio 工坊 craft pipeline' },
  { key: 'quality', labelToken: 'cmd_nav_quality', defaultLabel: '质量检验', icon: <FactCheckIcon fontSize="small" />, keywords: 'quality 质量 检验 qc check guard' },
  { key: 'assets', labelToken: 'cmd_nav_assets', defaultLabel: '资产库', icon: <FolderOpenIcon fontSize="small" />, keywords: 'assets 资产 库 matrix library' },
  { key: 'advanced', labelToken: 'cmd_nav_advanced', defaultLabel: '高级功能', icon: <AutoAwesomeIcon fontSize="small" />, keywords: 'advanced 高级 蒸馏 distill batch' },
  { key: 'system', labelToken: 'cmd_nav_system', defaultLabel: '系统', icon: <TuneIcon fontSize="small" />, keywords: 'system 系统 status compliance' },
  { key: 'settings', labelToken: 'cmd_nav_settings', defaultLabel: '设置', icon: <SettingsIcon fontSize="small" />, keywords: 'settings 设置 config preferences' },
  { key: 'admin', labelToken: 'cmd_nav_admin', defaultLabel: '管理后台', icon: <AdminPanelSettingsIcon fontSize="small" />, keywords: 'admin 管理 后台 administration' },
  { key: 'help', labelToken: 'cmd_nav_help', defaultLabel: '帮助中心', icon: <HelpOutlineIcon fontSize="small" />, keywords: 'help 帮助 指南 教程 faq glossary docs' },
]

/** 简单模糊匹配：query 的字符按序出现在 target 中 */
function fuzzyMatch(query: string, target: string): boolean {
  const q = query.toLowerCase().replace(/\s+/g, '')
  const t = target.toLowerCase()
  if (!q) return true
  let ti = 0
  for (const ch of q) {
    ti = t.indexOf(ch, ti)
    if (ti === -1) return false
    ti += 1
  }
  return true
}

export default function CommandPalette() {
  const { t } = useI18n()
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const { setWorkbench, openHelp } = useApp()
  const { mode, setMode } = useThemeMode()
  const uiModeState = useUiModeOptional()
  const listRef = useRef<HTMLDivElement>(null)

  const items: CommandItem[] = useMemo(() => {
    const list: CommandItem[] = []
    const gWorkbench = t('cmd_group_workbench', '工作台')
    const gCreation = t('cmd_group_creation', '创作')
    const gAssets = t('cmd_group_assets', '资产')
    const gSystem = t('cmd_group_system', '系统')

    // ── 工作台跳转 (10) ──
    for (const wb of WORKBENCH_META) {
      const localizedLabel = t(wb.labelToken, wb.defaultLabel)
      list.push({
        id: `wb-${wb.key}`,
        label: `${t('cmd_goto_prefix', '前往')}${localizedLabel}`,
        hint: wb.key === 'home' ? 'Alt+1' : wb.key === 'writing' ? 'Alt+3' : undefined,
        icon: wb.icon,
        group: gWorkbench,
        keywords: wb.keywords,
        run: () => setWorkbench(wb.key),
      })
    }

    // ── 创作域 (7) ──
    list.push({
      id: 'creation-new-project',
      label: t('cmd_creation_new_project', '新建项目'),
      icon: <AddIcon fontSize="small" />,
      group: gCreation,
      keywords: 'new project 新建 项目 创建 create novel book writing',
      run: () => {
        setWorkbench('writing')
        requestAnimationFrame(() => emitWritingAction('new-project'))
      },
    })
    list.push({
      id: 'creation-new-outline',
      label: t('cmd_creation_new_outline', '新建大纲'),
      icon: <MenuBookIcon fontSize="small" />,
      group: gCreation,
      keywords: 'outline 大纲 规划 章节 outline chapter volume structure beats',
      run: () => {
        setWorkbench('writing')
        requestAnimationFrame(() => emitWritingAction('new-outline'))
      },
    })
    list.push({
      id: 'creation-new-character',
      label: t('cmd_creation_new_character', '新建人物'),
      icon: <PersonIcon fontSize="small" />,
      group: gCreation,
      keywords: 'character 人物 人设 角色 persona card name naming protagonist',
      run: () => {
        setWorkbench('writing')
        requestAnimationFrame(() => emitWritingAction('new-character'))
      },
    })
    list.push({
      id: 'creation-go-studio',
      label: t('cmd_creation_go_studio', '去写作 — 沉浸创作室'),
      icon: <EditNoteIcon fontSize="small" />,
      group: gCreation,
      keywords: 'studio 沉浸 创作室 写作 writing immersion draft editor',
      run: () => setWorkbench('writing'),
    })
    list.push({
      id: 'creation-go-pipeline',
      label: t('cmd_creation_go_pipeline', '去写作 — 工坊流水线'),
      icon: <ViewModuleIcon fontSize="small" />,
      group: gCreation,
      keywords: 'pipeline 工坊 流水线 craft inject generate pipeline workflow',
      run: () => setWorkbench('writing'),
    })
    list.push({
      id: 'creation-go-analysis',
      label: t('cmd_creation_go_analysis', '去拆书'),
      icon: <BiotechIcon fontSize="small" />,
      group: gCreation,
      keywords: 'analysis 拆书 导入 import deconstruction pipeline 书 book',
      run: () => {
        setWorkbench('analysis')
        requestAnimationFrame(() => emitAnalysisTab('import'))
      },
    })
    list.push({
      id: 'creation-view-results',
      label: t('cmd_creation_view_results', '查看分析结果'),
      icon: <AssessmentIcon fontSize="small" />,
      group: gCreation,
      keywords: 'result 结果 报告 report score analysis progress result report',
      run: () => {
        setWorkbench('analysis')
        requestAnimationFrame(() => emitAnalysisTab('result'))
      },
    })

    // ── 资产域 (7) — 带 kind 预筛选 ──
    list.push({
      id: 'asset-voice',
      label: t('cmd_asset_voice', '查看声线卡'),
      icon: <StyleIcon fontSize="small" />,
      group: gAssets,
      keywords: 'voice 声线 卡 voice-card character voice style narration',
      run: () => {
        setWorkbench('assets')
        requestAnimationFrame(() => emitAssetFilter('voice'))
      },
    })
    list.push({
      id: 'asset-genre-pack',
      label: t('cmd_asset_genre_pack', '查看题材包'),
      icon: <PaletteIcon fontSize="small" />,
      group: gAssets,
      keywords: 'genre 题材 包 genre-pack genre pack template tropes',
      run: () => {
        setWorkbench('assets')
        requestAnimationFrame(() => emitAssetFilter('genre_pack'))
      },
    })
    list.push({
      id: 'asset-distilled',
      label: t('cmd_asset_distilled', '查看蒸馏规则'),
      icon: <BiotechIcon fontSize="small" />,
      group: gAssets,
      keywords: 'distill 蒸馏 规则 distilled rule distill aggregate genre',
      run: () => {
        setWorkbench('assets')
        requestAnimationFrame(() => emitAssetFilter('distilled'))
      },
    })
    list.push({
      id: 'asset-prose-card',
      label: t('cmd_asset_prose_card', '查看文风卡'),
      icon: <PaletteIcon fontSize="small" />,
      group: gAssets,
      keywords: 'prose 文风 卡 prose-card style card prose style',
      run: () => {
        setWorkbench('assets')
        requestAnimationFrame(() => emitAssetFilter('prose_card'))
      },
    })
    list.push({
      id: 'asset-craft',
      label: t('cmd_asset_craft', '查看笔法卡'),
      icon: <ExtensionIcon fontSize="small" />,
      group: gAssets,
      keywords: 'craft 笔法 卡 craft-card technique craft writing skill trope deslop',
      run: () => {
        setWorkbench('assets')
        requestAnimationFrame(() => emitAssetFilter('craft'))
      },
    })
    list.push({
      id: 'asset-trope',
      label: t('cmd_asset_trope', '查看桥段库'),
      icon: <ExtensionIcon fontSize="small" />,
      group: gAssets,
      keywords: 'trope 桥段 套路 桥段库 shuangdian trope hook goldfinger poison distill',
      run: () => {
        setWorkbench('assets')
        requestAnimationFrame(() => emitAssetFilter('trope'))
      },
    })
    list.push({
      id: 'asset-report',
      label: t('cmd_asset_report', '查看报告'),
      icon: <AssessmentIcon fontSize="small" />,
      group: gAssets,
      keywords: 'report 报告 万字 拆书报告 craft report book report analysis',
      run: () => {
        setWorkbench('assets')
        requestAnimationFrame(() => emitAssetFilter('report'))
      },
    })

    // ── 系统域 (7) ──
    list.push({
      id: 'system-config-model',
      label: t('cmd_system_config_model', '配置模型'),
      icon: <TuneIcon fontSize="small" />,
      group: gSystem,
      keywords: 'model 模型 配置 config api key llm openai anthropic provider',
      run: () => setWorkbench('system'),
    })
    list.push({
      id: 'system-toggle-uimode',
      label: uiModeState?.mode === 'advanced'
        ? t('cmd_system_uimode_simple', '切换为简洁模式')
        : t('cmd_system_uimode_advanced', '切换为完整模式'),
      icon: <DashboardCustomizeIcon fontSize="small" />,
      group: gSystem,
      keywords: 'ui mode 简洁 完整 simple advanced toggle switch 模式 切换',
      run: () => {
        if (uiModeState) {
          uiModeState.setMode(uiModeState.mode === 'advanced' ? 'simple' : 'advanced')
        }
      },
    })
    list.push({
      id: 'system-help-start',
      label: t('cmd_system_help_start', '打开帮助 — 新手上路'),
      icon: <HelpOutlineIcon fontSize="small" />,
      group: gSystem,
      keywords: 'help 帮助 新手 上路 start guide workflow onboarding',
      run: () => openHelp('start', null),
    })
    list.push({
      id: 'system-help-glossary',
      label: t('cmd_system_help_glossary', '打开帮助 — 术语表'),
      icon: <TranslateIcon fontSize="small" />,
      group: gSystem,
      keywords: 'glossary 术语 词汇 词典 deslop poison trope distill qc craft voice genre terminology',
      run: () => openHelp('glossary', null),
    })
    list.push({
      id: 'system-help-guides',
      label: t('cmd_system_help_guides', '打开帮助 — 功能指南'),
      icon: <HelpOutlineIcon fontSize="small" />,
      group: gSystem,
      keywords: 'guide 指南 功能 guides feature docs tutorial howto',
      run: () => openHelp('guides', null),
    })
    list.push({
      id: 'system-help-faq',
      label: t('cmd_system_help_faq', '打开帮助 — 常见问题'),
      icon: <HelpOutlineIcon fontSize="small" />,
      group: gSystem,
      keywords: 'faq 常见问题 问答 help troubleshoot issue question',
      run: () => openHelp('faq', null),
    })
    // 主题切换
    list.push({
      id: 'theme-toggle',
      label: mode === 'dark' ? t('cmd_theme_light', '切换为亮色模式') : t('cmd_theme_dark', '切换为暗色模式'),
      icon: mode === 'dark' ? <LightModeIcon fontSize="small" /> : <DarkModeIcon fontSize="small" />,
      group: gSystem,
      keywords: 'theme mode dark light 模式 亮色 暗色 主题 night day toggle',
      run: () => setMode(mode === 'dark' ? 'light' : 'dark'),
    })

    return list
  }, [setWorkbench, openHelp, mode, setMode, uiModeState, t])

  const filtered = useMemo(() => {
    if (!query.trim()) return items
    return items.filter((it) =>
      fuzzyMatch(query, `${it.label} ${it.group} ${it.hint ?? ''} ${it.keywords ?? ''}`)
    )
  }, [items, query])

  const close = useCallback(() => {
    setOpen(false)
    setQuery('')
    setActiveIndex(0)
  }, [])

  const runItem = useCallback((it: CommandItem) => {
    close()
    // 让 Dialog 关闭动画先跑，再执行跳转
    requestAnimationFrame(() => it.run())
  }, [close])

  // Cmd+K / Ctrl+K 打开
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setOpen((o) => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // 列表内键盘导航
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIndex((i) => Math.min(i + 1, filtered.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIndex((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const it = filtered[activeIndex]
        if (it) runItem(it)
      } else if (e.key === 'Escape') {
        e.preventDefault()
        setOpen(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, filtered, activeIndex, runItem])

  // 滚动到高亮项
  useEffect(() => {
    listRef.current?.querySelector(`[data-index="${activeIndex}"]`)?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  let lastGroup = ''
  return (
    <Dialog
      open={open}
      onClose={close}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          position: 'fixed',
          top: '12vh',
          m: 0,
          borderRadius: 3,
          overflow: 'hidden',
          animation: 'cmdIn 0.18s cubic-bezier(0.2, 0.9, 0.3, 1.2) both',
          '@keyframes cmdIn': {
            from: { opacity: 0, transform: 'translateY(-8px) scale(0.98)' },
            to: { opacity: 1, transform: 'translateY(0) scale(1)' },
          },
        },
      }}
    >
      <Box sx={{ p: 1.5, pb: 0 }}>
        <TextField
          autoFocus
          fullWidth
          placeholder={t('cmd_search_placeholder', '搜索工作台或操作…')}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setActiveIndex(0)
          }}
          variant="outlined"
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" sx={{ color: 'text.secondary' }} />
              </InputAdornment>
            ),
            endAdornment: (
              <InputAdornment position="end">
                <Typography
                  variant="caption"
                  sx={{
                    px: 0.75,
                    py: 0.25,
                    borderRadius: 1,
                    bgcolor: 'action.hover',
                    color: 'text.secondary',
                    fontFamily: 'monospace',
                  }}
                >
                  ESC
                </Typography>
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': { borderRadius: 2 },
          }}
        />
      </Box>
      <Box ref={listRef} sx={{ maxHeight: 360, overflowY: 'auto', px: 1.5, pb: 1.5 }}>
        {filtered.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 4, textAlign: 'center' }}>
            {t('cmd_empty', '没有匹配的结果')}
          </Typography>
        ) : (
          <List dense disablePadding>
            {filtered.map((it, idx) => {
              const showGroup = it.group !== lastGroup
              lastGroup = it.group
              const active = idx === activeIndex
              return (
                <Box key={it.id}>
                  {showGroup && (
                    <Typography
                      variant="caption"
                      sx={{ px: 1.5, pt: 1.5, pb: 0.5, display: 'block', color: 'text.secondary', letterSpacing: '0.08em' }}
                    >
                      {it.group}
                    </Typography>
                  )}
                  <ListItemButton
                    data-index={idx}
                    selected={active}
                    onClick={() => runItem(it)}
                    onMouseEnter={() => setActiveIndex(idx)}
                    sx={{
                      borderRadius: 1.5,
                      '&.Mui-selected': {
                        bgcolor: 'action.selected',
                        '&:hover': { bgcolor: 'action.selected' },
                      },
                    }}
                  >
                    <ListItemIcon sx={{ minWidth: 36, color: active ? 'primary.main' : 'text.secondary' }}>
                      {it.icon}
                    </ListItemIcon>
                    <ListItemText
                      primary={it.label}
                      primaryTypographyProps={{ variant: 'body2', fontWeight: active ? 600 : 400 }}
                    />
                    {it.hint && (
                      <Typography variant="caption" color="text.secondary">
                        {it.hint}
                      </Typography>
                    )}
                  </ListItemButton>
                </Box>
              )
            })}
          </List>
        )}
      </Box>
      <Divider />
      <Box sx={{ px: 2, py: 1, display: 'flex', gap: 2 }}>
        {[
          t('cmd_shortcut_nav', '↑↓ 导航'),
          t('cmd_shortcut_select', '↵ 选择'),
          t('cmd_shortcut_close', 'esc 关闭'),
        ].map((item) => (
          <Typography key={item} variant="caption" color="text.secondary">
            {item}
          </Typography>
        ))}
      </Box>
    </Dialog>
  )
}

/** 命令面板触发按钮（放在 AppBar 上） */
export function CommandPaletteTrigger() {
  const { t } = useI18n()
  const openPalette = () => {
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true }))
  }
  return (
    <Box
      onClick={openPalette}
      sx={{
        display: { xs: 'none', sm: 'flex' },
        alignItems: 'center',
        gap: 1,
        px: 1.5,
        py: 0.75,
        borderRadius: 2,
        border: '1px solid rgba(255,255,255,0.3)',
        color: 'rgba(255,255,255,0.85)',
        cursor: 'pointer',
        fontSize: 13,
        minWidth: 180,
        '&:hover': { borderColor: 'rgba(255,255,255,0.6)', bgcolor: 'rgba(255,255,255,0.1)' },
      }}
    >
      <SearchIcon fontSize="small" />
      <Box component="span" sx={{ flex: 1 }}>
        {t('cmd_search_btn', '搜索…')}
      </Box>
      <Typography
        variant="caption"
        sx={{ px: 0.75, py: 0.25, borderRadius: 1, bgcolor: 'rgba(255,255,255,0.2)', fontFamily: 'monospace', fontSize: 10 }}
      >
        ⌘K
      </Typography>
    </Box>
  )
}
