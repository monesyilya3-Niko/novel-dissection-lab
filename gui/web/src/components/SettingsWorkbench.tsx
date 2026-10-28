// 设置工作台：阈值 / 写作 / 端口配置管理。
// P2-F12：数值字段即时校验（与后端 update_settings 规则对齐），非法时禁用保存；
// 保存成功后调用 refreshThresholds()，让 QC/写作面板即时用上新阈值。
import { useState, useEffect } from 'react'
import Box from '@mui/material/Box'
import ContextHelpButton from './ContextHelpButton'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import Paper from '@mui/material/Paper'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Divider from '@mui/material/Divider'
import Chip from '@mui/material/Chip'
import ToggleButton from '@mui/material/ToggleButton'
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup'
import { systemApi } from '../api/client'
import { friendlyError } from '../api/client'
import { useApp } from '../state/AppContext'
import { useUiMode } from '../state/UiModeContext'
import { useI18n } from '../state/I18nContext'
import type { TranslationKey } from '../i18n/translations'

interface Settings {
  port: number
  batchSize: number
  thresholds: { consistencyTarget: number; qualityPassLine: number; qualityWarnLine: number }
  writing: { defaultWords: number; maxAttempts: number }
  paths: Record<string, string>
  envOverrides: Record<string, string>
  saved: Record<string, unknown>
}

// 与后端 system_service.update_settings 的校验规则保持一致
export function validateSettingsField(
  name: 'consistencyTarget' | 'qualityPassLine' | 'qualityWarnLine' | 'defaultWords' | 'maxAttempts',
  raw: string,
  all: Record<string, string>,
  t?: (key: TranslationKey, fallback?: string) => string,
): string {
  const v = raw.trim()
  if (v === '') return t ? t('settings_err_required', '不能为空') : '不能为空'
  if (!/^-?\d+(\.\d+)?$/.test(v)) return t ? t('settings_err_nan', '请输入数字') : '请输入数字'
  const n = Number(v)
  if (name === 'defaultWords' || name === 'maxAttempts') {
    if (!Number.isInteger(n)) return t ? t('settings_err_integer', '必须为整数') : '必须为整数'
  }
  if (name === 'consistencyTarget' || name === 'qualityPassLine' || name === 'qualityWarnLine') {
    if (n < 0 || n > 100) return t ? t('settings_err_range_100', '必须在 0-100 之间') : '必须在 0-100 之间'
  }
  if (name === 'defaultWords' && (n < 100 || n > 20000)) return t ? t('settings_err_range_words', '必须在 100-20000 之间') : '必须在 100-20000 之间'
  if (name === 'maxAttempts' && (n < 1 || n > 10)) return t ? t('settings_err_range_attempts', '必须在 1-10 之间') : '必须在 1-10 之间'
  // 及格线必须 >= 警告线（交叉校验，用解析后的数值）
  const pl = name === 'qualityPassLine' ? n : Number(all.qualityPassLine)
  const wl = name === 'qualityWarnLine' ? n : Number(all.qualityWarnLine)
  if (!Number.isNaN(pl) && !Number.isNaN(wl) && pl < wl) {
    return name === 'qualityPassLine'
      ? (t ? t('settings_err_pass_gte_warn', '及格线必须 ≥ 警告线') : '及格线必须 ≥ 警告线')
      : (t ? t('settings_err_warn_lte_pass', '警告线必须 ≤ 及格线') : '警告线必须 ≤ 及格线')
  }
  return ''
}

const FIELD_NAMES = ['consistencyTarget', 'qualityPassLine', 'qualityWarnLine', 'defaultWords', 'maxAttempts'] as const
type FieldName = (typeof FIELD_NAMES)[number]

const FIELD_LABEL_KEYS: Record<FieldName, TranslationKey> = {
  consistencyTarget: 'settings_field_consistency_target',
  qualityPassLine: 'settings_field_quality_pass_line',
  qualityWarnLine: 'settings_field_quality_warn_line',
  defaultWords: 'settings_field_default_words',
  maxAttempts: 'settings_field_max_attempts',
}

