import { render, screen, act } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import WorkbenchTransition from './WorkbenchTransition'

describe('WorkbenchTransition 工作台切流动效容器', () => {
  let rafCallbacks: FrameRequestCallback[] = []
  let rafIdCounter = 0

  beforeEach(() => {
    rafCallbacks = []
    rafIdCounter = 0

    vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb: FrameRequestCallback) => {
      const id = ++rafIdCounter
      rafCallbacks.push(cb)
      return id
    })

    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation(() => {
      // noop
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('渲染子节点内容', () => {
    render(
      <WorkbenchTransition>
        <div data-testid="child-content">写作工作台内容</div>
      </WorkbenchTransition>,
    )

    expect(screen.getByTestId('child-content')).toBeInTheDocument()
    expect(screen.getByText('写作工作台内容')).toBeInTheDocument()
  })

  it('在初始挂载时启动 requestAnimationFrame 并在回调后激活可见态', () => {
    const { container } = render(
      <WorkbenchTransition>
        <div>过渡内容</div>
      </WorkbenchTransition>,
    )

    const wrapper = container.firstChild as HTMLElement
    expect(wrapper).toBeInTheDocument()
    expect(window.requestAnimationFrame).toHaveBeenCalledTimes(1)

    // 执行 RAF 回调
    act(() => {
      rafCallbacks.forEach((cb) => cb(performance.now()))
    })

    // 激活后依然正常展示子元素
    expect(screen.getByText('过渡内容')).toBeInTheDocument()
  })

  it('在卸载时调用 cancelAnimationFrame 避免内存泄漏', () => {
    const { unmount } = render(
      <WorkbenchTransition>
        <div>卸载测试</div>
      </WorkbenchTransition>,
    )

    expect(window.requestAnimationFrame).toHaveBeenCalled()
    unmount()
    expect(window.cancelAnimationFrame).toHaveBeenCalledWith(1)
  })
})
