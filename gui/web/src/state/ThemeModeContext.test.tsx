import { render, screen, fireEvent, act } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { ThemeModeProvider, useThemeMode } from './ThemeModeContext'

let mediaListeners: Array<(e: MediaQueryListEvent) => void> = []
let matchesDark = false

function createMockMediaQueryList(matches: boolean): MediaQueryList {
  return {
    matches,
    media: '(prefers-color-scheme: dark)',
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn((event: string, listener: (e: MediaQueryListEvent) => void) => {
      if (event === 'change') {
        mediaListeners.push(listener)
      }
    }),
    removeEventListener: vi.fn((_event: string, listener: (e: MediaQueryListEvent) => void) => {
      mediaListeners = mediaListeners.filter((l) => l !== listener)
    }),
    dispatchEvent: vi.fn(),
  } as unknown as MediaQueryList
}

function ConsumerComponent() {
  const { mode, setMode, isDark } = useThemeMode()
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <span data-testid="isDark">{isDark ? 'dark-active' : 'light-active'}</span>
      <button onClick={() => setMode('light')}>Set Light</button>
      <button onClick={() => setMode('dark')}>Set Dark</button>
      <button onClick={() => setMode('system')}>Set System</button>
    </div>
  )
}

describe('ThemeModeContext 主题模式与系统偏好管理', () => {
  beforeEach(() => {
    mediaListeners = []
    matchesDark = false
    localStorage.clear()

    window.matchMedia = vi.fn().mockImplementation((query: string) => {
      if (query.includes('dark')) {
        return createMockMediaQueryList(matchesDark)
      }
      return createMockMediaQueryList(false)
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    localStorage.clear()
  })

  it('useThemeMode 在 Provider 之外调用时返回安全的默认值', () => {
    render(<ConsumerComponent />)
    expect(screen.getByTestId('mode').textContent).toBe('system')
    expect(screen.getByTestId('isDark').textContent).toBe('light-active')
  })

  it('初始无存储记录且系统偏好为浅色时，默认模式为 system 且 isDark 为 false', () => {
    matchesDark = false
    render(
      <ThemeModeProvider>
        <ConsumerComponent />
      </ThemeModeProvider>,
    )

    expect(screen.getByTestId('mode').textContent).toBe('system')
    expect(screen.getByTestId('isDark').textContent).toBe('light-active')
  })

  it('初始存储为 dark 时，模式为 dark 且 isDark 为 true', () => {
    localStorage.setItem('novellab.theme-mode', 'dark')
    render(
      <ThemeModeProvider>
        <ConsumerComponent />
      </ThemeModeProvider>,
    )

    expect(screen.getByTestId('mode').textContent).toBe('dark')
    expect(screen.getByTestId('isDark').textContent).toBe('dark-active')
  })

  it('初始存储为 light 时，模式为 light 且 isDark 为 false', () => {
    localStorage.setItem('novellab.theme-mode', 'light')
    render(
      <ThemeModeProvider>
        <ConsumerComponent />
      </ThemeModeProvider>,
    )

    expect(screen.getByTestId('mode').textContent).toBe('light')
    expect(screen.getByTestId('isDark').textContent).toBe('light-active')
  })

  it('存储包含无效值时优雅降级为 system', () => {
    localStorage.setItem('novellab.theme-mode', 'invalid-theme-value')
    render(
      <ThemeModeProvider>
        <ConsumerComponent />
      </ThemeModeProvider>,
    )

    expect(screen.getByTestId('mode').textContent).toBe('system')
  })

  it('通过 setMode 切换模式并同步持久化至 localStorage', () => {
    render(
      <ThemeModeProvider>
        <ConsumerComponent />
      </ThemeModeProvider>,
    )

    expect(screen.getByTestId('mode').textContent).toBe('system')

    // 切换到 dark
    fireEvent.click(screen.getByText('Set Dark'))
    expect(screen.getByTestId('mode').textContent).toBe('dark')
    expect(screen.getByTestId('isDark').textContent).toBe('dark-active')
    expect(localStorage.getItem('novellab.theme-mode')).toBe('dark')

    // 切换到 light
    fireEvent.click(screen.getByText('Set Light'))
    expect(screen.getByTestId('mode').textContent).toBe('light')
    expect(screen.getByTestId('isDark').textContent).toBe('light-active')
    expect(localStorage.getItem('novellab.theme-mode')).toBe('light')

    // 切换回 system
    fireEvent.click(screen.getByText('Set System'))
    expect(screen.getByTestId('mode').textContent).toBe('system')
    expect(localStorage.getItem('novellab.theme-mode')).toBe('system')
  })

  it('在 system 模式下响应系统偏好 MediaQueryList 的动态变更', () => {
    matchesDark = false
    render(
      <ThemeModeProvider>
        <ConsumerComponent />
      </ThemeModeProvider>,
    )

    expect(screen.getByTestId('mode').textContent).toBe('system')
    expect(screen.getByTestId('isDark').textContent).toBe('light-active')

    // 模拟系统由浅色切换为深色
    act(() => {
      mediaListeners.forEach((listener) => {
        listener({ matches: true } as MediaQueryListEvent)
      })
    })

    expect(screen.getByTestId('isDark').textContent).toBe('dark-active')

    // 模拟系统由深色切换回浅色
    act(() => {
      mediaListeners.forEach((listener) => {
        listener({ matches: false } as MediaQueryListEvent)
      })
    })

    expect(screen.getByTestId('isDark').textContent).toBe('light-active')
  })
})
