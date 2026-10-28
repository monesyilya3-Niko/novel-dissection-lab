// P2-F12 SettingsWorkbench 即时校验与双语国际化回归。
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import SettingsWorkbench, { validateSettingsField } from './SettingsWorkbench'
import { I18nProvider } from '../state/I18nContext'
import { systemApi } from '../api/client'
import { TRANSLATIONS } from '../i18n/translations'

vi.mock('../state/AppContext', () => ({
  useApp: () => ({ refreshThresholds: vi.fn() }),
  useAppOptional: () => null,
}))

vi.mock('../state/UiModeContext', () => ({
  useUiMode: () => ({ mode: 'advanced', setMode: vi.fn(), isHydrated: true }),
  useUiModeOptional: () => ({ mode: 'advanced', setMode: vi.fn(), isHydrated: true }),
}))

vi.mock('../api/client', () => ({
  systemApi: {
    settings: vi.fn(),
    updateSettings: vi.fn(),
    resetSettings: vi.fn(),
  },
  friendlyError: (e: unknown) => String(e),
}))


const base = {
  consistencyTarget: '90',
  qualityPassLine: '75',
  qualityWarnLine: '60',
  defaultWords: '2400',
  maxAttempts: '3',
}

describe('validateSettingsField 校验规则', () => {
  it('合法值无错误', () => {
    expect(validateSettingsField('consistencyTarget', '90', base)).toBe('')
    expect(validateSettingsField('qualityPassLine', '75', base)).toBe('')
    expect(validateSettingsField('qualityWarnLine', '60', base)).toBe('')
    expect(validateSettingsField('defaultWords', '2400', base)).toBe('')
    expect(validateSettingsField('maxAttempts', '3', base)).toBe('')
  })

  it('空值与非数字被拒绝（默认中文）', () => {
    expect(validateSettingsField('defaultWords', '', base)).toBe('不能为空')
    expect(validateSettingsField('defaultWords', 'abc', base)).toBe('请输入数字')
  })

  it('范围越界被拒绝（与后端一致）', () => {
    expect(validateSettingsField('qualityPassLine', '101', base)).toBe('必须在 0-100 之间')
    expect(validateSettingsField('qualityPassLine', '-1', base)).toBe('必须在 0-100 之间')
    expect(validateSettingsField('defaultWords', '99', base)).toBe('必须在 100-20000 之间')
    expect(validateSettingsField('defaultWords', '20001', base)).toBe('必须在 100-20000 之间')
    expect(validateSettingsField('maxAttempts', '0', base)).toBe('必须在 1-10 之间')
    expect(validateSettingsField('maxAttempts', '11', base)).toBe('必须在 1-10 之间')
  })

  it('整数约束', () => {
    expect(validateSettingsField('defaultWords', '2400.5', base)).toBe('必须为整数')
    expect(validateSettingsField('maxAttempts', '2.5', base)).toBe('必须为整数')
  })

  it('及格线必须 ≥ 警告线（交叉校验）', () => {
    expect(validateSettingsField('qualityPassLine', '50', base)).toBe('及格线必须 ≥ 警告线')
    expect(validateSettingsField('qualityWarnLine', '80', base)).toBe('警告线必须 ≤ 及格线')
    // 相等合法
    expect(validateSettingsField('qualityPassLine', '60', base)).toBe('')
  })

  it('传入英文翻译函数时返回对应英文错误提示', () => {
    const tEn = (key: keyof typeof TRANSLATIONS) => TRANSLATIONS[key]?.['en-US'] ?? key
    expect(validateSettingsField('defaultWords', '', base, tEn)).toBe('Cannot be empty')
    expect(validateSettingsField('defaultWords', 'abc', base, tEn)).toBe('Please enter a number')
    expect(validateSettingsField('qualityPassLine', '105', base, tEn)).toBe('Must be between 0 and 100')
    expect(validateSettingsField('defaultWords', '2400.5', base, tEn)).toBe('Must be an integer')
    expect(validateSettingsField('qualityPassLine', '50', base, tEn)).toBe('Pass line must be ≥ warn line')
  })
})

describe('SettingsWorkbench 组件双语国际化渲染', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(systemApi.settings).mockResolvedValue({
      port: 8080,
      batchSize: 5000,
      thresholds: {
        consistencyTarget: 90,
        qualityPassLine: 75,
        qualityWarnLine: 60,
      },
      writing: {
        defaultWords: 2400,
        maxAttempts: 3,
      },
      paths: {
        workspace: '/data/workspace',
      },
      envOverrides: {
        NOVEL_LAB_PORT: '8080',
      },
    })
  })

  it('zh-CN 默认环境下渲染完整中文设置与字段', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <SettingsWorkbench />
      </I18nProvider>
    )

    expect(await screen.findByRole('heading', { name: '系统设置' })).toBeInTheDocument()
    expect(screen.getByText('打分阈值')).toBeInTheDocument()
    expect(screen.getByText('写作设置')).toBeInTheDocument()
    expect(screen.getByText('服务配置')).toBeInTheDocument()
    expect(screen.getByText('需重启生效')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '保存设置' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重置为默认' })).toBeInTheDocument()

    // 字段标签
    expect(screen.getByLabelText('一致性目标分')).toBeInTheDocument()
    expect(screen.getByLabelText('质量及格线')).toBeInTheDocument()
    expect(screen.getByLabelText('质量警告线')).toBeInTheDocument()
    expect(screen.getByLabelText('默认字数')).toBeInTheDocument()
    expect(screen.getByLabelText('最大改写轮数')).toBeInTheDocument()
  })

  it('en-US 语言环境下全量渲染英文标题、说明与即时校验错误', async () => {
    render(
      <I18nProvider initialLocale="en-US">
        <SettingsWorkbench />
      </I18nProvider>
    )

    expect(await screen.findByRole('heading', { name: 'System Settings' })).toBeInTheDocument()
    expect(screen.getByText('Scoring Thresholds')).toBeInTheDocument()
    expect(screen.getByText('Writing Settings')).toBeInTheDocument()
    expect(screen.getByText('Service Configuration')).toBeInTheDocument()
    expect(screen.getByText('Restart Required')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save Settings' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Reset to Defaults' })).toBeInTheDocument()

    // 英文字段标签
    expect(screen.getByLabelText('Consistency Target')).toBeInTheDocument()
    const passInput = screen.getByLabelText('Quality Pass Line')
    expect(passInput).toBeInTheDocument()
    expect(screen.getByLabelText('Quality Warn Line')).toBeInTheDocument()
    expect(screen.getByLabelText('Default Words')).toBeInTheDocument()
    expect(screen.getByLabelText('Max Rewrite Attempts')).toBeInTheDocument()

    // 测试英文即时校验错误显示
    fireEvent.change(passInput, { target: { value: '40' } }) // 40 < 60 warn line
    await waitFor(() => {
      expect(screen.getByText('Pass line must be ≥ warn line')).toBeInTheDocument()
    })
    expect(screen.getByRole('button', { name: 'Save Settings' })).toBeDisabled()
  })
})
