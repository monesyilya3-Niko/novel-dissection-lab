import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import WorkbenchNav, { type WorkbenchKey, buildNavGroups } from './WorkbenchNav'
import { I18nProvider } from '../state/I18nContext'

// I18nProvider 已在 setup.ts 挂载默认 zh-CN；个别用例包 en-US Provider 覆盖。

describe('WorkbenchNav 左侧导航栏组件', () => {
  beforeEach(() => vi.clearAllMocks())

  it('buildNavGroups: simple 4+2+manage+help / advanced 全量可测，不依赖 DOM 渲染', () => {
    const t = (k: string, fb?: string) => fb ?? k
    // simple 非 admin：primary 4 + more collapsed + manage 2 + help 1
    const simple = buildNavGroups(t, 'simple', false)
    expect(simple.map((g) => g.id)).toEqual(['primary', 'more', 'manage', 'help'])
    expect(simple[0].items.map((i) => i.key)).toEqual(['home', 'analysis', 'writing', 'quality'])
    expect(simple[1].items.map((i) => i.key)).toEqual(['assets', 'advanced'])
    expect(simple[1].collapsible).toBe(true)
    expect(simple[1].defaultOpen).toBe(false)
    expect(simple[2].items.map((i) => i.key)).toEqual(['system', 'settings'])
    expect(simple[2].subtle).toBe(true)
    expect(simple[3].items.map((i) => i.key)).toEqual(['help'])
    // admin 不可见时绝不出现
    expect(simple.flatMap((g) => g.items).map((i) => i.key).includes('admin')).toBe(false)

    // simple + isAdmin：manage 含 admin
    const simpleAdmin = buildNavGroups(t, 'simple', true)
    expect(simpleAdmin[2].items.map((i) => i.key)).toEqual(['system', 'settings', 'admin'])

    // advanced：more 默认展开，admin 仅 isAdmin 时可见
    const advanced = buildNavGroups(t, 'advanced', true)
    expect(advanced[1].defaultOpen).toBe(true)
    expect(advanced[1].collapsible).toBe(true)
    expect(advanced[2].items.map((i) => i.key)).toEqual(['system', 'settings', 'admin'])
    const advNoAdmin = buildNavGroups(t, 'advanced', false)
    expect(advNoAdmin[2].items.map((i) => i.key)).toEqual(['system', 'settings'])
  })

  it('渲染默认 (advanced) 下全部可见项及分组标题', () => {
    const onChange = vi.fn()
    render(<WorkbenchNav active="home" onChange={onChange} />)

    // 分组标题：创作 / 管理 / 帮助（advanced 含"更多工具"可折叠区）
    expect(screen.getByText('创作')).toBeInTheDocument()
    expect(screen.getByText('更多工具')).toBeInTheDocument()
    expect(screen.getByText('管理')).toBeInTheDocument()
    expect(screen.getByText('帮助')).toBeInTheDocument()

    // 默认 non-admin：9 个工作台（admin 隐藏），data-testid 可用于 e2e
    expect(screen.getByTestId('nav-home')).toBeInTheDocument()
    expect(screen.getByTestId('nav-analysis')).toBeInTheDocument()
    expect(screen.getByTestId('nav-writing')).toBeInTheDocument()
    expect(screen.getByTestId('nav-quality')).toBeInTheDocument()
    expect(screen.getByTestId('nav-assets')).toBeInTheDocument()
    expect(screen.getByTestId('nav-advanced')).toBeInTheDocument()
    expect(screen.getByTestId('nav-system')).toBeInTheDocument()
    expect(screen.getByTestId('nav-settings')).toBeInTheDocument()
    expect(screen.getByTestId('nav-help')).toBeInTheDocument()
    expect(screen.queryByTestId('nav-admin')).toBeNull()

    // 版本号展示
    expect(screen.getByText('v2.3.0')).toBeInTheDocument()
  })

  it('isAdmin=true 时显示管理后台入口', () => {
    const onChange = vi.fn()
    render(<WorkbenchNav active="home" onChange={onChange} isAdmin mode="advanced" />)
    expect(screen.getByTestId('nav-admin')).toBeInTheDocument()
    expect(screen.getByText('管理后台')).toBeInTheDocument()
  })

  it('simple 模式："更多工具"默认收起，可展开/collapse via data-testid', () => {
    const onChange = vi.fn()
    render(<WorkbenchNav active="home" onChange={onChange} mode="simple" />)

    // simple 默认收起：more 内的资产/高级不可见
    expect(screen.queryByTestId('nav-assets')).toBeNull()
    expect(screen.queryByTestId('nav-advanced')).toBeNull()
    expect(screen.getByTestId('nav-more-toggle')).toBeInTheDocument()

    // 点击展开
    const toggle = screen.getByTestId('nav-more-toggle')
    fireEvent.click(toggle)
    expect(screen.getByTestId('nav-assets')).toBeInTheDocument()
    expect(screen.getByTestId('nav-advanced')).toBeInTheDocument()

    // 再次点击收起
    fireEvent.click(toggle)
    expect(screen.queryByTestId('nav-assets')).toBeNull()
  })

  it('advanced 模式："更多工具"默认展开', () => {
    const onChange = vi.fn()
    render(<WorkbenchNav active="home" onChange={onChange} mode="advanced" />)
    expect(screen.getByTestId('nav-more-toggle')).toBeInTheDocument()
    expect(screen.getByTestId('nav-assets')).toBeInTheDocument()
    expect(screen.getByTestId('nav-advanced')).toBeInTheDocument()
  })

  it('mode 切换时 "更多工具" 同步打开/关闭（advanced→simple 收起，simple→advanced 展开）', () => {
    const onChange = vi.fn()
    const { rerender } = render(<WorkbenchNav active="home" onChange={onChange} mode="advanced" />)
    expect(screen.getByTestId('nav-assets')).toBeInTheDocument()
    rerender(<WorkbenchNav active="home" onChange={onChange} mode="simple" />)
    expect(screen.queryByTestId('nav-assets')).toBeNull()
    rerender(<WorkbenchNav active="home" onChange={onChange} mode="advanced" />)
    expect(screen.getByTestId('nav-assets')).toBeInTheDocument()
  })

  it('高亮当前选中的工作台项目，点击切换触发 onChange 回调', () => {
    const onChange = vi.fn()
    const { rerender } = render(<WorkbenchNav active="writing" onChange={onChange} />)

    // writing 项目应带有 Mui-selected 类
    const writingBtn = screen.getByText('辅助写作').closest('.MuiListItemButton-root')
    expect(writingBtn).toHaveClass('Mui-selected')

    const qualityBtn = screen.getByText('质量检验').closest('.MuiListItemButton-root')
    expect(qualityBtn).not.toHaveClass('Mui-selected')

    // 点击切换至 quality
    if (qualityBtn) {
      fireEvent.click(qualityBtn)
      expect(onChange).toHaveBeenCalledWith('quality' satisfies WorkbenchKey)
    }

    // 重新渲染为 quality active
    rerender(<WorkbenchNav active="quality" onChange={onChange} />)
    expect(screen.getByText('质量检验').closest('.MuiListItemButton-root')).toHaveClass('Mui-selected')
    expect(screen.getByText('辅助写作').closest('.MuiListItemButton-root')).not.toHaveClass('Mui-selected')
  })

  it('data-testid 点击链路：通过 nav-* e2e 选择器切换工作台', () => {
    const onChange = vi.fn()
    render(<WorkbenchNav active="home" onChange={onChange} />)
    fireEvent.click(screen.getByTestId('nav-quality'))
    expect(onChange).toHaveBeenCalledWith('quality')
    fireEvent.click(screen.getByTestId('nav-help'))
    expect(onChange).toHaveBeenCalledWith('help')
  })

  it('en-US 国际化语言下全导航项双语渲染', () => {
    const onChange = vi.fn()
    render(
      <I18nProvider initialLocale="en-US">
        <WorkbenchNav active="home" onChange={onChange} />
      </I18nProvider>,
    )

    // 分组
    expect(screen.getByText('Creation')).toBeInTheDocument()
    expect(screen.getByText('More Tools')).toBeInTheDocument()
    expect(screen.getByText('Management')).toBeInTheDocument()
    expect(screen.getByText('Help')).toBeInTheDocument()

    // 工作台项
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.getByText('Deconstruction')).toBeInTheDocument()
    expect(screen.getByText('Writing Studio')).toBeInTheDocument()
    expect(screen.getByText('Quality Guard')).toBeInTheDocument()
    expect(screen.getByText('Asset Matrix')).toBeInTheDocument()
    expect(screen.getByText('Advanced Tools')).toBeInTheDocument()
    expect(screen.getByText('System')).toBeInTheDocument()
    expect(screen.getByText('Settings')).toBeInTheDocument()
    expect(screen.getByText('Help Center')).toBeInTheDocument()
  })
})
