import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import GaugeChart from './GaugeChart'
import { I18nProvider } from '../../state/I18nContext'

vi.mock('./BaseChart', () => ({
  default: ({ option, height, ariaLabel }: { option: any; height?: number; ariaLabel?: string }) => (
    <div
      data-testid="base-chart"
      data-height={height}
      aria-label={ariaLabel}
      data-option={JSON.stringify(option)}
    />
  ),
}))

describe('GaugeChart 仪表盘/进度环组件', () => {
  it('渲染单值进度仪表盘与数值配置', () => {
    render(<GaugeChart value={85} />)

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '仪表盘')
    expect(chart).toHaveAttribute('data-height', '240')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    const series = option.series[0]
    expect(series.type).toBe('gauge')
    expect(series.min).toBe(0)
    expect(series.max).toBe(100)
    expect(series.startAngle).toBe(210)
    expect(series.endAngle).toBe(-30)
    expect(series.pointer.show).toBe(false)
    expect(series.data[0].value).toBe(85)
    expect(series.title).toBeUndefined()
  })

  it('支持自定义最大值、标题与单位后缀', () => {
    render(<GaugeChart value={92} max={120} title="综合质量" unit="分" />)

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    const series = option.series[0]
    expect(series.max).toBe(120)
    expect(series.data[0].name).toBe('综合质量')
    expect(series.title.offsetCenter).toEqual([0, '75%'])
  })

  it('支持自定义高度与 optionOverride 深度覆盖', () => {
    render(
      <GaugeChart
        value={60}
        height={300}
        optionOverride={{ series: [{ splitNumber: 5 }] } as any}
      />,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '300')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.series[0].splitNumber).toBe(5)
  })

  it('支持自定义 ariaLabel 与 en-US 语言环境下的默认双语标签', () => {
    const { rerender } = render(
      <I18nProvider initialLocale="en-US">
        <GaugeChart value={90} />
      </I18nProvider>,
    )

    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Gauge Chart')

    rerender(
      <I18nProvider initialLocale="en-US">
        <GaugeChart value={90} ariaLabel="Custom Gauge Score" />
      </I18nProvider>,
    )
    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Custom Gauge Score')
  })
})
