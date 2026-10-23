// M5 系统与合规工作台：系统状态 / 版权合规 / 模型配置 / 设置。
import { useState, useEffect } from 'react'
import Box from '@mui/material/Box'
import ContextHelpButton from './ContextHelpButton'
import Tabs from '@mui/material/Tabs'
import Tab from '@mui/material/Tab'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import Paper from '@mui/material/Paper'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Chip from '@mui/material/Chip'
import { systemApi } from '../api/client'
import ModelManager from './ModelManager'
import { friendlyError } from '../api/client'
import { useI18n } from '../state/I18nContext'

export default function SystemWorkbench() {
  const { t } = useI18n()
  const [tab, setTab] = useState(0)
  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', borderBottom: 1, borderColor: 'divider', pr: 1 }}>
        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ flex: 1, px: 2 }}>
          <Tab label={t('system_tab_status')} />
          <Tab label={t('system_tab_compliance')} />
          <Tab label={t('system_tab_models')} />
          <Tab label={t('system_tab_settings')} />
        </Tabs>
        <ContextHelpButton guideKey="system" />
      </Box>
      <Box sx={{ flex: 1, minHeight: 0, overflow: 'auto', p: 2 }}>
        {tab === 0 && <SystemStatusPanel />}
        {tab === 1 && <CompliancePanel />}
        {tab === 2 && <ModelManager />}
        {tab === 3 && <SettingsPanel />}
      </Box>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 系统状态
// ---------------------------------------------------------------------------

function SystemStatusPanel() {
  const { t } = useI18n()
  const [status, setStatus] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await systemApi.status()
      setStatus(data as Record<string, unknown>)
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return <CircularProgress />
  if (error) return <Alert severity="error">{error}</Alert>
  if (!status) return null

  const disk = status.disk as Record<string, number>
  const counts = status.counts as Record<string, unknown>
  const model = status.model as Record<string, unknown>
  const paths = status.paths as Record<string, string>

  const fmtSize = (bytes: number) => {
    if (bytes > 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(1)} MB`
    if (bytes > 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${bytes} B`
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">{t('system_status_title')}</Typography>
        <Button variant="outlined" size="small" onClick={load}>{t('system_status_refresh')}</Button>
      </Box>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('system_disk_title')}</Typography>
        <Typography variant="body2">{t('system_disk_assets')}{fmtSize(Number(disk.assetsBytes ?? 0))} | {t('system_disk_reports')}{fmtSize(Number(disk.reportsBytes ?? 0))}</Typography>
        <Typography variant="body2">{t('system_disk_corpus')}{fmtSize(Number(disk.corpusBytes ?? 0))} | {t('system_disk_novel')}{fmtSize(Number(disk.novelBytes ?? 0))}</Typography>
        <Typography variant="body2">{t('system_disk_db')}{fmtSize(Number(disk.dbBytes ?? 0))} | {t('system_disk_total')}{fmtSize(Number(disk.totalBytes ?? 0))}</Typography>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('system_counts_title')}</Typography>
        <Typography variant="body2">
          {t('system_counts_assets_prefix')}{String(counts.assets ?? 0)}{t('system_counts_assets_unit')}{String(counts.reports ?? 0)}{t('system_counts_reports_unit')}{((counts.bookNames ?? counts.book_names ?? []) as string[]).length}{t('system_counts_books_unit')}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {((counts.bookNames ?? counts.book_names ?? []) as string[]).join('、')}
        </Typography>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('system_model_title')}</Typography>
        <Chip label={model.configured ? t('system_model_configured') : t('system_model_unconfigured')} size="small" color={model.configured ? 'success' : 'warning'} />
        {Array.isArray(model.models) && (model.models as Record<string, unknown>[]).map((m, i) => (
          <Typography key={i} variant="body2">{String(m.id)} — {String(m.name)}</Typography>
        ))}
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('system_paths_title')}</Typography>
        {Object.entries(paths).map(([k, v]) => (
          <Typography key={k} variant="body2" sx={{ fontSize: 12, fontFamily: 'monospace' }}>
            {k}: {v}
          </Typography>
        ))}
      </Paper>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 版权合规
