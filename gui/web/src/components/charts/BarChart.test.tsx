import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import BarChart from './BarChart'
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

describe('BarChart 柱状图/条形图组件', () => {
  const sampleCategories = ['第1章', '第2章', '第3章']
  const sampleSeries = [
    { name: '一致性', data: [85, 90, 88] },
    { name: '质量', data: [78, 82, 80] },
  ]

  it('默认垂直柱状图配置：渲染类目轴为 xAxis，数值轴为 yAxis，不带 stack', () => {
    render(<BarChart categories={sampleCategories} series={sampleSeries} />)

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '柱状图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.xAxis.type).toBe('category')
    expect(option.xAxis.data).toEqual(sampleCategories)
    expect(option.xAxis.axisLabel.rotate).toBe(0)

    expect(option.yAxis.type).toBe('value')
    expect(option.series.length).toBe(2)
    expect(option.series[0].stack).toBeUndefined()
    expect(option.legend).toBeUndefined()
  })

  it('堆叠模式（stacked=true）：series 标记 stack 为 total 并启用图例 legend', () => {
    render(<BarChart categories={sampleCategories} series={sampleSeries} stacked={true} />)

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.series[0].stack).toBe('total')
    expect(option.series[1].stack).toBe('total')
    expect(option.legend).toBeDefined()
    expect(option.legend.data).toEqual(['一致性', '质量'])
  })

  it('横向条形图模式（horizontal=true）：xAxis 为数值轴，yAxis 为类目轴', () => {
    render(<BarChart categories={sampleCategories} series={sampleSeries} horizontal={true} />)

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.xAxis.type).toBe('value')
    expect(option.yAxis.type).toBe('category')
    expect(option.yAxis.data).toEqual(sampleCategories)
  })

  it('当类目数大于 8 时横轴标签自动倾斜 30 度防重叠', () => {
    const nineCategories = Array.from({ length: 9 }).map((_, i) => `Ch.${i + 1}`)
    render(<BarChart categories={nineCategories} series={[{ name: 's1', data: Array(9).fill(10) }]} />)

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.xAxis.axisLabel.rotate).toBe(30)
  })

  it('支持系列专属颜色配置与 optionOverride 深度覆盖', () => {
    const customSeries = [
      { name: '自定义色', data: [100], color: '#ff0055' },
    ]
    render(
      <BarChart
        categories={['单章']}
        series={customSeries}
        height={400}
        optionOverride={{ title: { text: '章节对比' } } as any}
      />,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '400')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.series[0].itemStyle.color).toBe('#ff0055')
    expect(option.title.text).toBe('章节对比')
  })

  it('支持自定义 ariaLabel 与 en-US 语言环境下的默认双语标签', () => {
    const { rerender } = render(
      <I18nProvider initialLocale="en-US">
        <BarChart categories={sampleCategories} series={sampleSeries} />
      </I18nProvider>,
    )

    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Bar Chart')

    // 显式传入 ariaLabel 优先
    rerender(
      <I18nProvider initialLocale="en-US">
        <BarChart categories={sampleCategories} series={sampleSeries} ariaLabel="Custom Score Bar" />
      </I18nProvider>,
    )
    expect(screen.getByTestId('base-chart')).toHaveAttribute('aria-label', 'Custom Score Bar')
  })
})
