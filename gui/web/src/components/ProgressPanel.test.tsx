import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import ProgressPanel from './ProgressPanel'
import { I18nProvider } from '../state/I18nContext'

const mockRunOfflineAnalysis = vi.fn()
const mockGetTakeoverStatus = vi.fn()
const mockGetTakeoverPass = vi.fn()
const mockSaveTakeoverPass = vi.fn()
const mockGenerateBookReports = vi.fn()
const mockListGenres = vi.fn()

vi.mock('../api/client', () => ({
  runOfflineAnalysis: (...args: any[]) => mockRunOfflineAnalysis(...args),
  getTakeoverStatus: (...args: any[]) => mockGetTakeoverStatus(...args),
  getTakeoverPass: (...args: any[]) => mockGetTakeoverPass(...args),
  saveTakeoverPass: (...args: any[]) => mockSaveTakeoverPass(...args),
  generateBookReports: (...args: any[]) => mockGenerateBookReports(...args),
  listGenres: () => mockListGenres(),
  getGenres: () => mockListGenres(),
  friendlyError: (e: unknown) => (e instanceof Error ? e.message : String(e)),
}))

const mockLoadBookResults = vi.fn()
const mockRefreshOverview = vi.fn()

const mockAppState = {
  book: null as unknown,
  batchStates: {} as Record<string, { status: string }>,
  status: { status: 'idle', done: 0, total: 0, cursor: '' },
  loadBookResults: mockLoadBookResults,
  refreshOverview: mockRefreshOverview,
}

vi.mock('../state/AppContext', () => ({
  useApp: () => mockAppState,
}))

