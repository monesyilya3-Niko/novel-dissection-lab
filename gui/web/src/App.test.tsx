import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import App from './App'
import { replayOnboarding } from './components/OnboardingWizard'
import { I18nProvider } from './state/I18nContext'
import { ThemeModeProvider } from './state/ThemeModeContext'
import { writeStorage, removeStorage } from './safeStorage'
import { getStatus, getOverview } from './api/client'

// App 依赖 useThemeMode，测试需 mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

vi.mock('./components/HomeDashboard', () => ({ default: () => <div data-testid="workbench-home">HomeDashboard</div> }))
vi.mock('./components/AnalysisView', () => ({ default: () => <div data-testid="workbench-analysis">AnalysisView</div> }))
vi.mock('./components/AssetLibrary', () => ({ default: () => <div data-testid="workbench-assets">AssetLibrary</div> }))
vi.mock('./components/WritingWorkbench', () => ({ default: () => <div data-testid="workbench-writing">WritingWorkbench</div> }))
vi.mock('./components/QualityWorkbench', () => ({ default: () => <div data-testid="workbench-quality">QualityWorkbench</div> }))
vi.mock('./components/SystemWorkbench', () => ({ default: () => <div data-testid="workbench-system">SystemWorkbench</div> }))
vi.mock('./components/AdvancedWorkbench', () => ({ default: () => <div data-testid="workbench-advanced">AdvancedWorkbench</div> }))
vi.mock('./components/SettingsWorkbench', () => ({ default: () => <div data-testid="workbench-settings">SettingsWorkbench</div> }))
vi.mock('./components/AdminWorkbench', () => ({ default: () => <div data-testid="workbench-admin">AdminWorkbench</div> }))
vi.mock('./components/HelpWorkbench', () => ({ default: () => <div data-testid="workbench-help">HelpWorkbench</div> }))

vi.mock('./api/client', () => ({
  getStatus: vi.fn().mockResolvedValue({ bookId: 'b1', status: 'idle', cursor: '', done: 0, total: 0 }),
  getBook: vi.fn().mockResolvedValue({ bookId: 'b1', name: '测试书', chapters: [] }),
  getOverview: vi.fn().mockResolvedValue({ totalBooks: 1, totalAssets: 10 }),
  getChapter: vi.fn().mockResolvedValue({ chapterIndex: 1, title: '第一章' }),
  getBookResults: vi.fn().mockResolvedValue(null),
  subscribeEvents: vi.fn().mockReturnValue(() => {}),
  systemApi: { settings: vi.fn().mockResolvedValue({}) },
  friendlyError: (e: unknown) => String(e),
}))

