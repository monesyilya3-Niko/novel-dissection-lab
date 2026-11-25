import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MenuItem from '@mui/material/MenuItem'
import TextField from '@mui/material/TextField'
import GlossaryTooltip from './GlossaryTooltip'
import { I18nProvider } from '../../state/I18nContext'

describe('GlossaryTooltip', () => {
  it('下拉框术语提示不拦截展开后的选项', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <GlossaryTooltip term="声线卡">
          <TextField select label="声线卡" defaultValue="voice-1">
            <MenuItem value="voice-1">测试声线卡</MenuItem>
          </TextField>
        </GlossaryTooltip>
      </I18nProvider>,
    )

    fireEvent.mouseOver(screen.getByRole('combobox', { name: '声线卡' }))
    expect(await screen.findByRole('tooltip')).toHaveStyle({ pointerEvents: 'none' })
  })
})
