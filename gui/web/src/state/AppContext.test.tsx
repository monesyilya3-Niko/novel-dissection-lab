import { render, screen, fireEvent, waitFor, act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import { useEffect } from 'react'
import { AppProvider, useApp, useAppOptional } from './AppContext'
import * as api from '../api/client'
import type { Book, Chapter, Overview, StatusInfo } from '../types'

vi.mock('../api/client', () => ({
  // 2026-11-03：AppContext 的初始化错误改走 friendlyError，mock 需提供
  // 与真实实现一致：普通 Error 取 message，其余 String()
  friendlyError: (e: unknown) => (e instanceof Error && e.message ? e.message : String(e)),
  getStatus: vi.fn(),
  getBook: vi.fn(),
  getOverview: vi.fn(),
  getChapter: vi.fn(),
  getBookResults: vi.fn(),
  importBook: vi.fn(),
  uploadBook: vi.fn(),
  importSample: vi.fn(),
  startAnalysis: vi.fn(),
  runFullAnalysis: vi.fn(),
  pauseAnalysis: vi.fn(),
  resumeAnalysis: vi.fn(),
  retryFailed: vi.fn(),
  subscribeEvents: vi.fn(),
  systemApi: {
    settings: vi.fn(),
  },
}))

const sampleBook: Book = {
  bookId: 'b-101',
  title: '天风海雨录',
  sourcePath: '/path/to/novel.txt',
  totalChapters: 2,
  chapters: [
    {
      index: 1,
      title: '第一回 风起青萍',
      batchCount: 2,
      batches: [
        { chapterIndex: 1, batchIndex: 0, charStart: 0, charEnd: 1000, text: '...', status: 'pending' },
        { chapterIndex: 1, batchIndex: 1, charStart: 1000, charEnd: 2000, text: '...', status: 'pending' },
      ],
    },
    {
      index: 2,
      title: '第二回 云涌大荒',
      batchCount: 1,
      batches: [
        { chapterIndex: 2, batchIndex: 0, charStart: 0, charEnd: 1500, text: '...', status: 'success' },
      ],
    },
  ],
}

const sampleChapter: Chapter = {
  index: 1,
  title: '第一回 风起青萍',
  batchCount: 2,
  text: '第一回 风起青萍 全文内容...',
  batches: [
    { chapterIndex: 1, batchIndex: 0, charStart: 0, charEnd: 1000, text: '...', status: 'pending' },
    { chapterIndex: 1, batchIndex: 1, charStart: 1000, charEnd: 2000, text: '...', status: 'pending' },
  ],
}

const sampleOverview: Overview = {
  totalBooks: 3,
  totalGenrePacks: 1,
  totalReports: 2,
  totalAssets: 42,
  assetsByKind: { voice: 10, structure: 5 },
  modelConfigured: true,
  recentActivity: ['Imported b-101'],
}

const sampleStatus: StatusInfo = {
  bookId: 'b-101',
  status: 'idle',
  cursor: '',
  done: 0,
  total: 3,
}

let capturedCtx: ReturnType<typeof useApp> | null = null
let sseCallback: ((e: any) => void) | null = null
const mockCloseSse = vi.fn()

function TestConsumer() {
  const ctx = useApp()
  useEffect(() => {
    capturedCtx = ctx
  })
  return (
    <div>
      <div data-testid="workbench">{ctx.workbench}</div>
      <div data-testid="book-title">{ctx.book?.title ?? 'no-book'}</div>
      <div data-testid="qualityPassLine">{ctx.qualityPassLine}</div>
      <div data-testid="consistencyTarget">{ctx.consistencyTarget}</div>
      <div data-testid="initError">{ctx.initError ?? 'none'}</div>
      <div data-testid="selectedChapter">{ctx.selectedChapter ?? 'none'}</div>
      <div data-testid="currentChapter">{ctx.currentChapter?.title ?? 'none'}</div>
      <div data-testid="helpNonce">{ctx.helpRequest?.nonce ?? 0}</div>
      <button onClick={() => ctx.setWorkbench('analysis')}>Go Analysis</button>
      <button onClick={() => ctx.openHelp('guides', 'guide-anchor-1')}>Open Help</button>
      <button onClick={() => ctx.selectChapter(1)}>Select Ch 1</button>
      <button onClick={() => ctx.startAnalysis('xuanhuan')}>Start Analysis</button>
      <button onClick={() => ctx.runFullAnalysis('xuanhuan')}>Full Analysis</button>
      <button onClick={() => ctx.pauseAnalysis()}>Pause</button>
      <button onClick={() => ctx.resumeAnalysis()}>Resume</button>
      <button onClick={() => ctx.retryFailed()}>Retry</button>
      <button onClick={() => ctx.importBook('/path/test.txt')}>Import Book</button>
      <button onClick={() => ctx.uploadBook(new File(['txt'], 'sample.txt'))}>Upload Book</button>
      <button onClick={() => ctx.importSampleBook('demo')}>Import Sample</button>
      <button onClick={() => ctx.refreshThresholds()}>Refresh Thresholds</button>
    </div>
  )
}

describe('AppContext 全局状态上下文与业务编排测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    capturedCtx = null
    sseCallback = null

    vi.mocked(api.getStatus).mockResolvedValue(sampleStatus)
    vi.mocked(api.getBook).mockResolvedValue(sampleBook)
    vi.mocked(api.getOverview).mockResolvedValue(sampleOverview)
    vi.mocked(api.getChapter).mockResolvedValue(sampleChapter)
    vi.mocked(api.getBookResults).mockResolvedValue({ bookId: 'b-101', reportIds: ['r1'] } as any)
    vi.mocked(api.importBook).mockResolvedValue(sampleBook)
    vi.mocked(api.uploadBook).mockResolvedValue(sampleBook)
    vi.mocked(api.importSample).mockResolvedValue(sampleBook)
    vi.mocked(api.startAnalysis).mockResolvedValue({} as any)
    vi.mocked(api.runFullAnalysis).mockResolvedValue({} as any)
    vi.mocked(api.pauseAnalysis).mockResolvedValue({} as any)
    vi.mocked(api.resumeAnalysis).mockResolvedValue({} as any)
    vi.mocked(api.retryFailed).mockResolvedValue({} as any)
    vi.mocked(api.subscribeEvents).mockImplementation((_bid, onEvent) => {
      sseCallback = onEvent
      return mockCloseSse
    })
    vi.mocked(api.systemApi.settings).mockResolvedValue({
      thresholds: { qualityPassLine: 80, consistencyTarget: 92 },
    } as any)
  })

  it('useApp 与 useAppOptional 在 Provider 外调用时的断言与降级行为', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {})
    try {
      // useApp 在 Provider 外必须抛出异常
      expect(() => {
        renderHook(() => useApp())
      }).toThrow('useApp 必须在 AppProvider 内使用')

      // useAppOptional 在 Provider 外应安全返回 null
      const { result } = renderHook(() => useAppOptional())
      expect(result.current).toBeNull()
    } finally {
      spy.mockRestore()
    }
  })

  it('组件挂载时自动初始化 status、book、overview、thresholds 并订阅 SSE', async () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('book-title').textContent).toBe('天风海雨录')
    })

    expect(screen.getByTestId('qualityPassLine').textContent).toBe('80')
    expect(screen.getByTestId('consistencyTarget').textContent).toBe('92')
    expect(screen.getByTestId('initError').textContent).toBe('none')

    expect(api.getStatus).toHaveBeenCalled()
    expect(api.getBook).toHaveBeenCalledWith('b-101')
    expect(api.getOverview).toHaveBeenCalled()
    expect(api.systemApi.settings).toHaveBeenCalled()
    expect(api.subscribeEvents).toHaveBeenCalled()
  })

  it('初始化 status 或 overview 失败时捕获并写入 initError', async () => {
    vi.mocked(api.getStatus).mockRejectedValueOnce(new Error('后端连接失败 503'))

    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('initError').textContent).toBe('后端连接失败 503')
    })
  })

  it('refreshThresholds 可动态更新阈值并在接口报错时保持现有值', async () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('qualityPassLine').textContent).toBe('80')
    })

    // 模拟设置更新
    vi.mocked(api.systemApi.settings).mockResolvedValueOnce({
      thresholds: { qualityPassLine: 85, consistencyTarget: 95 },
    } as any)

    fireEvent.click(screen.getByText('Refresh Thresholds'))

    await waitFor(() => {
      expect(screen.getByTestId('qualityPassLine').textContent).toBe('85')
      expect(screen.getByTestId('consistencyTarget').textContent).toBe('95')
    })

    // 接口报错时不崩溃且保持旧值
    vi.mocked(api.systemApi.settings).mockRejectedValueOnce(new Error('网络闪断'))
    fireEvent.click(screen.getByText('Refresh Thresholds'))

    await waitFor(() => {
      expect(screen.getByTestId('qualityPassLine').textContent).toBe('85')
    })
  })

  it('importBook、uploadBook、importSampleBook 成功后更新当前书并初始化各批次状态', async () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(capturedCtx?.book).not.toBeNull()
    })

    // 测试 importBook
    await act(async () => {
      await capturedCtx!.importBook('/path/to/novel.txt')
    })
    expect(api.importBook).toHaveBeenCalledWith('/path/to/novel.txt')
    expect(capturedCtx!.batchStates['c1-b0']).toEqual({ status: 'pending' })
    expect(capturedCtx!.batchStates['c1-b1']).toEqual({ status: 'pending' })
    expect(capturedCtx!.batchStates['c2-b0']).toEqual({ status: 'success' })

    // 测试 uploadBook
    const dummyFile = new File(['novel text'], 'my_book.txt')
    await act(async () => {
      await capturedCtx!.uploadBook(dummyFile)
    })
    expect(api.uploadBook).toHaveBeenCalledWith(dummyFile)

    // 测试 importSampleBook
    await act(async () => {
      await capturedCtx!.importSampleBook('demo')
    })
    expect(api.importSample).toHaveBeenCalledWith('demo')
  })

  it('selectChapter 获取章节详情并写入 currentChapter', async () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(capturedCtx?.book).not.toBeNull()
    })

    fireEvent.click(screen.getByText('Select Ch 1'))

    await waitFor(() => {
      expect(screen.getByTestId('selectedChapter').textContent).toBe('1')
      expect(screen.getByTestId('currentChapter').textContent).toBe('第一回 风起青萍')
    })
    expect(api.getChapter).toHaveBeenCalledWith('b-101', 1)
  })

  it('拆书分析控制方法 (start, full, pause, resume, retry) 正常调用并刷新状态', async () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(capturedCtx?.book).not.toBeNull()
    })

    // startAnalysis
    fireEvent.click(screen.getByText('Start Analysis'))
    await waitFor(() => {
      expect(api.startAnalysis).toHaveBeenCalledWith('b-101', 'xuanhuan')
    })

    // runFullAnalysis
    fireEvent.click(screen.getByText('Full Analysis'))
    await waitFor(() => {
      expect(api.runFullAnalysis).toHaveBeenCalledWith('b-101', 'xuanhuan')
    })

    // pauseAnalysis
    fireEvent.click(screen.getByText('Pause'))
    await waitFor(() => {
      expect(api.pauseAnalysis).toHaveBeenCalledWith('b-101')
    })

    // resumeAnalysis
    fireEvent.click(screen.getByText('Resume'))
    await waitFor(() => {
      expect(api.resumeAnalysis).toHaveBeenCalledWith('b-101')
    })

    // retryFailed
    fireEvent.click(screen.getByText('Retry'))
    await waitFor(() => {
      expect(api.retryFailed).toHaveBeenCalledWith('b-101')
    })
  })

  it('openHelp 切换工作台至 help 并自增 nonce 标识', async () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(screen.getByTestId('book-title').textContent).toBe('天风海雨录')
    })

    expect(screen.getByTestId('workbench').textContent).toBe('home')
    expect(screen.getByTestId('helpNonce').textContent).toBe('0')

    // 第一次打开帮助中心
    fireEvent.click(screen.getByText('Open Help'))
    expect(screen.getByTestId('workbench').textContent).toBe('help')
    expect(screen.getByTestId('helpNonce').textContent).toBe('1')
    expect(capturedCtx!.helpRequest).toEqual({
      tab: 'guides',
      anchor: 'guide-anchor-1',
      nonce: 1,
    })

    // 第二次打开相同位置，nonce 自增以触发子页面重定位
    fireEvent.click(screen.getByText('Open Help'))
    expect(screen.getByTestId('helpNonce').textContent).toBe('2')
    expect(capturedCtx!.helpRequest?.nonce).toBe(2)
  })

  it('loadBookResults 与 refreshBookResults 正确加载并静默处理无结果情况', async () => {
    render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(capturedCtx?.book).not.toBeNull()
    })

    await act(async () => {
      await capturedCtx!.loadBookResults('b-101')
    })
    expect(capturedCtx!.bookResults).toEqual({ bookId: 'b-101', reportIds: ['r1'] })

    // refreshBookResults
    await act(async () => {
      await capturedCtx!.refreshBookResults()
    })
    expect(api.getBookResults).toHaveBeenCalledWith('b-101')

    // 当无结果抛错时静默保持，不抛给外部
    vi.mocked(api.getBookResults).mockRejectedValueOnce(new Error('无拆书报告'))
    await act(async () => {
      await expect(capturedCtx!.refreshBookResults()).resolves.toBeUndefined()
    })
  })

  it('SSE 事件推送：接收 batch 状态并在 done 与 report_ready 时自动刷新数据', async () => {
    const { unmount } = render(
      <AppProvider>
        <TestConsumer />
      </AppProvider>,
    )

    await waitFor(() => {
      expect(sseCallback).not.toBeNull()
    })

    // 推送 running 事件
    act(() => {
      sseCallback!({
        cursor: 'c1-b0',
        chapterIndex: 1,
        batchIndex: 0,
        status: 'running',
        done: 0,
        total: 2,
      })
    })

    expect(capturedCtx!.lastEvent?.status).toBe('running')
    expect(capturedCtx!.batchStates['c1-b0']).toEqual({ status: 'running' })

    // 推送 success 事件
    act(() => {
      sseCallback!({
        cursor: 'c1-b0',
        chapterIndex: 1,
        batchIndex: 0,
        status: 'success',
        done: 1,
        total: 2,
      })
    })
    expect(capturedCtx!.batchStates['c1-b0']).toEqual({ status: 'success' })

    // 推送 done 事件 -> 触发 refreshStatus, refreshBookResults, refreshOverview
    const prevStatusCallCount = vi.mocked(api.getStatus).mock.calls.length
    const prevOverviewCallCount = vi.mocked(api.getOverview).mock.calls.length
    act(() => {
      sseCallback!({
        cursor: 'c1-b1',
        chapterIndex: 1,
        batchIndex: 1,
        status: 'done',
        done: 2,
        total: 2,
      })
    })
    expect(vi.mocked(api.getStatus).mock.calls.length).toBeGreaterThan(prevStatusCallCount)
    expect(vi.mocked(api.getOverview).mock.calls.length).toBeGreaterThan(prevOverviewCallCount)

    // 推送 report_ready 事件 -> 触发 refreshBookResults, refreshOverview
    act(() => {
      sseCallback!({
        cursor: 'report',
        chapterIndex: 1,
        batchIndex: 1,
        status: 'report_ready',
        done: 2,
        total: 2,
      })
    })

    // 卸载组件触发 SSE 关闭
    unmount()
    expect(mockCloseSse).toHaveBeenCalled()
  })
})
