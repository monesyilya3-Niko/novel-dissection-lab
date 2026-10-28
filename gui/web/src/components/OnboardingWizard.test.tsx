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

    // s1 -> s2 -> 主按钮"下一步"进入 s3（v2 修复：s2 不再直接 finish，否则 s3/s4 永不可达）
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByText('第一步：导入并拆书')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(screen.getByText('第二步：查看资产与质检')).toBeInTheDocument()
    expect(screen.getByText(/浏览全部结构化资产|「资产库」浏览全部结构化资产/)).toBeInTheDocument()

    // s3 -> s4（三选一）
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(screen.getByText('下一步做什么')).toBeInTheDocument()
    expect(screen.getByTestId('onboarding-action-analysis')).toBeInTheDocument()
    expect(screen.getByTestId('onboarding-action-assets')).toBeInTheDocument()
    expect(screen.getByTestId('onboarding-action-writing')).toBeInTheDocument()

    // 点 s4 卡片 → 完成并跳转
    fireEvent.click(screen.getByTestId('onboarding-action-analysis'))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(onNavigate).toHaveBeenCalledWith('analysis')
    expect(isOnboarded()).toBe(true)
  })

  it('s2 捷径按钮直接跳转到对应工作台（未配模型 → system）', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <OnboardingWizard onDone={onDone} onNavigate={onNavigate} modelConfigured={false} />
      </I18nProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: '下一步' }))
    expect(screen.getByText('第一步：导入并拆书')).toBeInTheDocument()
    // 未配模型时捷径为「去配置模型」
    const shortcut = screen.getByTestId('onboarding-shortcut-cta')
    expect(shortcut).toHaveTextContent('去配置模型')
    fireEvent.click(shortcut)
    expect(onNavigate).toHaveBeenCalledWith('system')
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

    // s2 主按钮点击进入 s3（不再是完成式跳转）
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(screen.getByText('Step 2: Inspect Assets & QC')).toBeInTheDocument()

    // 跳过
    fireEvent.click(screen.getByRole('button', { name: 'Skip' }))
    expect(onDone).toHaveBeenCalledTimes(1)
    expect(isOnboarded()).toBe(true)
  })

  it('en-US s4 渲染完整（单独用例）', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <OnboardingWizard onDone={onDone} onNavigate={onNavigate} modelConfigured />
      </I18nProvider>
    )
    fireEvent.click(screen.getByRole('button', { name: 'Next' }))
    expect(screen.getByText('Step 1: Import & Deconstruct')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(screen.getByText('Step 2: Inspect Assets & QC')).toBeInTheDocument()
    fireEvent.click(screen.getByTestId('onboarding-primary-cta'))
    expect(screen.getByText('What next?')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Get Started' })).toBeInTheDocument()
  })
})
