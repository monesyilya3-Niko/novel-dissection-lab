import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PoisonCheckPanel from './PoisonCheckPanel'
import { I18nProvider } from '../state/I18nContext'
import { writeStorage, removeStorage } from '../safeStorage'
import { toolsApi } from '../api/client'

vi.mock('../api/client', () => ({
  toolsApi: {
    checkPoison: vi.fn().mockResolvedValue({
      score: 25,
      verdict: '警告：存在部分憋屈或送人头情节',
      totalIssues: 1,
      findings: [
        {
          line: 3,
          type: 'excessive_suffering',
          typeName: '过度憋屈受辱',
          severity: 'fatal',
          snippet: '低头不敢出声，受尽了百般刁难',
          matched: '低头不敢出声',
          reason: '主角遭受侮辱无反击',
          suggestion: '当场展现反击动作',
        },
      ],
    }),
    getTaboos: vi.fn().mockResolvedValue({
      totalCount: 1,
      taboos: [
        {
          id: 'TB-001',
          name: '长篇憋屈无反击 (Excessive Suffering)',
          severity: 'fatal',
          description: '主角连续2章以上遭遇不公诬陷却隐忍自证。',
          readerReaction: '极度胸闷烦躁，直接弃书。',
          fixSuggestion: '受辱必须在同一章节内完成打脸反击。',
        },
      ],
    }),
  },
  friendlyError: (e: unknown) => String(e),
}))

describe('PoisonCheckPanel', () => {
  it('空输入显示独立错误提示，清空后移除提示且不发起扫描', () => {
    vi.mocked(toolsApi.checkPoison).mockClear()
    render(<PoisonCheckPanel />)

    fireEvent.click(screen.getByRole('button', { name: '一键扫描毒点' }))
    expect(screen.getByRole('alert')).toHaveTextContent('请先输入或粘贴需要排查的正文段落')
    expect(toolsApi.checkPoison).not.toHaveBeenCalled()

    fireEvent.click(screen.getByRole('button', { name: '清空' }))
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('渲染并执行毒点扫描', async () => {
    render(<PoisonCheckPanel />)
    expect(screen.getByText('毒点快速排查 (本地规则)')).toBeDefined()

    const textarea = screen.getByPlaceholderText('请在此粘贴需要检测的章节正文或剧情草稿...')
    fireEvent.change(textarea, { target: { value: '主角低头不敢出声，受尽了百般刁难。' } })

    const scanBtn = screen.getByText('一键扫描毒点')
    fireEvent.click(scanBtn)

    await waitFor(() => {
      expect(screen.getByText('警告：存在部分憋屈或送人头情节')).toBeDefined()
      expect(screen.getByText('过度憋屈受辱')).toBeDefined()
      expect(screen.getByText(/当场展现反击动作/)).toBeDefined()
    })
  })

  it('切换到弃坑避雷规范库', async () => {
    render(<PoisonCheckPanel />)
    fireEvent.click(screen.getByText('弃坑避雷规范库 (10大红线)'))

    await waitFor(() => {
      expect(screen.getByText('长篇憋屈无反击 (Excessive Suffering)')).toBeDefined()
      expect(screen.getByText(/受辱必须在同一章节内完成打脸反击/)).toBeDefined()
    })
  })

  it('窄屏下页签可滚动且规范卡片不会撑宽页面', async () => {
    render(<PoisonCheckPanel />)
    expect(screen.getByRole('tablist').parentElement).toHaveClass('MuiTabs-scrollableX')

    fireEvent.click(screen.getByText('弃坑避雷规范库 (10大红线)'))
    const cardTitle = await screen.findByText('长篇憋屈无反击 (Excessive Suffering)')
    const grid = cardTitle.closest('.MuiCard-root')?.parentElement
    expect(grid).toHaveStyle({
      gridTemplateColumns: 'repeat(auto-fill, minmax(min(360px, 100%), 1fr))',
    })
  })

  it('在 en-US 语言环境下渲染英文动作按钮与标签', async () => {
    writeStorage('novellab.locale', 'en-US')
    try {
      render(
        <I18nProvider>
          <PoisonCheckPanel />
        </I18nProvider>,
      )
      expect(screen.getByText('Anti-Poison Scanner (Local)')).toBeDefined()
      expect(screen.getByText('Fatal Taboo Library (10 Rules)')).toBeDefined()
      expect(screen.getByText('Scan for Taboos')).toBeDefined()
      expect(screen.getByText('Clear')).toBeDefined()
    } finally {
      removeStorage('novellab.locale')
    }
  })
})