describe('App 顶层应用框架与导航集成测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    removeStorage('novellab.locale')
    removeStorage('novellab.themeMode')
    removeStorage('novellab.onboarded')
    vi.mocked(getStatus).mockResolvedValue({ bookId: 'b1', status: 'idle', cursor: '', done: 0, total: 0 } as any)
    vi.mocked(getOverview).mockResolvedValue({ totalBooks: 1, totalAssets: 10 } as any)
  })

  it('在 zh-CN 环境下渲染默认中文品牌与帮助中心悬浮按钮', async () => {
    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )
    expect(await screen.findByText('暮冬念春')).toBeDefined()
    expect(screen.getByText('全功能工作台')).toBeDefined()
    expect(screen.getByLabelText('打开帮助中心')).toBeDefined()
    expect(screen.getByLabelText('打开导航')).toBeDefined()
  })

  it('在 en-US 环境下渲染英文品牌与英文帮助中心悬浮按钮', async () => {
    writeStorage('novellab.locale', 'en-US')
    try {
      render(
        <ThemeModeProvider>
          <I18nProvider>
            <App />
          </I18nProvider>
        </ThemeModeProvider>,
      )
      expect(await screen.findByText('Exoscribe')).toBeDefined()
      expect(screen.getByText('The Vernal Engine for Fiction')).toBeDefined()
      expect(screen.getByLabelText('Open Help Center')).toBeDefined()
      expect(screen.getByLabelText('Open Navigation')).toBeDefined()
    } finally {
      removeStorage('novellab.locale')
    }
  })

  it('ModeToggle 主题循环切换 (system -> light -> dark -> system)', async () => {
    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )

    // 默认 system -> 点击切换为 light（按钮提示 '切换亮色'）
    const toggleBtn = await screen.findByLabelText('切换亮色')
    expect(toggleBtn).toBeDefined()

    // 点击切换为 light 模式，此时 next 变成 dark，提示变为 '切换暗色'
    fireEvent.click(toggleBtn)
    expect(screen.getByLabelText('切换暗色')).toBeDefined()

    // 再次点击切换为 dark 模式，此时 next 变成 system，提示变为 '切换为跟随系统'
    fireEvent.click(screen.getByLabelText('切换暗色'))
    expect(screen.getByLabelText('切换为跟随系统')).toBeDefined()

    // 再次点击切换回 system 模式，提示变回 '切换亮色'
    fireEvent.click(screen.getByLabelText('切换为跟随系统'))
    expect(screen.getByLabelText('切换亮色')).toBeDefined()
  })

  it('支持 Alt+1..9 快捷键切换不同工作台，初始在首页', async () => {
    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )

    expect(await screen.findByTestId('workbench-home')).toBeDefined()

    // Alt+2 -> 切换到 analysis (分析拆书)
    fireEvent.keyDown(window, { key: '2', altKey: true })
    expect(await screen.findByTestId('workbench-analysis')).toBeDefined()

    // Alt+3 -> 切换到 writing (辅助写作)
    fireEvent.keyDown(window, { key: '3', altKey: true })
    expect(await screen.findByTestId('workbench-writing')).toBeDefined()

    // Alt+4 -> 切换到 quality (质量检验)
    fireEvent.keyDown(window, { key: '4', altKey: true })
    expect(await screen.findByTestId('workbench-quality')).toBeDefined()

    // Alt+5 -> 切换到 assets (资产库)
    fireEvent.keyDown(window, { key: '5', altKey: true })
    expect(await screen.findByTestId('workbench-assets')).toBeDefined()

    // Alt+1 -> 切回 home
    fireEvent.keyDown(window, { key: '1', altKey: true })
    expect(await screen.findByTestId('workbench-home')).toBeDefined()
  })

  it('在文本输入框聚焦时不会触发 Alt+1..9 导航劫持', async () => {
    render(
      <ThemeModeProvider>
        <I18nProvider>
          <div>
            <input data-testid="dummy-input" defaultValue="test text" />
            <App />
          </div>
        </I18nProvider>
      </ThemeModeProvider>,
    )

    expect(await screen.findByTestId('workbench-home')).toBeDefined()
    const input = screen.getByTestId('dummy-input')

    // 在 input 元素上触发 Alt+2 键盘事件
    fireEvent.keyDown(input, { key: '2', altKey: true })

    // 依然停留在 home，未被切换至 analysis
    expect(screen.getByTestId('workbench-home')).toBeDefined()
    expect(screen.queryByTestId('workbench-analysis')).toBeNull()
  })

  it('帮助中心悬浮按钮 (FAB) 点击跳转至 help 工作台并在该工作台下自动隐藏', async () => {
    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )

    const fab = await screen.findByLabelText('打开帮助中心')
    expect(fab).toBeDefined()

    // 点击 FAB 跳转帮助中心
    fireEvent.click(fab)

    // 工作台渲染为 HelpWorkbench
    expect(await screen.findByTestId('workbench-help')).toBeDefined()

    // FAB 在 help 页面隐藏
    expect(screen.queryByLabelText('打开帮助中心')).toBeNull()
  })

  it('移动端导航抽屉可展开并通过点击选项切换工作台', async () => {
    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )

    const menuBtn = await screen.findByLabelText('打开导航')
    fireEvent.click(menuBtn)

    // 抽屉内包含导航项，点击“分析拆书”
    const analysisNav = screen.getAllByText('分析拆书')[0]
    fireEvent.click(analysisNav)

    expect(await screen.findByTestId('workbench-analysis')).toBeDefined()
  })

  it('初始化失败时顶层展示错误警告 Alert', async () => {
    vi.mocked(getStatus).mockRejectedValueOnce(new Error('无法连接后端服务'))

    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )

    expect(await screen.findByText(/初始化失败：无法连接后端服务/)).toBeDefined()
  })

  it('无书籍且无资产且未完成过引导时展示 OnboardingWizard 引导弹窗', async () => {
    vi.mocked(getOverview).mockResolvedValue({ totalBooks: 0, totalAssets: 0 } as any)

    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )

    // OnboardingWizard 出现
    expect(await screen.findByText('欢迎使用暮冬念春')).toBeDefined()

    // 点击跳过
    const skipBtn = screen.getByText('跳过')
    fireEvent.click(skipBtn)

    await waitFor(() => {
      expect(screen.queryByText('欢迎使用暮冬念春')).toBeNull()
    })
  })

  it('已有数据时点「重看引导」仍然弹出向导（不受空库条件限制）', async () => {
    // 有书有资产 —— 首次自动弹出条件不满足
    vi.mocked(getOverview).mockResolvedValue({ totalBooks: 3, totalAssets: 20 } as any)

    render(
      <ThemeModeProvider>
        <I18nProvider>
          <App />
        </I18nProvider>
      </ThemeModeProvider>,
    )

    // 等首屏渲染完成，确认没有自动弹出
    await waitFor(() => {
      expect(screen.queryByText('欢迎使用暮冬念春')).toBeNull()
    })

    // 触发重播（HomeDashboard/HelpWorkbench 上的按钮走同一事件）
    act(() => {
      replayOnboarding()
    })

    expect(await screen.findByText('欢迎使用暮冬念春')).toBeDefined()
  })
})

