import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import BaseChart from './BaseChart'
import * as echarts from 'echarts/core'

const mockSetOption = vi.fn()
const mockDispose = vi.fn()
const mockResize = vi.fn()
const mockShowLoading = vi.fn()
const mockHideLoading = vi.fn()

vi.mock('echarts/core', () => ({
  use: vi.fn(),
  init: vi.fn(() => ({
    setOption: mockSetOption,
    dispose: mockDispose,
    resize: mockResize,
    showLoading: mockShowLoading,
    hideLoading: mockHideLoading,
  })),
}))

const mockObserve = vi.fn()
const mockDisconnect = vi.fn()

class MockResizeObserver {
  observe = mockObserve
  unobserve = vi.fn()
  disconnect = mockDisconnect
}

describe('BaseChart ECharts 统一基础组件', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver
  })

  it('渲染无障碍容器并初始化 ECharts 实例', () => {
    render(
      <BaseChart
        option={{ series: [{ type: 'bar', data: [1, 2, 3] }] }}
        height={320}
        ariaLabel="测试柱状图"
      />,
    )

    const container = screen.getByRole('img', { name: '测试柱状图' })
    expect(container).toBeInTheDocument()
    expect(container).toHaveStyle({ height: '320px', width: '100%' })

    expect(echarts.init).toHaveBeenCalledWith(
      container,
      undefined,
      expect.objectContaining({ renderer: 'canvas', locale: 'ZH' }),
    )
    expect(mockSetOption).toHaveBeenCalledWith(
      expect.objectContaining({
        series: [{ type: 'bar', data: [1, 2, 3] }],
        color: expect.any(Array),
        textStyle: expect.any(Object),
      }),
      true,
    )
  })

  it('响应 loading 属性展示与隐藏加载动画', () => {
    const { rerender } = render(
      <BaseChart
        option={{ series: [] }}
        loading={true}
      />,
    )

    expect(mockShowLoading).toHaveBeenCalledTimes(1)
    expect(mockHideLoading).not.toHaveBeenCalled()

    rerender(
      <BaseChart
        option={{ series: [] }}
        loading={false}
      />,
    )

    expect(mockHideLoading).toHaveBeenCalledTimes(1)
  })

  it('挂载 ResizeObserver 监听容器尺寸，卸载时注销并释放 ECharts 实例', () => {
    const { unmount } = render(
      <BaseChart
        option={{ series: [] }}
        disableResize={false}
      />,
    )

    expect(mockObserve).toHaveBeenCalled()

    unmount()

    expect(mockDisconnect).toHaveBeenCalled()
    expect(mockDispose).toHaveBeenCalledTimes(1)
  })

  it('当 disableResize 为 true 时不注册 ResizeObserver', () => {
    render(
      <BaseChart
        option={{ series: [] }}
        disableResize={true}
      />,
    )

    expect(mockObserve).not.toHaveBeenCalled()
  })
})
