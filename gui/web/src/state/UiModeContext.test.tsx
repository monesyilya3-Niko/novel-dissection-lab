import { render, screen, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { UiModeProvider, useUiMode } from './UiModeContext'
import { removeStorage, readStorage } from '../safeStorage'

vi.mock('../api/client', () => ({
  systemApi: { updateSettings: vi.fn().mockResolvedValue({}) },
}))

function Probe() {
  const { mode, isHydrated } = useUiMode()
  return (
    <div>
      <span data-testid="mode">{mode}</span>
      <span data-testid="hydrated">{String(isHydrated)}</span>
    </div>
  )
}

const KEY = 'novellab.ui.mode'

describe('UiModeContext 简洁/进阶模式', () => {
  beforeEach(() => {
    removeStorage(KEY)
  })

  it('无存储时跟随 defaultMode（新手 → simple）', () => {
    render(
      <UiModeProvider defaultMode="simple">
        <Probe />
      </UiModeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('simple')
  })

  it('推断出的默认值不得写进 localStorage（用户的显式偏好才算数）', () => {
    render(
      <UiModeProvider defaultMode="simple">
        <Probe />
      </UiModeProvider>,
    )
    // 关键回归：早期实现会在 effect 里 writeStorage(KEY, defaultMode)，
    // 导致新手被永久钉在 simple —— 后来有了书也回不到 advanced。
    expect(readStorage(KEY)).toBeNull()
  })

  it('overview 就绪后 defaultMode 变化时跟随（从 undefined 到 advanced）', () => {
    const { rerender } = render(
      <UiModeProvider>
        <Probe />
      </UiModeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('simple') // 兜底

    rerender(
      <UiModeProvider defaultMode="advanced">
        <Probe />
      </UiModeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('advanced')
    // 跟随推断值同样不应落盘
    expect(readStorage(KEY)).toBeNull()
  })

  it('已有存储偏好优先于 defaultMode', () => {
    localStorage.setItem(KEY, 'advanced')
    render(
      <UiModeProvider defaultMode="simple">
        <Probe />
      </UiModeProvider>,
    )
    expect(screen.getByTestId('mode')).toHaveTextContent('advanced')
  })

  it('setMode 显式切换会持久化（这才算用户偏好）', async () => {
    // 通过按钮触发，避免在渲染期给外部变量赋值（React 纯函数规则）。
    function SwitchButton() {
      const { setMode } = useUiMode()
      return (
        <button type="button" onClick={() => setMode('advanced')}>
          switch
        </button>
      )
    }
    render(
      <UiModeProvider defaultMode="simple">
        <SwitchButton />
      </UiModeProvider>,
    )
    await act(async () => {
      screen.getByRole('button', { name: 'switch' }).click()
    })
    expect(readStorage(KEY)).toBe('advanced')
  })
})
