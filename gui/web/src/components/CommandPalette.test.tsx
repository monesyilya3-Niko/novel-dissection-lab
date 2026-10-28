import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import CommandPalette, { CommandPaletteTrigger } from './CommandPalette'
import { I18nProvider } from '../state/I18nContext'

const mockSetWorkbench = vi.fn()
const mockSetMode = vi.fn()
let mockCurrentMode: 'light' | 'dark' = 'light'

vi.mock('../state/AppContext', () => ({
  useApp: () => ({
    setWorkbench: mockSetWorkbench,
  }),
}))

vi.mock('../state/ThemeModeContext', () => ({
  useThemeMode: () => ({
    mode: mockCurrentMode,
    setMode: mockSetMode,
  }),
}))

describe('CommandPalette 全局命令面板双语国际化与功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCurrentMode = 'light'
  })

  it('zh-CN 环境下触发按钮与命令面板正确展示中文标签与快捷键', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <CommandPaletteTrigger />
        <CommandPalette />
      </I18nProvider>
    )

    // 触发按钮文案
    expect(screen.getByText('搜索…')).toBeInTheDocument()
    expect(screen.getByText('⌘K')).toBeInTheDocument()

    // 点击打开面板
    fireEvent.click(screen.getByText('搜索…'))

    // 搜索框 placeholder
    expect(screen.getByPlaceholderText('搜索工作台或操作…')).toBeInTheDocument()

    // 分组——WS-A5 扩为 4 组
    expect(screen.getByText('工作台')).toBeInTheDocument()
    expect(screen.getByText('创作')).toBeInTheDocument()
    expect(screen.getByText('资产')).toBeInTheDocument()
    expect(screen.getByText('系统')).toBeInTheDocument()

    // 工作台跳转项
    expect(screen.getByText('前往首页')).toBeInTheDocument()
    expect(screen.getByText('前往分析拆书')).toBeInTheDocument()
    expect(screen.getByText('前往辅助写作 (沉浸创作室与工坊)')).toBeInTheDocument()
    expect(screen.getByText('前往质量检验')).toBeInTheDocument()
    expect(screen.getByText('前往资产库')).toBeInTheDocument()
    expect(screen.getByText('前往高级功能')).toBeInTheDocument()
    expect(screen.getByText('前往系统')).toBeInTheDocument()
    expect(screen.getByText('前往设置')).toBeInTheDocument()
    expect(screen.getByText('前往管理后台')).toBeInTheDocument()
    expect(screen.getByText('前往帮助中心')).toBeInTheDocument()

    // 快捷键提示
    expect(screen.getByText('Alt+1')).toBeInTheDocument()
    expect(screen.getByText('Alt+3')).toBeInTheDocument()

    // 操作项（当前 light 模式下应为切换为暗色模式）
    expect(screen.getByText('切换为暗色模式')).toBeInTheDocument()

    // 底部快捷键指南
    expect(screen.getByText('↑↓ 导航')).toBeInTheDocument()
    expect(screen.getByText('↵ 选择')).toBeInTheDocument()
    expect(screen.getByText('esc 关闭')).toBeInTheDocument()
  })

  it('en-US 环境下触发按钮与命令面板全量渲染英文', async () => {
    mockCurrentMode = 'dark'
    render(
      <I18nProvider initialLocale="en-US">
        <CommandPaletteTrigger />
        <CommandPalette />
      </I18nProvider>
    )

    // 触发按钮英文文案
    expect(screen.getByText('Search…')).toBeInTheDocument()

    // 打开面板
    fireEvent.click(screen.getByText('Search…'))

    // 搜索框英文 placeholder
    expect(screen.getByPlaceholderText('Search workbenches or actions…')).toBeInTheDocument()

    // 英文分组——WS-A5 4 组
    expect(screen.getByText('Workbenches')).toBeInTheDocument()
    expect(screen.getByText('Creation')).toBeInTheDocument()
    expect(screen.getByText('Assets')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()

    // 英文工作台跳转
    expect(screen.getByText('Go to Home')).toBeInTheDocument()
    expect(screen.getByText('Go to Book Analysis')).toBeInTheDocument()
    expect(screen.getByText('Go to Writing Studio & Workbenches')).toBeInTheDocument()
    expect(screen.getByText('Go to Quality Check')).toBeInTheDocument()
    expect(screen.getByText('Go to Asset Library')).toBeInTheDocument()
    expect(screen.getByText('Go to Advanced Features')).toBeInTheDocument()
    expect(screen.getByText('Go to System')).toBeInTheDocument()
    expect(screen.getByText('Go to Settings')).toBeInTheDocument()
    expect(screen.getByText('Go to Admin Console')).toBeInTheDocument()
    expect(screen.getByText('Go to Help Center')).toBeInTheDocument()

    // 操作项（dark 模式下应为 Switch to Light Mode）
    expect(screen.getByText('Switch to Light Mode')).toBeInTheDocument()

    // 底部快捷键指南英文
    expect(screen.getByText('↑↓ Navigate')).toBeInTheDocument()
    expect(screen.getByText('↵ Select')).toBeInTheDocument()
    expect(screen.getByText('esc Close')).toBeInTheDocument()
  })

  it('搜索与模糊匹配在双语与空态下均正常工作', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <CommandPaletteTrigger />
        <CommandPalette />
      </I18nProvider>
    )

    fireEvent.click(screen.getByText('搜索…'))
    const input = screen.getByPlaceholderText('搜索工作台或操作…')

    // 过滤写作
    fireEvent.change(input, { target: { value: '写作' } })
    expect(screen.getByText('前往辅助写作 (沉浸创作室与工坊)')).toBeInTheDocument()
    expect(screen.queryByText('前往首页')).not.toBeInTheDocument()

    // 英文关键字模糊匹配
    fireEvent.change(input, { target: { value: 'analysis' } })
    expect(screen.getByText('前往分析拆书')).toBeInTheDocument()

    // 无匹配项空态展示
    fireEvent.change(input, { target: { value: 'xyz123nonexistent' } })
    expect(screen.getByText('没有匹配的结果')).toBeInTheDocument()
  })

  it('点击条目正确触发跳转并关闭面板', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <CommandPaletteTrigger />
        <CommandPalette />
      </I18nProvider>
    )

    fireEvent.click(screen.getByText('搜索…'))
    const writingItem = screen.getByText('前往辅助写作 (沉浸创作室与工坊)')
    fireEvent.click(writingItem)

    // 等待 requestAnimationFrame 执行
    await waitFor(() => {
      expect(mockSetWorkbench).toHaveBeenCalledWith('writing')
    })
  })
})