const FIELD_HELPER_KEYS: Record<FieldName, TranslationKey> = {
  consistencyTarget: 'settings_helper_consistency_target',
  qualityPassLine: 'settings_helper_quality_pass_line',
  qualityWarnLine: 'settings_helper_quality_warn_line',
  defaultWords: 'settings_helper_default_words',
  maxAttempts: 'settings_helper_max_attempts',
}

export default function SettingsWorkbench() {
  const { t } = useI18n()
  const { refreshThresholds } = useApp()
  const { mode: uiMode, setMode: setUiMode } = useUiMode()
  const [settings, setSettings] = useState<Settings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  // 表单状态用字符串保存，避免非法输入被 Number() 吞成 NaN/0
  const [fields, setFields] = useState<Record<FieldName, string>>({
    consistencyTarget: '90',
    qualityPassLine: '75',
    qualityWarnLine: '60',
    defaultWords: '2400',
    maxAttempts: '3',
  })

  const loadSettings = async () => {
    setLoading(true)
    setError('')
    try {
      const d = await systemApi.settings() as Record<string, unknown>
      setSettings(d as unknown as Settings)
      const th = d.thresholds as Record<string, number> | undefined
      const wr = d.writing as Record<string, number> | undefined
      // deepToCamel 已将 snake_case 转为 camelCase
      setFields({
        consistencyTarget: String(th?.consistencyTarget ?? 90),
        qualityPassLine: String(th?.qualityPassLine ?? 75),
        qualityWarnLine: String(th?.qualityWarnLine ?? 60),
        defaultWords: String(wr?.defaultWords ?? 2400),
        maxAttempts: String(wr?.maxAttempts ?? 3),
      })
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadSettings() }, [])

  const fieldErrors = Object.fromEntries(
    FIELD_NAMES.map((n) => [n, validateSettingsField(n, fields[n], fields, t)]),
  ) as Record<FieldName, string>
  const hasError = FIELD_NAMES.some((n) => fieldErrors[n] !== '')

  const saveSettings = async () => {
    if (hasError) return
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const data = await systemApi.updateSettings({
        thresholds: {
          consistency_target: Number(fields.consistencyTarget),
          quality_pass_line: Number(fields.qualityPassLine),
          quality_warn_line: Number(fields.qualityWarnLine),
        },
        writing: {
          default_words: Number(fields.defaultWords),
          max_attempts: Number(fields.maxAttempts),
        },
      })
      setSettings(data as unknown as Settings)
      setMessage(t('settings_msg_saved'))
      // 阈值即时刷新：QC 合格线/写书目标分立即生效
      await refreshThresholds()
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setSaving(false)
    }
  }

  const resetSettings = async () => {
    // P2-F11/F13：重置二次确认
    if (!window.confirm(t('settings_confirm_reset'))) return
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const data = await systemApi.resetSettings()
      setSettings(data as unknown as Settings)
      setFields({
        consistencyTarget: '90',
        qualityPassLine: '75',
        qualityWarnLine: '60',
        defaultWords: '2400',
        maxAttempts: '3',
      })
      setMessage(t('settings_msg_reset'))
      await refreshThresholds()
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setSaving(false)
    }
  }

  const renderField = (name: FieldName) => (
    <TextField
      key={name}
      label={t(FIELD_LABEL_KEYS[name])} type="number" size="small" fullWidth
      value={fields[name]}
      onChange={(e) => setFields((f) => ({ ...f, [name]: e.target.value }))}
      error={fieldErrors[name] !== ''}
      helperText={fieldErrors[name] || t(FIELD_HELPER_KEYS[name])}
    />
  )

  if (loading) return <CircularProgress />
  if (error && !settings) return <Alert severity="error">{error}</Alert>

  return (
    <Box sx={{ maxWidth: 600, height: '100%', overflow: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center' }}>
        <Typography variant="h6" gutterBottom sx={{ flex: 1 }}>{t('settings_title')}</Typography>
        <ContextHelpButton guideKey="settings" />
      </Box>
      {message && <Alert severity="success" sx={{ mb: 2 }}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {/* 界面偏好：简洁/进阶切换（双持久化，立即生效） */}
      <Paper sx={{ p: 2, mb: 2 }} data-testid="settings-ui-mode">
        <Typography variant="subtitle2" gutterBottom>{t('settings_section_ui_mode', '界面偏好')}</Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
          {t('settings_ui_mode_desc', '简洁模式只显示核心功能（首页/分析/写作/质检），进阶模式显示全部工具。切换立即生效并自动保存。')}
        </Typography>
        <ToggleButtonGroup
          exclusive
          value={uiMode}
          onChange={(_, v) => { if (v) setUiMode(v) }}
          size="small"
          color="primary"
          aria-label={t('settings_ui_mode_aria', '界面模式')}
          data-testid="settings-ui-mode-toggle"
        >
          <ToggleButton value="simple" aria-label={t('settings_ui_mode_simple', '简洁')}>
            {t('settings_ui_mode_simple', '简洁')}
          </ToggleButton>
          <ToggleButton value="advanced" aria-label={t('settings_ui_mode_advanced', '进阶')}>
            {t('settings_ui_mode_advanced', '进阶')}
          </ToggleButton>
        </ToggleButtonGroup>
      </Paper>

      {/* 打分阈值 */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('settings_section_thresholds')}</Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 1.5, flexWrap: 'wrap' }}>
          {renderField('consistencyTarget')}
          {renderField('qualityPassLine')}
          {renderField('qualityWarnLine')}
        </Box>
      </Paper>

      {/* 写作设置 */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('settings_section_writing')}</Typography>
        <Box sx={{ display: 'flex', gap: 2, mb: 1.5, flexWrap: 'wrap' }}>
          {renderField('defaultWords')}
          {renderField('maxAttempts')}
        </Box>
      </Paper>

      {/* 操作按钮 */}
      <Box sx={{ display: 'flex', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <Button variant="contained" onClick={saveSettings} disabled={saving || hasError}>
          {saving ? <CircularProgress size={20} /> : t('settings_btn_save')}
        </Button>
        <Button variant="outlined" color="warning" onClick={resetSettings} disabled={saving}>
          {t('settings_btn_reset')}
        </Button>
      </Box>

      <Divider sx={{ my: 2 }} />

      {/* 只读信息 */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          {t('settings_section_service')} <Chip label={t('settings_chip_restart')} size="small" color="warning" />
        </Typography>
        <Typography variant="body2">{t('settings_port_prefix')}{settings?.port}</Typography>
        <Typography variant="body2">{t('settings_batch_size_prefix')}{settings?.batchSize}{t('settings_chars_unit')}</Typography>
        <Typography variant="caption" color="text.secondary">
          {t('settings_env_hint')}
        </Typography>
      </Paper>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('settings_section_paths')}</Typography>
        {settings?.paths && Object.entries(settings.paths).map(([k, v]) => (
          <Typography key={k} variant="body2" sx={{ fontSize: 12, fontFamily: 'monospace' }}>
            {k}: {v}
          </Typography>
        ))}
      </Paper>

      <Paper sx={{ p: 2 }}>
        <Typography variant="subtitle2" gutterBottom>{t('settings_section_env')}</Typography>
        {settings?.envOverrides && Object.entries(settings.envOverrides).map(([k, v]) => (
          <Typography key={k} variant="body2" sx={{ fontSize: 12, fontFamily: 'monospace' }}>
            {k}: {v || t('settings_env_unset')}
          </Typography>
        ))}
      </Paper>
    </Box>
  )
}

