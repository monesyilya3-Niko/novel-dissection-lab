import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import ResultPanel from './ResultPanel'
import { I18nProvider } from '../state/I18nContext'

const mockGetAsset = vi.fn()

vi.mock('../api/client', () => ({
  getAsset: (...args: unknown[]) => mockGetAsset(...args),
  friendlyError: (e: unknown) => String(e),
}))

const mockAppState = {
  book: null as unknown,
  selectedChapter: null as number | null,
  currentChapter: null as unknown,
  batchStates: {} as Record<string, { status: string }>,
}

vi.mock('../state/AppContext', () => ({
  useApp: () => mockAppState,
}))

describe('ResultPanel 分析结果面板组件', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetAsset.mockResolvedValue({
      characters: ['林动', '绫清竹'],
      tension_peak: '九品古墓府争夺',
    })
  })

  it('未选择章节时渲染引导提示', () => {
    mockAppState.book = null
    mockAppState.selectedChapter = null
    render(<ResultPanel />)
    expect(screen.getByText('请先选择章节查看分析结果')).toBeInTheDocument()
  })

  it('en-US 环境下未选择章节展示英文引导提示', () => {
    mockAppState.book = null
    mockAppState.selectedChapter = null
    render(
      <I18nProvider initialLocale="en-US">
        <ResultPanel />
      </I18nProvider>,
    )
    expect(screen.getByText('Please select a chapter to view analysis results')).toBeInTheDocument()
  })

  it('选中章节时渲染批次选择、4 个 Pass 标签与产出 JSON 结果', async () => {
    mockAppState.book = { bookId: 'b1', title: '武动乾坤' }
    mockAppState.selectedChapter = 1
    mockAppState.currentChapter = { chapterIndex: 1, batchCount: 2 }
    mockAppState.batchStates = {
      'c1-b0': { status: 'success' },
      'c1-b1': { status: 'pending' },
    }

    render(<ResultPanel />)

    expect(screen.getByText(/分析结果 · 第1章/)).toBeInTheDocument()
    expect(screen.getByText('结构拆解')).toBeInTheDocument()
    expect(screen.getByText('人物弧光')).toBeInTheDocument()
    expect(screen.getByText('文风指纹')).toBeInTheDocument()
    expect(screen.getByText('商业评估')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument()

    // 等待数据加载并展示 JSON 内容
    await waitFor(() => {
      expect(screen.getByText(/九品古墓府争夺/)).toBeInTheDocument()
    })

    // 切换到人物弧光 Tab
    const charTab = screen.getByText('人物弧光')
    fireEvent.click(charTab)

    await waitFor(() => {
      expect(mockGetAsset).toHaveBeenCalledWith('b1', 1, 0, 'pass2_character')
    })
  })

  it('当资产为空时渲染尚未生成提示', async () => {
    mockAppState.book = { bookId: 'b1', title: '武动乾坤' }
    mockAppState.selectedChapter = 1
    mockAppState.currentChapter = { chapterIndex: 1, batchCount: 1 }
    mockAppState.batchStates = {}
    mockGetAsset.mockResolvedValueOnce({})

    render(<ResultPanel />)

    await waitFor(() => {
      expect(screen.getByText('该批次尚未生成此 pass 的结果（请先运行分析）')).toBeInTheDocument()
    })
  })

  it('en-US 环境下渲染全量英文标签与 Pass 阶段名称', async () => {
    mockAppState.book = { bookId: 'b1', title: 'Martial World' }
    mockAppState.selectedChapter = 2
    mockAppState.currentChapter = { chapterIndex: 2, batchCount: 1 }
    mockAppState.batchStates = {}
    mockGetAsset.mockResolvedValueOnce({
      structure: 'Climax reached',
    })

    render(
      <I18nProvider initialLocale="en-US">
        <ResultPanel />
      </I18nProvider>,
    )

    expect(screen.getByText(/Analysis Result · Ch\.2/)).toBeInTheDocument()
    expect(screen.getByText('Structure Pass')).toBeInTheDocument()
    expect(screen.getByText('Character Pass')).toBeInTheDocument()
    expect(screen.getByText('Style Pass')).toBeInTheDocument()
    expect(screen.getByText('Commercial Pass')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/Climax reached/)).toBeInTheDocument()
    })
  })
})
