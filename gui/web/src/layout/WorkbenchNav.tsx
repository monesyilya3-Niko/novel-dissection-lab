// 左侧导航栏：工作台切换（Simple/Advanced 双模式 + e2e 稳定 data-testid）。「墨」设计系统 v2。
import React, { useEffect, useState } from 'react'
import List from '@mui/material/List'
import ListItemButton from '@mui/material/ListItemButton'
import ListItemIcon from '@mui/material/ListItemIcon'
import ListItemText from '@mui/material/ListItemText'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Divider from '@mui/material/Divider'
import Collapse from '@mui/material/Collapse'
import HomeIcon from '@mui/icons-material/Home'
import InsightsIcon from '@mui/icons-material/Insights'
import EditNoteIcon from '@mui/icons-material/EditNote'
import FactCheckIcon from '@mui/icons-material/FactCheck'
import FolderOpenIcon from '@mui/icons-material/FolderOpen'
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome'
import SettingsIcon from '@mui/icons-material/Settings'
import TuneIcon from '@mui/icons-material/Tune'
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings'
import HelpOutlineIcon from '@mui/icons-material/HelpOutline'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import ExpandLessIcon from '@mui/icons-material/ExpandLess'
import { ink } from '../ink'
import { useI18n } from '../state/I18nContext'
import type { UIMode } from '../state/UiModeContext'

export type WorkbenchKey =
  | 'home'
  | 'analysis'
  | 'writing'
  | 'quality'
  | 'assets'
  | 'advanced'
  | 'system'
  | 'settings'
  | 'admin'
  | 'help'

export interface WorkbenchNavItem {
  key: WorkbenchKey
  label: string
  icon: React.ReactNode
}

export interface WorkbenchNavProps {
  active: WorkbenchKey
  onChange: (key: WorkbenchKey) => void
  /** UI 模式：simple 4+2 精简，advanced 全量。未传时默认 advanced 以兼容旧单测/e2e。 */
  mode?: UIMode
  /** 是否已登录管理员：仅 true 时展示 admin 入口。未传时默认 false。 */
  isAdmin?: boolean
}

export interface NavGroupDef {
  id: string
  title: string
  items: WorkbenchNavItem[]
  collapsible: boolean
  defaultOpen: boolean
  /** simple 模式下的管理区以 subtle 样式呈现（更淡、更紧凑）。 */
  subtle?: boolean
}

function getNavItemDefs(t: (k: string, fb?: string) => string): Record<WorkbenchKey, WorkbenchNavItem> {
  return {
    home: { key: 'home', label: t('nav_home', '首页'), icon: <HomeIcon /> },
    analysis: { key: 'analysis', label: t('nav_analysis', '分析拆书'), icon: <InsightsIcon /> },
    writing: { key: 'writing', label: t('nav_writing', '辅助写作'), icon: <EditNoteIcon /> },
    quality: { key: 'quality', label: t('nav_quality', '质量检验'), icon: <FactCheckIcon /> },
    assets: { key: 'assets', label: t('nav_assets', '资产库'), icon: <FolderOpenIcon /> },
    advanced: { key: 'advanced', label: t('nav_advanced', '高级功能'), icon: <AutoAwesomeIcon /> },
    system: { key: 'system', label: t('nav_system', '系统'), icon: <TuneIcon /> },
    settings: { key: 'settings', label: t('nav_settings', '设置'), icon: <SettingsIcon /> },
    admin: { key: 'admin', label: t('nav_admin', '管理后台'), icon: <AdminPanelSettingsIcon /> },
    help: { key: 'help', label: t('nav_help', '帮助中心'), icon: <HelpOutlineIcon /> },
  }
}

/**
 * 构建导航分组：供渲染层与单测复用。
 * - Primary（始终可见，4 项）：home, analysis, writing, quality
 * - More（可折叠，simple 默认收起，advanced 默认展开）：assets, advanced
 * - Management（system, settings 始终；admin 仅 isAdmin 时）：simple 时 subtle 样式
 * - Help（单项始终可见）
 */
export function buildNavGroups(
  t: (k: string, fb?: string) => string,
  mode: UIMode,
  isAdmin: boolean,
): NavGroupDef[] {
  const defs = getNavItemDefs(t)
  return [
    {
      id: 'primary',
      title: t('nav_group_create', '创作'),
      items: [defs.home, defs.analysis, defs.writing, defs.quality],
      collapsible: false,
      defaultOpen: true,
    },
    {
      id: 'more',
      title: t('nav_group_more', '更多工具'),
      items: [defs.assets, defs.advanced],
      collapsible: true,
      defaultOpen: mode === 'advanced',
    },
    {
      id: 'manage',
      title: t('nav_group_manage', '管理'),
      items: isAdmin ? [defs.system, defs.settings, defs.admin] : [defs.system, defs.settings],
      collapsible: false,
      defaultOpen: true,
      subtle: mode === 'simple',
    },
    {
      id: 'help',
      title: t('nav_group_help', '帮助'),
      items: [defs.help],
      collapsible: false,
      defaultOpen: true,
    },
  ]
}

