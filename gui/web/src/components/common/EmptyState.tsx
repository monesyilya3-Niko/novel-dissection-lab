import Box from '@mui/material/Box'
import Button from '@mui/material/Button'
import Typography from '@mui/material/Typography'
import type { ReactNode } from 'react'
import { ink } from '../../ink'

export interface EmptyStateProps {
  icon?: ReactNode
  title: string
  hint?: string
  primaryCta?: { label: string; onClick: () => void }
  secondaryLink?: { label: string; onClick: () => void }
  minHeight?: number
  /** Optional test id for e2e */
  'data-testid'?: string
  /** Accessible label for the container */
  'aria-label'?: string
}

/**
 * Standardized empty state — centered flex column with large icon, title,
 * hint, CTA button + secondary link. Uses ink colors, no new deps.
 */
export default function EmptyState({
  icon,
  title,
  hint,
  primaryCta,
  secondaryLink,
  minHeight = 240,
  'data-testid': testId = 'empty-state',
  'aria-label': ariaLabel,
}: EmptyStateProps) {
  return (
    <Box
      data-testid={testId}
      aria-label={ariaLabel ?? title}
      sx={{
        minHeight,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 1.25,
        p: 4,
        textAlign: 'center',
      }}
    >
      {icon && (
        <Box
          sx={{
            fontSize: 40,
            lineHeight: 1,
            color: ink.textTertiary,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            '& svg': { fontSize: 40 },
          }}
          aria-hidden
        >
          {icon}
        </Box>
      )}
      <Typography variant="subtitle1" sx={{ fontWeight: 700, color: ink.text }}>
        {title}
      </Typography>
      {hint && (
        <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 420 }}>
          {hint}
        </Typography>
      )}
      {(primaryCta || secondaryLink) && (
        <Box sx={{ display: 'flex', gap: 1, mt: 1, flexWrap: 'wrap', justifyContent: 'center' }}>
          {primaryCta && (
            <Button variant="contained" onClick={primaryCta.onClick} sx={{ bgcolor: ink.primary, '&:hover': { bgcolor: ink.primaryHover } }}>
              {primaryCta.label}
            </Button>
          )}
          {secondaryLink && (
            <Button variant="text" onClick={secondaryLink.onClick} sx={{ color: ink.accent }}>
              {secondaryLink.label}
            </Button>
          )}
        </Box>
      )}
    </Box>
  )
}
