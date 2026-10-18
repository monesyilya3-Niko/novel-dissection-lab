import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ContextHelpButton from './ContextHelpButton'
import { I18nProvider } from '../state/I18nContext'

const mockOpenHelp = vi.fn()

let mockAppValue: { openHelp: typeof mockOpenHelp } | null = {
  openHelp: mockOpenHelp,
}

vi.mock('../state/AppContext', () => ({
  useAppOptional: () => mockAppValue,
}))

describe('ContextHelpButton 上下文帮助按钮组件', () => {
  it('渲染默认帮助提示并在点击时触发 openHelp 跳转', () => {
    mockAppValue = { openHelp: mockOpenHelp }
    render(<ContextHelpButton guideKey="analysis" />)

    const button = screen.getByLabelText('查看此功能的使用指南')
    expect(button).toBeInTheDocument()

    fireEvent.click(button)
    expect(mockOpenHelp).toHaveBeenCalledWith('guides', 'analysis')
  })

  it('支持自定义提示文本', () => {
    mockAppValue = { openHelp: mockOpenHelp }
    render(<ContextHelpButton guideKey="writing" title="自定义写作指南提示" />)

    const button = screen.getByLabelText('自定义写作指南提示')
    expect(button).toBeInTheDocument()
  })

  it('脱离 AppProvider 时点击不抛错', () => {
    mockAppValue = null
    render(<ContextHelpButton guideKey="qc" />)

    const button = screen.getByLabelText('查看此功能的使用指南')
    expect(button).toBeInTheDocument()

    expect(() => fireEvent.click(button)).not.toThrow()
  })

  it('en-US 环境下渲染英文默认提示', () => {
    mockAppValue = { openHelp: mockOpenHelp }
    render(
      <I18nProvider initialLocale="en-US">
        <ContextHelpButton guideKey="analysis" />
      </I18nProvider>,
    )

    const button = screen.getByLabelText('View guide for this feature')
    expect(button).toBeInTheDocument()
  })
})