export default function WorkbenchNav({ active, onChange, mode = 'advanced', isAdmin = false }: WorkbenchNavProps) {
  const { t } = useI18n()
  const effectiveMode: UIMode = mode ?? 'advanced'
  const groups = buildNavGroups(t, effectiveMode, !!isAdmin)

  // "更多工具"折叠状态：simple 默认收起，advanced 默认展开；随 mode 切换自动同步。
  const [moreOpen, setMoreOpen] = useState(() => effectiveMode === 'advanced')
  useEffect(() => {
    setMoreOpen(effectiveMode === 'advanced')
  }, [effectiveMode])

  const navItemSx = () => ({
    borderRadius: 2,
    mb: 0.5,
    py: 1.1,
    position: 'relative' as const,
    '&.Mui-selected': {
      bgcolor: (theme: { palette: { mode: string } }) =>
        theme.palette.mode === 'dark' ? `${ink.cinnabar}26` : ink.cinnabarSoft,
      color: (theme: { palette: { mode: string } }) =>
        theme.palette.mode === 'dark' ? '#93B4FD' : ink.cinnabarDeep,
      '& .MuiListItemIcon-root': { color: 'inherit' },
      '&:hover': {
        bgcolor: (theme: { palette: { mode: string } }) =>
          theme.palette.mode === 'dark' ? `${ink.cinnabar}33` : '#E4EBFD',
      },
      '&::before': {
        content: '""',
        position: 'absolute',
        left: 0,
        top: '20%',
        bottom: '20%',
        width: 3,
        borderRadius: 2,
        bgcolor: ink.cinnabar,
      },
    },
    '&:hover': {
      bgcolor: 'action.hover',
    },
  })

  const renderNavItem = (item: WorkbenchNavItem) => {
    const selected = active === item.key
    return (
      <ListItemButton
        key={item.key}
        data-testid={`nav-${item.key}`}
        selected={selected}
        onClick={() => onChange(item.key)}
        sx={navItemSx()}
      >
        <ListItemIcon sx={{ minWidth: 38, color: selected ? 'inherit' : 'text.secondary' }}>
          {item.icon}
        </ListItemIcon>
        <ListItemText
          primary={item.label}
          primaryTypographyProps={{ fontSize: 14, fontWeight: selected ? 700 : 400 }}
        />
      </ListItemButton>
    )
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', py: 1.5 }}>
      {groups.map((group, gi) => {
        const isMore = group.collapsible
        const isSubtleManage = group.id === 'manage' && group.subtle
        if (isMore) {
          return (
            <React.Fragment key={group.id}>
              {gi > 0 && <Divider sx={{ mx: 2, my: 1 }} />}
              <ListItemButton
                data-testid="nav-more-toggle"
                onClick={() => setMoreOpen((o) => !o)}
                sx={{
                  borderRadius: 2,
                  mx: 1.5,
                  py: 0.9,
                  color: 'text.secondary',
                  '&:hover': { bgcolor: 'action.hover', color: 'text.primary' },
                }}
              >
                <ListItemIcon sx={{ minWidth: 38, color: 'inherit' }}>
                  <AutoAwesomeIcon fontSize="small" />
                </ListItemIcon>
                <ListItemText
                  primary={group.title}
                  primaryTypographyProps={{ fontSize: 13, fontWeight: 600 }}
                />
                {moreOpen ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
              </ListItemButton>
              {moreOpen && <Collapse in={moreOpen} timeout={0} unmountOnExit>
                <List component="nav" disablePadding sx={{ px: 1.5, pt: 0.5 }}>
                  {group.items.map(renderNavItem)}
                </List>
              </Collapse>}
            </React.Fragment>
          )
        }

        // subtle 管理区：simple 模式下更紧凑、更淡
        return (
          <React.Fragment key={group.id}>
            {gi > 0 && <Divider sx={{ mx: 2, my: 1 }} />}
            <Box sx={isSubtleManage ? { opacity: 0.92 } : undefined}>
              <Typography
                variant="caption"
                sx={{
                  px: 2.5,
                  pb: 0.5,
                  color: isSubtleManage ? 'text.secondary' : 'text.secondary',
                  fontWeight: 600,
                  letterSpacing: isSubtleManage ? '0.2em' : '0.25em',
                  fontSize: isSubtleManage ? 10 : 11,
                  opacity: isSubtleManage ? 0.85 : 1,
                }}
              >
                {group.title}
              </Typography>
              <List component="nav" disablePadding sx={{ px: 1.5 }}>
                {group.items.map(renderNavItem)}
              </List>
            </Box>
          </React.Fragment>
        )
      })}
      <Box sx={{ flex: 1 }} />
      <Box sx={{ px: 2.5, pb: 1 }}>
        <Typography variant="caption" color="text.secondary" sx={{ letterSpacing: '0.1em' }}>
          v1.0.0
        </Typography>
      </Box>
    </Box>
  )
}