// ---------------------------------------------------------------------------

function CompliancePanel() {
  const { t } = useI18n()
  const [results, setResults] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const doScan = async () => {
    setLoading(true)
    setError('')
    try {
      const data = await systemApi.compliance()
      setResults(data as Record<string, unknown>)
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setLoading(false)
    }
  }

  const items = (results?.results ?? []) as { name: string; verdict: string; errors: string[]; warns: string[] }[]
  const summary = results?.summary as Record<string, number> | undefined

  return (
    <Box>
      <Typography variant="h6" gutterBottom>{t('system_comp_title')}</Typography>
      <Button variant="contained" onClick={doScan} disabled={loading} sx={{ mb: 2 }}>
        {loading ? <CircularProgress size={20} /> : t('system_comp_btn_scan')}
      </Button>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {summary && (
        <Alert severity={summary.rejected > 0 ? 'error' : summary.warned > 0 ? 'warning' : 'success'} sx={{ mb: 2 }}>
          {t('system_comp_summary_total')}{summary.total}{t('system_comp_summary_assets')}{summary.passed} PASS / {summary.warned} WARN / {summary.rejected} REJECT
        </Alert>
      )}
      {items.map((r) => (
        <Paper key={r.name} sx={{ p: 1.5, mb: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography variant="body2" sx={{ flex: 1 }}>{r.name}</Typography>
            <Chip
              label={r.verdict} size="small"
              color={r.verdict === 'PASS' ? 'success' : r.verdict === 'WARN' ? 'warning' : 'error'}
            />
          </Box>
          {(r.errors ?? []).map((e, i) => (
            <Typography key={i} variant="caption" sx={{ color: 'error.main', display: 'block' }}>{e}</Typography>
          ))}
          {(r.warns ?? []).map((w, i) => (
            <Typography key={i} variant="caption" sx={{ color: 'warning.main', display: 'block' }}>{w}</Typography>
          ))}
        </Paper>
      ))}
    </Box>
  )
}

// ---------------------------------------------------------------------------
// 设置
// ---------------------------------------------------------------------------

function SettingsPanel() {
  const { t } = useI18n()
  const [settings, setSettings] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    systemApi.settings()
      .then((data) => setSettings(data as Record<string, unknown>))
      .catch((e) => setError(friendlyError(e)))
  }, [])

  if (error) return <Alert severity="error">{error}</Alert>
  if (!settings) return <CircularProgress />

  const paths = (settings.paths ?? {}) as Record<string, string>
  const env = (settings.envOverrides ?? {}) as Record<string, string>

  return (
    <Box>
      <Typography variant="h6" gutterBottom>{t('system_settings_title')}</Typography>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('system_settings_service')}</Typography>
        <Typography variant="body2">{t('system_settings_port')}{String(settings.port ?? '-')}</Typography>
        <Typography variant="body2">{t('system_settings_batch_size')}{String(settings.batchSize ?? settings.batch_size ?? '-')}{t('system_settings_chars_unit')}</Typography>
      </Paper>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('system_paths_title')}</Typography>
        {Object.entries(paths).map(([k, v]) => (
          <Typography key={k} variant="body2" sx={{ fontSize: 12, fontFamily: 'monospace' }}>{k}: {String(v)}</Typography>
        ))}
      </Paper>
      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('system_settings_env_title')}</Typography>
        {Object.entries(env).map(([k, v]) => (
          <Typography key={k} variant="body2" sx={{ fontSize: 12, fontFamily: 'monospace' }}>
            {k}: {v ? String(v) : t('system_settings_env_unset')}
          </Typography>
        ))}
      </Paper>
      <Alert severity="info" sx={{ mt: 2 }}>
        {t('system_settings_notice')}
      </Alert>
    </Box>
  )
}

