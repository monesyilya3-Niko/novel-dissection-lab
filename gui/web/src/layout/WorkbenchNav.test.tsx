import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import WorkbenchNav, { type WorkbenchKey } from './WorkbenchNav'
import { I18nProvider } from '../state/I18nContext'

describe('WorkbenchNav 左侧导航栏组件', () => {
  it('渲染三大导航分组及全部 10 个工作台入口', () => {
    const onChange = vi.fn()
    render(<WorkbenchNav active="home" onChange={onChange} />)

    // 分组标题
    expect(screen.getByText('创作')).toBeInTheDocument()
    expect(screen.getByText('管理')).toBeInTheDocument()
    expect(screen.getByText('帮助')).toBeInTheDocument()

    // 10 个工作台导航项
    expect(screen.getByText('首页')).toBeInTheDocument()
    expect(screen.getByText('分析拆书')).toBeInTheDocument()
    expect(screen.getByText('辅助写作')).toBeInTheDocument()
    expect(screen.getByText('质量检验')).toBeInTheDocument()
    expect(screen.getByText('资产库')).toBeInTheDocument()
    expect(screen.getByText('高级功能')).toBeInTheDocument()
    expect(screen.getByText('系统')).toBeInTheDocument()
    expect(screen.getByText('设置')).toBeInTheDocument()
    expect(screen.getByText('管理后台')).toBeInTheDocument()
    expect(screen.getByText('帮助中心')).toBeInTheDocument()

    // 版本号展示
    expect(screen.getByText('v2.3.0')).toBeInTheDocument()
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

  it('en-US 国际化语言下全导航项双语渲染', () => {
    const onChange = vi.fn()
    render(
      <I18nProvider initialLocale="en-US">
        <WorkbenchNav active="home" onChange={onChange} />
      </I18nProvider>,
    )

    // 分组
    expect(screen.getByText('Creation')).toBeInTheDocument()
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
    expect(screen.getByText('Administration')).toBeInTheDocument()
    expect(screen.getByText('Help Center')).toBeInTheDocument()
  })
})
