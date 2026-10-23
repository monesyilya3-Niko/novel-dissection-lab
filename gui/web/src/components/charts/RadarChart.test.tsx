import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RadarChart from './RadarChart'
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

describe('RadarChart 雷达图组件', () => {
  const sampleIndicators = [
    { name: '爽点节奏', max: 100 },
    { name: '期待感', max: 100 },
    { name: '信息密度', max: 100 },
    { name: '金手指', max: 100 },
    { name: '章末钩子', max: 100 },
  ]
  const sampleSeries = [
    { name: '本书得分', value: [85, 90, 75, 88, 92] },
    { name: '标杆基准', value: [80, 85, 80, 85, 85] },
  ]

  it('渲染雷达图指标与多组对比系列数据', () => {
    render(<RadarChart indicators={sampleIndicators} series={sampleSeries} />)

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '雷达图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.radar.indicator).toEqual(sampleIndicators)
    expect(option.radar.radius).toBe('65%')

    const series = option.series[0]
    expect(series.type).toBe('radar')
    expect(series.data).toEqual(sampleSeries)
    expect(series.areaStyle.opacity).toBe(0.18)
    expect(series.symbol).toBe('circle')

    expect(option.legend.data).toEqual(['本书得分', '标杆基准'])
  })

  it('配置半透明水墨交替背景区域', () => {
    render(<RadarChart indicators={sampleIndicators} series={sampleSeries} />)

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.radar.splitArea.areaStyle.color).toEqual([
      'rgba(37,99,235,0.04)',
      'rgba(37,99,235,0.08)',
    ])
  })

  it('支持自定义高度与 optionOverride 深度覆盖', () => {
    render(
      <RadarChart
        indicators={sampleIndicators}
        series={sampleSeries}
        height={350}
        optionOverride={{ title: { text: '节奏六维图' } } as any}
      />,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '350')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.title.text).toBe('节奏六维图')
  })

  it('支持自定义 ariaLabel 与 en-US 语言环境下的默认双语标签', () => {
    const { rerender } = render(
      <I18nProvider initialLocale="en-US">
        <RadarChart indicators={sampleIndicators} series={sampleSeries} />
      </I18nProvider>,
    )

    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Radar Chart')

    rerender(
      <I18nProvider initialLocale="en-US">
        <RadarChart indicators={sampleIndicators} series={sampleSeries} ariaLabel="Custom Radar" />
      </I18nProvider>,
    )
    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Custom Radar')
  })
})
