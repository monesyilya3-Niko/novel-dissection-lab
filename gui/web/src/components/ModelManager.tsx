// 模型管理面板：自定义 API/模型的增删改查与测试。
import { useState, useEffect, useCallback } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import MenuItem from '@mui/material/MenuItem'
import Paper from '@mui/material/Paper'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import Chip from '@mui/material/Chip'
import Dialog from '@mui/material/Dialog'
import DialogTitle from '@mui/material/DialogTitle'
import DialogContent from '@mui/material/DialogContent'
import DialogActions from '@mui/material/DialogActions'
import AddIcon from '@mui/icons-material/Add'
import EditIcon from '@mui/icons-material/Edit'
import DeleteIcon from '@mui/icons-material/Delete'
import PlayArrowIcon from '@mui/icons-material/PlayArrow'
import KeyIcon from '@mui/icons-material/Key'
import { modelApi } from '../api/client'
import { friendlyError } from '../api/client'
import { useI18n } from '../state/I18nContext'

interface ModelInfo {
  id: string
  label: string
  protocol: string
  baseUrl: string
  modelName: string
  roles: string[]
  hasKey: boolean
  note?: string
}

interface Preset {
  name: string
  label: string
  protocol: string
  baseUrl: string
  modelName: string
}

export default function ModelManager() {
  const { t } = useI18n()
  const [models, setModels] = useState<ModelInfo[]>([])
  const [presets, setPresets] = useState<Preset[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  // Dialog state
  const [showAdd, setShowAdd] = useState(false)
  const [editing, setEditing] = useState<ModelInfo | null>(null)
  const [showKey, setShowKey] = useState<string | null>(null)
  const [apiKey, setApiKey] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState<string | null>(null)

  // Form state
  const [form, setForm] = useState({
    id: '', label: '', protocol: 'openai', baseUrl: '', modelName: '', note: '',
  })

  const loadModels = useCallback(async () => {
    try {
      const data = await modelApi.list()
      setModels((data.models ?? []) as ModelInfo[])
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setLoading(false)
    }
  }, [])

  const loadPresets = useCallback(async () => {
    try {
      const data = await modelApi.presets()
      setPresets((data.presets ?? []) as Preset[])
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    loadModels()
    loadPresets()
  }, [loadModels, loadPresets])

  const resetForm = () => setForm({ id: '', label: '', protocol: 'openai', baseUrl: '', modelName: '', note: '' })

  const openAdd = () => {
    resetForm()
    setEditing(null)
    setShowAdd(true)
  }

  const openEdit = (m: ModelInfo) => {
    setForm({
      id: m.id, label: m.label, protocol: m.protocol,
      baseUrl: m.baseUrl, modelName: m.modelName, note: m.note || '',
    })
    setEditing(m)
    setShowAdd(true)
  }

  const applyPreset = (p: Preset) => {
    setForm({
      id: p.name, label: p.label, protocol: p.protocol,
      baseUrl: p.baseUrl, modelName: p.modelName, note: '',
    })
  }

  const saveModel = async () => {
    if (saving) return
    setSaving(true)
    setMessage('')
    setError('')
    try {
      const body: Record<string, unknown> = {
        id: form.id, label: form.label, protocol: form.protocol,
        base_url: form.baseUrl, model_name: form.modelName,
      }
      if (form.note) body.note = form.note

      if (editing) {
        await modelApi.update(editing.id, body)
      } else {
        await modelApi.add(body)
      }
      setMessage(editing ? t('model_mgr_msg_updated') : t('model_mgr_msg_added'))
      setShowAdd(false)
      loadModels()
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setSaving(false)
    }
  }

  const deleteModel = async (id: string) => {
    if (!confirm(t('model_mgr_confirm_delete') + id + '？')) return
    try {
      await modelApi.delete(id)
      setMessage(`${id}${t('model_mgr_msg_deleted')}`)
      loadModels()
    } catch (e) {
      setError(friendlyError(e))
    }
  }

  const saveKey = async () => {
    if (!showKey || !apiKey || saving) return
    setSaving(true)
    try {
      await modelApi.setKey(showKey, apiKey)
      setMessage(t('model_mgr_msg_key_saved'))
      setShowKey(null)
      setApiKey('')
      loadModels()
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setSaving(false)
    }
  }

  const testModel = async (id: string) => {
    setTesting(id)
    setMessage('')
    try {
      const data = await modelApi.test(id)
      if (data.success) {
        setMessage(`${id}${t('model_mgr_msg_test_ok')}`)
      } else {
        setError(`${id}${t('model_mgr_msg_test_fail')}${String(data.error ?? '未知错误')}`)
      }
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setTesting(null)
    }
  }

  if (loading) return <CircularProgress />

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
        <Typography variant="h6">{t('model_mgr_title')}</Typography>
        <Button variant="contained" startIcon={<AddIcon />} onClick={openAdd}>{t('model_mgr_add_btn')}</Button>
      </Box>

      {message && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage('')}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {models.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>{t('model_mgr_empty_hint')}</Alert>
      )}

      {models.map((m) => (
        <Paper key={m.id} sx={{ p: 2, mb: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle2">
                {m.label} <Chip label={m.id} size="small" />
                <Chip label={m.protocol} size="small" color="primary" variant="outlined" sx={{ ml: 0.5 }} />
                {m.hasKey && <Chip label={t('model_mgr_chip_key_set')} size="small" color="success" sx={{ ml: 0.5 }} />}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12 }}>
                {m.modelName} @ {m.baseUrl}
              </Typography>
              {m.roles.length > 0 && (
                <Typography variant="caption" color="text.secondary">
                  {t('model_mgr_role_prefix')}{m.roles.join(', ')}
                </Typography>
              )}
            </Box>
            <Box sx={{ display: 'flex', gap: 1, flexShrink: 0 }}>
              <Button size="small" startIcon={<PlayArrowIcon />} onClick={() => testModel(m.id)} disabled={testing === m.id}>
                {testing === m.id ? t('model_mgr_btn_testing') : t('model_mgr_btn_test')}
              </Button>
              <Button size="small" startIcon={<KeyIcon />} onClick={() => { setShowKey(m.id); setApiKey('') }}>
                {t('model_mgr_btn_key')}
              </Button>
              <Button size="small" startIcon={<EditIcon />} onClick={() => openEdit(m)}>
                {t('model_mgr_btn_edit')}
              </Button>
              <Button size="small" color="error" startIcon={<DeleteIcon />} onClick={() => deleteModel(m.id)}>
                {t('model_mgr_btn_delete')}
              </Button>
            </Box>
          </Box>
        </Paper>
      ))}

      {/* 添加/编辑对话框 */}
      <Dialog open={showAdd} onClose={() => setShowAdd(false)} maxWidth="sm" fullWidth>
        <DialogTitle>{editing ? `${t('model_mgr_dialog_edit_prefix')}${editing.id}` : t('model_mgr_dialog_add')}</DialogTitle>
        <DialogContent>
          {!editing && presets.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption" color="text.secondary">{t('model_mgr_quick_preset')}</Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                {presets.map((p) => (
                  <Chip key={p.name} label={p.label} size="small" onClick={() => applyPreset(p)} variant="outlined" />
                ))}
              </Box>
            </Box>
          )}
          <TextField
            label={t('model_mgr_field_id')} fullWidth size="small" sx={{ mb: 1.5 }}
            value={form.id} onChange={(e) => setForm({ ...form, id: e.target.value })}
            disabled={!!editing}
            helperText={t('model_mgr_field_id_helper')}
          />
          <TextField
            label={t('model_mgr_field_label')} fullWidth size="small" sx={{ mb: 1.5 }}
            value={form.label} onChange={(e) => setForm({ ...form, label: e.target.value })}
          />
          <TextField
            select label={t('model_mgr_field_protocol')} fullWidth size="small" sx={{ mb: 1.5 }}
            value={form.protocol} onChange={(e) => setForm({ ...form, protocol: e.target.value })}
          >
            <MenuItem value="openai">{t('model_mgr_proto_openai')}</MenuItem>
            <MenuItem value="anthropic">{t('model_mgr_proto_anthropic')}</MenuItem>
            <MenuItem value="ollama">{t('model_mgr_proto_ollama')}</MenuItem>
          </TextField>
          <TextField
            label={t('model_mgr_field_base_url')} fullWidth size="small" sx={{ mb: 1.5 }}
            value={form.baseUrl} onChange={(e) => setForm({ ...form, baseUrl: e.target.value })}
            helperText={t('model_mgr_field_base_url_helper')}
          />
          <TextField
            label={t('model_mgr_field_name')} fullWidth size="small" sx={{ mb: 1.5 }}
            value={form.modelName} onChange={(e) => setForm({ ...form, modelName: e.target.value })}
            helperText={t('model_mgr_field_name_helper')}
          />
          <TextField
            label={t('model_mgr_field_note')} fullWidth size="small"
            value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowAdd(false)}>{t('model_mgr_btn_cancel')}</Button>
          <Button variant="contained" onClick={saveModel} disabled={saving || !form.id || !form.baseUrl || !form.modelName}>
            {editing ? t('model_mgr_btn_save') : t('model_mgr_btn_add')}
          </Button>
        </DialogActions>
      </Dialog>

      {/* API Key 对话框 */}
      <Dialog open={!!showKey} onClose={() => setShowKey(null)} maxWidth="sm" fullWidth>
        <DialogTitle>{t('model_mgr_key_dialog_title')}{showKey}</DialogTitle>
        <DialogContent>
          <TextField
            label={t('model_mgr_key_field')} fullWidth size="small" type="password"
            value={apiKey} onChange={(e) => setApiKey(e.target.value)}
            helperText={t('model_mgr_key_helper')}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowKey(null)}>{t('model_mgr_btn_cancel')}</Button>
          <Button variant="contained" onClick={saveKey} disabled={saving || !apiKey}>{t('model_mgr_btn_save')}</Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

