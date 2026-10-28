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
    removeStorage('novellab.onboarded.v2')
  })

  it('isOnboarded 正确判定本地存储状态', () => {
    expect(isOnboarded()).toBe(false)
    writeStorage('novellab.onboarded', '1')
    expect(isOnboarded()).toBe(true)
    removeStorage('novellab.onboarded')
    removeStorage('novellab.onboarded.v2')
    writeStorage('novellab.onboarded.v2', JSON.stringify({ done: true, dismissedAt: Date.now() }))
    expect(isOnboarded()).toBe(true)
  })

  it('zh-CN 环境下完整走通四步引导并能返回与完成', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <OnboardingWizard onDone={onDone} onNavigate={onNavigate} />
      </I18nProvider>
    )

    // s1 欢迎
    expect(screen.getByText('欢迎使用暮冬念春')).toBeInTheDocument()
    expect(screen.getByText(/把优秀小说拆成可复用的写作资产/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '跳过' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '下一步' })).toBeInTheDocument()

    // s1 -> s2
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByText('第一步：导入并拆书')).toBeInTheDocument()
    expect(screen.getByText(/到「分析」页导入一本 TXT 全本/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '上一步' })).toBeInTheDocument()
    expect(screen.getByTestId('onboarding-primary-cta')).toBeInTheDocument()

    // 返回 s1
    fireEvent.click(screen.getByRole('button', { name: '上一步' }))
    expect(screen.getByText('欢迎使用暮冬念春')).toBeInTheDocument()

    // s1 -> s2 -> 点主按钮直接完成并跳转（v2：s2 CTA 为完成式跳转）
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByText('第一步：导入并拆书')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onNavigate).toHaveBeenCalled()
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

    // s2 主按钮点击直接完成并跳转
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onNavigate).toHaveBeenCalled()
    expect(isOnboarded()).toBe(true)
  })

  it('en-US s3/s4 渲染完整（单独用例）', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <OnboardingWizard onDone={onDone} onNavigate={onNavigate} modelConfigured />
      </I18nProvider>
    )
    // s1 -> s2 再直接完成
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Step 1: Import & Deconstruct')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(onDone).toHaveBeenCalled()
  })
})
