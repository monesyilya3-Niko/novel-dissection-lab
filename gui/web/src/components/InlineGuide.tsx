// InlineGuide：在功能旁边直接展示的就地说明（不跳转帮助中心）。
// 设计：默认一行"这个功能做什么"，点击展开看步骤/示例/注意事项。
// i18n 用法：what/steps/tips/example 均可直接传原始中文，亦可传 t('key') 的结果。
// 为保持向后兼容，组件同时支持显式 key 形式：whatKey/stepsKeys/tipsKeys/exampleKey。
// 若提供了 *Key，则以 t(key) 解析为准；否则使用对应的原始字符串 prop。
// 例：<InlineGuide what={t('guide_inject_what')} steps={[t('guide_inject_step_1'), ...]} />
// 或：<InlineGuide what="后备文本" whatKey="guide_inject_what" stepsKeys={['guide_inject_step_1', ...]} />
import { useState } from 'react'
import Box from '@mui/material/Box'
import Collapse from '@mui/material/Collapse'
import IconButton from '@mui/material/IconButton'
import Typography from '@mui/material/Typography'
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { ink } from '../ink'
import { useI18n } from '../state/I18nContext'

interface InlineGuideProps {
  /** 一句话：这个功能是做什么的 — 可传原始文本或 t('key') 结果 */
  what: string
  /** what 的翻译键（可选）；若提供则以 t(whatKey) 为准 */
  whatKey?: string
  /** 操作步骤 — 原始文本或 t() 结果数组 */
  steps?: string[]
  /** steps 的翻译键数组（可选）；若提供则逐项 t(stepsKeys[i]) */
  stepsKeys?: string[]
  /** 注意事项 — 原始文本或 t() 结果数组 */
  tips?: string[]
  /** tips 的翻译键数组（可选） */
  tipsKeys?: string[]
  /** 输入示例（如"写作要点"怎么写）— 原始文本或 t() 结果 */
  example?: string
  /** example 的翻译键（可选） */
  exampleKey?: string
  /** 默认展开 */
  defaultOpen?: boolean
}

export default function InlineGuide({
  what,
  whatKey,
  steps,
  stepsKeys,
  tips,
  tipsKeys,
  example,
  exampleKey,
  defaultOpen = false,
}: InlineGuideProps) {
  const { t } = useI18n()
  const [open, setOpen] = useState(defaultOpen)

  // 解析：Key 优先，回落到原始 prop。what 本身已可在调用处传入 t('key')，
  // 因此此处仅在显式提供 *Key 时再做一次 t() 解析，保证两种调用方式均可工作。
  const resolvedWhat = whatKey ? t(whatKey, what) : what
  const resolvedSteps = stepsKeys ? stepsKeys.map((k) => t(k)) : steps
  const resolvedTips = tipsKeys ? tipsKeys.map((k) => t(k)) : tips
  const resolvedExample = exampleKey ? t(exampleKey, example ?? '') : example

  const hasDetail =
    (resolvedSteps?.length ?? 0) > 0 || (resolvedTips?.length ?? 0) > 0 || !!resolvedExample
  return (
    <Box
      sx={{
        mb: 2,
        border: `1px solid ${ink.hairline}`,
        borderRadius: 2,
        backgroundColor: ink.bg,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, px: 1.5, py: 1 }}>
        <InfoOutlinedIcon sx={{ fontSize: 18, color: ink.accent, flexShrink: 0 }} />
        <Typography variant="body2" sx={{ flex: 1, color: ink.textSecondary }}>
          {resolvedWhat}
        </Typography>
        {hasDetail && (
          <IconButton
            size="small"
            onClick={() => setOpen((o) => !o)}
            aria-label={open ? t('inline_guide_collapse', '收起说明') : t('inline_guide_expand', '展开说明')}
            sx={{
              transform: open ? 'rotate(180deg)' : 'none',
              transition: 'transform 0.2s',
              color: ink.textTertiary,
            }}
          >
            <ExpandMoreIcon fontSize="small" />
          </IconButton>
        )}
      </Box>
      {hasDetail && (
        <Collapse in={open}>
          <Box sx={{ px: 1.5, pb: 1.5, pt: 0.5, borderTop: `1px dashed ${ink.hairline}` }}>
            {resolvedSteps && resolvedSteps.length > 0 && (
              <Box component="ol" sx={{ m: 0, pl: 2.5, mb: resolvedTips || resolvedExample ? 1 : 0 }}>
                {resolvedSteps.map((s, i) => (
                  <Typography component="li" variant="body2" key={i} sx={{ color: ink.textSecondary, mb: 0.5 }}>
                    {s}
                  </Typography>
                ))}
              </Box>
            )}
            {resolvedExample && (
              <Box sx={{ mt: 1, p: 1.2, borderRadius: 1.5, backgroundColor: ink.surface, border: `1px solid ${ink.hairline}` }}>
                <Typography variant="caption" sx={{ color: ink.textTertiary, display: 'block', mb: 0.5 }}>
                  {t('inline_guide_example', '示例')}
                </Typography>
                <Typography variant="body2" sx={{ color: ink.text, whiteSpace: 'pre-wrap' }}>
                  {resolvedExample}
                </Typography>
              </Box>
            )}
            {resolvedTips && resolvedTips.length > 0 && (
              <Box sx={{ mt: 1 }}>
                {resolvedTips.map((ti, i) => (
                  <Typography variant="caption" key={i} sx={{ display: 'block', color: ink.textTertiary, mb: 0.4 }}>
                    ※ {ti}
                  </Typography>
                ))}
              </Box>
            )}
          </Box>
        </Collapse>
      )}
    </Box>
  )
}
