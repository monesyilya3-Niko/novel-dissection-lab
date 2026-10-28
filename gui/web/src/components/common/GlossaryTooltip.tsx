import Box from '@mui/material/Box'
import Chip from '@mui/material/Chip'
import Tooltip from '@mui/material/Tooltip'
import Typography from '@mui/material/Typography'
import type { ReactElement } from 'react'
import { useI18n } from '../../state/I18nContext'
import { useAppOptional } from '../../state/AppContext'
import { ink } from '../../ink'
import { GLOSSARY, type GlossaryTerm } from '../../help/glossary'

function firstSentence(s: string): string {
  const m = s.match(/^[^。．.]+[。．.]?/)
  return m ? m[0].trim() : s
}

function catLabel(cat: string, t: (k: string, fb?: string) => string): string {
  const keyMap: Record<string, string> = {
    concept: 'help_cat_concept',
    asset: 'help_cat_asset',
    feature: 'help_cat_feature',
  }
  const k = keyMap[cat]
  return k ? t(k, cat) : cat
}

function localize(rec: Record<string, string>, locale: string): string {
  return rec[locale] ?? rec['zh-CN'] ?? rec['en-US'] ?? Object.values(rec)[0] ?? ''
}

export interface GlossaryTooltipProps {
  term: string
  children: ReactElement
}

/**
 * GlossaryTooltip — wraps children with a Tooltip showing the glossary
 * definition's first sentence + category chip. Clicking tooltip content
 * navigates to the glossary entry via openHelp('glossary', termKey).
 * If term not found, renders children unchanged (passthrough).
 */
export default function GlossaryTooltip({ term, children }: GlossaryTooltipProps) {
  const { t, locale } = useI18n()
  const app = useAppOptional()

  const glossary: GlossaryTerm[] = GLOSSARY
  const needle = term.toLowerCase()
  const entry = glossary.find((g: GlossaryTerm) => {
    const zh = (g.term['zh-CN'] ?? '').toLowerCase()
    const en = (g.term['en-US'] ?? '').toLowerCase()
    return zh === needle || en === needle || zh.includes(needle) || en.includes(needle)
  })
  if (!entry) return children

  const termKey = localize(entry.term, locale)
  const def = localize(entry.definition, locale)
  const snippet = firstSentence(def)
  const catText = catLabel(entry.category, t)

  return (
    <Tooltip
      arrow
      title={
        <Box
          onClick={() => app?.openHelp('glossary', termKey)}
          sx={{ cursor: app ? 'pointer' : 'default', maxWidth: 320 }}
        >
          <Typography variant="body2" sx={{ lineHeight: 1.7 }}>{snippet}</Typography>
          <Chip
            label={catText}
            size="small"
            sx={{ mt: 0.75, bgcolor: ink.primarySoft, color: ink.primary, height: 20, fontSize: '0.7rem' }}
          />
        </Box>
      }
    >
      <Box component="span" sx={{ cursor: 'help', borderBottom: `1px dotted ${ink.textTertiary}`, display: 'inline' }}>
        {children}
      </Box>
    </Tooltip>
  )
}
