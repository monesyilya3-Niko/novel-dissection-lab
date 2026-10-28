import Tooltip from '@mui/material/Tooltip'
import type { ReactElement } from 'react'

export interface DisabledTooltipButtonProps {
  disabled: boolean
  disabledReason?: string
  children: ReactElement
  placement?: 'top' | 'bottom' | 'left' | 'right' | 'bottom-start' | 'bottom-end' | 'top-start' | 'top-end'
}

/**
 * Disabled button with reason tooltip.
 * MUI Tooltip doesn't trigger on disabled elements, so we wrap in a span.
 */
export default function DisabledTooltipButton({
  disabled,
  disabledReason,
  children,
  placement = 'top',
}: DisabledTooltipButtonProps) {
  if (disabled && disabledReason) {
    return (
      <Tooltip title={disabledReason} arrow placement={placement}>
        {/* span wrapper needed — MUI Tooltip doesn't fire on disabled */}
        <span style={{ display: 'inline-flex' }}>{children}</span>
      </Tooltip>
    )
  }
  return children
}