describe('ProgressPanel 分析进度面板组件', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListGenres.mockResolvedValue(['xianxia', 'kehuan'])
    mockGetTakeoverStatus.mockResolvedValue({
      bookId: 'b1',
      sampledReady: false,
      passes: [],
      assembledCards: [],
      reports: [],
    })
  })
  it('未导入书籍时渲染空提示', () => {
    mockAppState.book = null
    render(<ProgressPanel />)
    expect(screen.getByText('请先导入书籍')).toBeInTheDocument()
  })

  it('en-US 环境下未导入书籍渲染英文空提示', () => {
    mockAppState.book = null
    render(
      <I18nProvider initialLocale="en-US">
        <ProgressPanel />
      </I18nProvider>,
    )
    expect(screen.getByText('Please import a book first')).toBeInTheDocument()
  })

  it('渲染进度条、计算完成批次与章×批状态矩阵', () => {
    mockAppState.book = {
      bookId: 'b1',
      title: '诡秘之主',
      totalChapters: 2,
      chapters: [
        { index: 1, title: '第一章 绯红', batchCount: 2 },
        { index: 2, title: '第二章 局势', batchCount: 2 },
      ],
    }
    mockAppState.batchStates = {
      'c1-b0': { status: 'success' },
      'c1-b1': { status: 'success' },
      'c2-b0': { status: 'running' },
      'c2-b1': { status: 'pending' },
    }
    mockAppState.status = { status: 'running', done: 2, total: 4, cursor: 'c2-b0' }

    render(<ProgressPanel />)

    expect(screen.getByText('分析进度')).toBeInTheDocument()
    // 2 / 4 批 · 50%
    expect(screen.getByText(/2\s*\/\s*4\s*批\s*·\s*50%/)).toBeInTheDocument()
    // 当前状态与检查点
    expect(screen.getByText(/当前状态：运行中 · 断点 c2-b0/)).toBeInTheDocument()

    // 章节行
    expect(screen.getByText('第1章')).toBeInTheDocument()
    expect(screen.getByText('第2章')).toBeInTheDocument()

    // 图例标签
    expect(screen.getByText('等待')).toBeInTheDocument()
    expect(screen.getByText('运行中')).toBeInTheDocument()
    expect(screen.getByText('成功')).toBeInTheDocument()
    expect(screen.getByText('失败')).toBeInTheDocument()
    expect(screen.getByText('跳过')).toBeInTheDocument()
  })

  it('en-US 环境下渲染英文进度与图例', () => {
    mockAppState.book = {
      bookId: 'b1',
      title: 'Dune',
      totalChapters: 1,
      chapters: [
        { index: 1, title: 'Chapter 1 Arrakis', batchCount: 1 },
      ],
    }
    mockAppState.batchStates = {
      'c1-b0': { status: 'success' },
    }
    mockAppState.status = { status: 'success', done: 1, total: 1, cursor: 'c1-b0' }

    render(
      <I18nProvider initialLocale="en-US">
        <ProgressPanel />
      </I18nProvider>,
    )

    expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    expect(screen.getByText(/1\s*\/\s*1\s*batches\s*·\s*100%/i)).toBeInTheDocument()
    expect(screen.getByText(/Current Status：Success · Checkpoint c1-b0/i)).toBeInTheDocument()
    expect(screen.getByText('Ch.1')).toBeInTheDocument()

    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Success')).toBeInTheDocument()
  })

  it('offlineTriggerNonce > 0 首次挂载自动触发离线量化拆解，完成 Pass 1–5 网页 AI 接管全流程', async () => {
    mockAppState.book = {
      bookId: 'b1',
      title: '诡秘之主',
      totalChapters: 2,
      chapters: [
        { index: 1, title: '第一章 绯红', batchCount: 1 },
        { index: 2, title: '第二章 局势', batchCount: 1 },
      ],
    }
    mockAppState.batchStates = {}
    mockAppState.status = { status: 'idle', done: 0, total: 2, cursor: '' }

    mockRunOfflineAnalysis.mockResolvedValue({
      bookId: 'b1',
      genre: 'xianxia',
      totalChapters: 2,
      selectedCount: 2,
      sampleWords: 6000,
      guidePath: 'reports/b1-guide.md',
      guideMarkdown: '# 离线接管指南',
      metrics: { avgSentenceLen: 18.5, dialogueRatio: 0.34, charTtr: 0.42 },
    })
    mockGetTakeoverStatus
      .mockResolvedValueOnce({
        bookId: 'b1',
        sampledReady: false,
        passes: [],
        assembledCards: [],
        reports: [],
      })
      .mockResolvedValueOnce({
        bookId: 'b1',
        sampledReady: true,
        passes: [
          { passName: 'pass1_structure', label: 'Pass 1 · 结构与节拍', saved: false, sizeBytes: 0, updatedAt: null },
          { passName: 'pass2_character', label: 'Pass 2 · 人物与声线', saved: false, sizeBytes: 0, updatedAt: null },
        ],
        assembledCards: [],
        reports: [],
      })
      .mockResolvedValueOnce({
        bookId: 'b1',
        sampledReady: true,
        passes: [
          { passName: 'pass1_structure', label: 'Pass 1 · 结构与节拍', saved: true, sizeBytes: 512, updatedAt: 1000 },
          { passName: 'pass2_character', label: 'Pass 2 · 人物与声线', saved: false, sizeBytes: 0, updatedAt: null },
        ],
        assembledCards: [],
        reports: [],
      })
    mockGetTakeoverPass.mockResolvedValue({
      bookId: 'b1',
      passName: 'pass1_structure',
      promptBundle: '=== PASS 1 PROMPT + SAMPLE ===',
      charCount: 30,
      saved: false,
      existingJson: null,
    })
    mockSaveTakeoverPass.mockResolvedValue({
      bookId: 'b1',
      passName: 'pass1_structure',
      savedPath: 'gui_state/passes/b1/pass1_structure.json',
      keys: ['opening_hook', 'pacing'],
      sizeBytes: 512,
    })
    mockGenerateBookReports.mockResolvedValue({
      bookId: 'b1',
      assembled: ['voice-b1.json', 'craft-b1.json'],
      reports: ['b1-report.md', 'b1-craft.md'],
      reportOk: true,
      totalChars: 12800,
    })

    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.assign(navigator, { clipboard: { writeText } })

    render(<ProgressPanel offlineTriggerNonce={1} genre="xianxia" />)

    // 1. 挂载后立即响应 offlineTriggerNonce 自动运行离线拆解并展开接管工作台
    await waitFor(() => {
      expect(mockRunOfflineAnalysis).toHaveBeenCalledWith('b1', 'xianxia')
      expect(screen.getByTestId('takeover-workbench')).toBeInTheDocument()
    })

    // 2. 点击复制本 Pass 完整投喂包
    fireEvent.click(screen.getByRole('button', { name: '复制本 Pass 完整投喂包' }))
    await waitFor(() => {
      expect(mockGetTakeoverPass).toHaveBeenCalledWith('b1', 'pass1_structure')
      expect(writeText).toHaveBeenCalledWith('=== PASS 1 PROMPT + SAMPLE ===')
      expect(screen.getByText(/已复制本 Pass 投喂包/)).toBeInTheDocument()
    })

    // 3. 粘贴 AI 返回的 JSON 代码块并入库
    const pasteBox = screen.getByPlaceholderText(/将任意网页版 AI/)
    fireEvent.change(pasteBox, { target: { value: '```json\n{"opening_hook":"绯红之月","pacing":"紧凑"}\n```' } })
    fireEvent.click(screen.getByRole('button', { name: '保存本 Pass JSON' }))

    await waitFor(() => {
      expect(mockSaveTakeoverPass).toHaveBeenCalledWith(
        'b1',
        'pass1_structure',
        '```json\n{"opening_hook":"绯红之月","pacing":"紧凑"}\n```',
      )
      expect(screen.getByText(/已保存 pass1_structure（字段数：2）/)).toBeInTheDocument()
    })

    // 4. 一键组装四维资产并生成万字双报告
    fireEvent.click(screen.getByRole('button', { name: '一键组装四维资产并生成万字双报告' }))
    await waitFor(() => {
      expect(mockGenerateBookReports).toHaveBeenCalledWith('b1', { genre: 'xianxia', assemble: true })
      expect(mockLoadBookResults).toHaveBeenCalledWith('b1')
      expect(mockRefreshOverview).toHaveBeenCalled()
      expect(screen.getByText(/已组装 2 张资产卡，生成 2 份报告（共 12,800 字）/)).toBeInTheDocument()
    })
  })
})
