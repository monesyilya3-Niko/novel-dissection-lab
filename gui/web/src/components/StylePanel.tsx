// 文风集成面板：风格分析 / 风格库 / 风格应用。
import { useState, useEffect } from 'react'
import Box from '@mui/material/Box'
import Typography from '@mui/material/Typography'
import Button from '@mui/material/Button'
import TextField from '@mui/material/TextField'
import Paper from '@mui/material/Paper'
import Alert from '@mui/material/Alert'
import CircularProgress from '@mui/material/CircularProgress'
import { styleApi } from '../api/client'
import { friendlyError } from '../api/client'
import InlineGuide from './InlineGuide'
import { useI18n } from '../state/I18nContext'

interface StyleCard {
  name: string
  createdAt: string
  metrics: Record<string, number>
}

export default function StylePanel() {
  const { t } = useI18n()
  const [tab, setTab] = useState<'analyze' | 'library'>('analyze')
  const [text, setText] = useState('')
  const [styleName, setStyleName] = useState('')
  const [result, setResult] = useState<Record<string, unknown> | null>(null)
  const [styles, setStyles] = useState<StyleCard[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const loadStyles = async () => {
    try {
      const data = await styleApi.list()
      setStyles((data.styles ?? []) as StyleCard[])
    } catch { /* ignore */ }
  }

  useEffect(() => { loadStyles() }, [])

  const doAnalyze = async () => {
    setLoading(true)
    setError('')
    setMessage('')
    try {
      const data = await styleApi.analyze({ text, name: styleName || '未命名' })
      setResult(data)
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setLoading(false)
    }
  }

  const doSave = async () => {
    if (!result || !styleName || saving) return
    setSaving(true)
    try {
      await styleApi.save({ name: styleName, style_card: result })
      setMessage(t('style_save_success', '风格「{name}」已保存', { name: styleName }))
      loadStyles()
    } catch (e) {
      setError(friendlyError(e))
    } finally {
      setSaving(false)
    }
  }

  const doDelete = async (name: string) => {
    // P2-F13：破坏性操作二次确认
    if (!window.confirm(t('style_delete_confirm', '确定删除风格「{name}」吗？此操作不可恢复。', { name }))) return
    try {
      await styleApi.delete(name)
      setMessage(t('style_delete_success', '风格「{name}」已删除', { name }))
      loadStyles()
    } catch (e) {
      setError(friendlyError(e))
    }
  }

  const metrics = result?.metrics as Record<string, number> | undefined

  return (
    <Box>
      <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
        <Button variant={tab === 'analyze' ? 'contained' : 'outlined'} onClick={() => setTab('analyze')}>
          {t('style_tab_analyze', '风格分析')}
        </Button>
        <Button variant={tab === 'library' ? 'contained' : 'outlined'} onClick={() => setTab('library')}>
          {t('style_tab_library', '风格库')}
        </Button>
      </Box>

      {message && <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMessage('')}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {tab === 'analyze' && (
        <Box>
          <InlineGuide
            what={t(
              'style_guide_what',
              '从一段样本文本里提取可量化的风格指标（句长、对话占比、情绪密度等），保存成风格卡，方便以后对照和复用。'
            )}
            steps={[
              t('style_guide_s1', '起一个风格名称，如：悬疑冷峻风。'),
              t('style_guide_s2', '粘贴至少 100 字的代表性文本（最好是你认可的成品段落）。'),
              t('style_guide_s3', '点「分析风格」，看平均句长、对话占比等指标。'),
              t('style_guide_s4', '确认指标符合预期后点「保存风格卡」，它会出现在「风格库」里。'),
            ]}
            tips={[
              t('style_guide_tip1', '样本越有代表性，风格卡越准；拼凑的多段文字会拉平均值。'),
            ]}
          />
          <TextField
            label={t('style_name_label', '风格名称')}
            fullWidth
            size="small"
            sx={{ mb: 1.5 }}
            value={styleName}
            onChange={(e) => setStyleName(e.target.value)}
            helperText={t('style_name_helper', '保存时使用，如：悬疑冷峻风')}
          />
          <TextField
            label={t('style_text_label', '文本样本')}
            multiline
            rows={8}
            fullWidth
            size="small"
            sx={{ mb: 1.5 }}
            value={text}
            onChange={(e) => setText(e.target.value)}
            helperText={t('style_text_helper', '粘贴至少 100 字的代表性文本')}
          />
          <Button variant="contained" onClick={doAnalyze} disabled={!text.trim() || loading}>
            {loading ? <CircularProgress size={20} /> : t('style_btn_analyze', '分析风格')}
          </Button>

          {result && metrics && (
            <Paper sx={{ p: 2, mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                {t('style_metrics_title', '风格指标')}
              </Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1 }}>
                <Typography variant="body2">
                  {t('style_metric_avg_sentence', '平均句长：')}
                  {String(metrics.avgSentenceLength ?? metrics.avg_sentence_length ?? '-')}
                  {t('style_metric_avg_sentence_unit', ' 字')}
                </Typography>
                <Typography variant="body2">
                  {t('style_metric_dialogue_ratio', '对话占比：')}
                  {(Number(metrics.dialogueRatio ?? metrics.dialogue_ratio ?? 0) * 100).toFixed(1)}%
                </Typography>
                <Typography variant="body2">
                  {t('style_metric_emotion_density', '情绪密度：')}
                  {String(metrics.emotionDensity ?? metrics.emotion_density ?? '-')}
                  {t('style_metric_emotion_density_unit', '/千字')}
                </Typography>
                <Typography variant="body2">
                  {t('style_metric_avg_paragraph', '段落均长：')}
                  {String(metrics.avgParagraphLength ?? metrics.avg_paragraph_length ?? '-')}
                  {t('style_metric_avg_paragraph_unit', ' 字')}
                </Typography>
                <Typography variant="body2">
                  {t('style_metric_short_paragraph_ratio', '短段占比：')}
                  {(Number(metrics.shortParagraphRatio ?? metrics.short_paragraph_ratio ?? 0) * 100).toFixed(1)}%
                </Typography>
                <Typography variant="body2">
                  {t('style_metric_total_chars', '总字数：')}
                  {String(metrics.totalChars ?? metrics.total_chars ?? '-')}
                </Typography>
              </Box>
              <Button variant="outlined" size="small" sx={{ mt: 1.5 }} onClick={doSave} disabled={!styleName || saving}>
                {t('style_btn_save', '保存风格卡')}
              </Button>
            </Paper>
          )}
        </Box>
      )}

      {tab === 'library' && (
        <Box>
          {styles.length === 0 && (
            <Alert severity="info">
              {t('style_library_empty', '暂无风格卡，请先在「风格分析」中创建')}
            </Alert>
          )}
          {styles.map((s) => (
            <Paper key={s.name} sx={{ p: 1.5, mb: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Box sx={{ flex: 1 }}>
                  <Typography variant="subtitle2">{s.name}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t('style_lib_summary', '句长 {s} 字 | 对话 {d}%', {
                      s: String(s.metrics?.avg_sentence_length ?? '-'),
                      d: (Number(s.metrics?.dialogue_ratio ?? 0) * 100).toFixed(0),
                    })}
                  </Typography>
                </Box>
                <Button size="small" color="error" onClick={() => doDelete(s.name)}>
                  {t('action_delete', '删除')}
                </Button>
              </Box>
            </Paper>
          ))}
        </Box>
      )}
    </Box>
  )
}
