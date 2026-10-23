import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import PieChart from './PieChart'
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

describe('PieChart 饼图与环形图组件', () => {
  const sampleData = [
    { name: '声线卡', value: 12 },
    { name: '笔法卡', value: 8 },
    { name: '蒸馏规则', value: 5 },
  ]

  it('默认环形图模式（donut=true）：设置内外半径区间与切片圆角', () => {
    render(<PieChart data={sampleData} />)

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '饼图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    const series = option.series[0]
    expect(series.type).toBe('pie')
    expect(series.radius).toEqual(['42%', '68%'])
    expect(series.center).toEqual(['50%', '46%'])
    expect(series.itemStyle.borderRadius).toBe(6)
    expect(series.data).toEqual(sampleData)
  })

  it('传统全饼图模式（donut=false）：radius 设置为单一半径 70%', () => {
    render(<PieChart data={sampleData} donut={false} />)

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.series[0].radius).toBe('70%')
  })

  it('配置提示框与文本标签百分比格式化模板', () => {
    render(<PieChart data={sampleData} />)

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.tooltip.formatter).toBe('{b}: {c} ({d}%)')
    expect(option.series[0].label.formatter).toBe('{b}\n{d}%')
    expect(option.legend.orient).toBe('horizontal')
    expect(option.legend.bottom).toBe(0)
  })

  it('支持自定义高度与 optionOverride 深度覆盖', () => {
    render(
      <PieChart
        data={sampleData}
        height={360}
        optionOverride={{ title: { text: '资产全景' } } as any}
      />,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '360')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.title.text).toBe('资产全景')
  })

  it('支持自定义 ariaLabel 与 en-US 语言环境下的默认双语标签', () => {
    const { rerender } = render(
      <I18nProvider initialLocale="en-US">
        <PieChart data={sampleData} />
      </I18nProvider>,
    )

    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Pie Chart')

    rerender(
      <I18nProvider initialLocale="en-US">
        <PieChart data={sampleData} ariaLabel="Custom Asset Distribution" />
      </I18nProvider>,
    )
    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Custom Asset Distribution')
  })
})
