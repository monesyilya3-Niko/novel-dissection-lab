import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import OnboardingWizard, { isOnboarded } from './OnboardingWizard'
import { I18nProvider } from '../state/I18nContext'
import { writeStorage, removeStorage } from '../safeStorage'

describe('OnboardingWizard 首启引导向导双语国际化与步进流程测试', () => {
  const onDone = vi.fn()
  const onNavigate = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    removeStorage('novellab.onboarded')
  })

  it('isOnboarded 正确判定本地存储状态', () => {
    expect(isOnboarded()).toBe(false)
    writeStorage('novellab.onboarded', '1')
    expect(isOnboarded()).toBe(true)
  })

  it('zh-CN 环境下完整走通三步引导并能返回与完成', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <OnboardingWizard onDone={onDone} onNavigate={onNavigate} />
      </I18nProvider>
    )

    // 第一步：欢迎
    expect(screen.getByText('欢迎使用暮冬念春')).toBeInTheDocument()
    expect(screen.getByText(/把优秀小说拆成可复用的写作资产/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '跳过' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '下一步' })).toBeInTheDocument()

    // 步进到第二步
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByText('第一步：导入并拆书')).toBeInTheDocument()
    expect(screen.getByText(/到「分析」页导入一本 TXT 全本/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '上一步' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '去导入' })).toBeInTheDocument()

    // 点击上一步
    fireEvent.click(screen.getByRole('button', { name: '上一步' }))
    expect(screen.getByText('欢迎使用暮冬念春')).toBeInTheDocument()

    // 再次步进到第二步
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByText('第一步：导入并拆书')).toBeInTheDocument()

    // 步进到第三步
    fireEvent.click(screen.getByRole('button', { name: '去导入' }))
    expect(screen.getByText('第二步：查看资产与质检')).toBeInTheDocument()
    expect(screen.getByText(/浏览全部结构化资产/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '开始使用' })).toBeInTheDocument()

    // 完成引导
    fireEvent.click(screen.getByRole('button', { name: '开始使用' }))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(isOnboarded()).toBe(true)
  })

  it('en-US 环境下全量双语渲染与跳过功能', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <OnboardingWizard onDone={onDone} onNavigate={onNavigate} />
      </I18nProvider>
    )

    // 第一步英文
    expect(screen.getByText('Welcome to Exoscribe')).toBeInTheDocument()
    expect(screen.getByText(/Deconstruct masterworks into reusable writing assets/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Skip' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next' })).toBeInTheDocument()

    // 步进到第二步
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Step 1: Import & Deconstruct')).toBeInTheDocument()
    expect(screen.getByText(/Go to "Analysis" to import a full TXT novel/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Back' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Go to Import' })).toBeInTheDocument()

    // 步进到第三步
    fireEvent.click(screen.getByRole('button', { name: 'Go to Import' }))
    expect(screen.getByText('Step 2: Inspect Assets & QC')).toBeInTheDocument()
    expect(screen.getByText(/Browse all structured assets in "Asset Library"/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Get Started' })).toBeInTheDocument()

    // 点击跳过
    fireEvent.click(screen.getByRole('button', { name: 'Skip' }))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(isOnboarded()).toBe(true)
  })
})
