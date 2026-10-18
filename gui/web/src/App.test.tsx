import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import App from './App'
import { I18nProvider } from './state/I18nContext'
import { ThemeModeProvider } from './state/ThemeModeContext'
import { writeStorage, removeStorage } from './safeStorage'

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

vi.mock('./api/client', () => ({
  getStatus: vi.fn().mockResolvedValue({ bookId: 'b1', status: 'idle', cursor: '', done: 0, total: 0 }),
  getBook: vi.fn().mockResolvedValue({ bookId: 'b1', name: '测试书', chapters: [] }),
  getOverview: vi.fn().mockResolvedValue({ totalBooks: 1, totalAssets: 10 }),
  getChapter: vi.fn().mockResolvedValue({ chapterIndex: 1, title: '第一章' }),
  subscribeEvents: vi.fn().mockReturnValue(() => {}),
  systemApi: { settings: vi.fn().mockResolvedValue({}) },
  friendlyError: (e: unknown) => String(e),
}))

describe('App 顶层集成与多语言测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    removeStorage('novellab.locale')
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
})
