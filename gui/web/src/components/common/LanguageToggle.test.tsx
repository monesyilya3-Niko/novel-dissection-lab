import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import LanguageToggle from './LanguageToggle'
import { I18nProvider } from '../../state/I18nContext'

describe('LanguageToggle 语言切换按钮组件', () => {
  it('在 zh-CN 环境下展示 "中" 并提示切换为英文', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <LanguageToggle />
      </I18nProvider>,
    )

    expect(screen.getByText('中')).toBeInTheDocument()
    const btn = screen.getByRole('button', { name: '切换为英文 (Switch to English)' })
    expect(btn).toBeInTheDocument()
  })

  it('点击按钮在 zh-CN 与 en-US 之间双向切换', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <LanguageToggle />
      </I18nProvider>,
    )

    const btn = screen.getByRole('button', { name: '切换为英文 (Switch to English)' })
    fireEvent.click(btn)

    // 切换后变为 EN
    expect(screen.getByText('EN')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '切换为中文 (Switch to Chinese)' })).toBeInTheDocument()

    // 再次点击切回 中
    fireEvent.click(screen.getByRole('button', { name: '切换为中文 (Switch to Chinese)' }))
    expect(screen.getByText('中')).toBeInTheDocument()
  })

  it('在 en-US 初始环境下展示 "EN" 并提示切换为中文', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <LanguageToggle />
      </I18nProvider>,
    )

    expect(screen.getByText('EN')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '切换为中文 (Switch to Chinese)' })).toBeInTheDocument()
  })
})
