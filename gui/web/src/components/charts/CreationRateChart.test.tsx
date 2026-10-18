import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CreationRateChart, { type DailyStatPoint } from './CreationRateChart'
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

describe('CreationRateChart 创作速率与字数统计折线图', () => {
  const sampleData: DailyStatPoint[] = [
    { date: '2026-10-01', words: 1000 },
    { date: '2026-10-02', words: 2000 },
    { date: '2026-10-03', words: 3000 },
    { date: '2026-10-04', words: 4000 },
  ]

  it('截取 MM-DD 日期并计算 3 日移动平滑速率', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <CreationRateChart data={sampleData} />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '创作速率与字数统计折线图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    // 日期截取校验
    expect(option.xAxis.data).toEqual(['10-01', '10-02', '10-03', '10-04'])

    // 每日字数系列
    const wordsSeries = option.series[0]
    expect(wordsSeries.name).toBe('每日字数')
    expect(wordsSeries.data).toEqual([1000, 2000, 3000, 4000])
    expect(wordsSeries.itemStyle.color).toBe('#2563EB')
    expect(wordsSeries.areaStyle).toBeDefined()

    // 移动平均速率系列 (i=0: 1000, i=1: 1500, i=2: 2000, i=3: 3000)
    const rateSeries = option.series[1]
    expect(rateSeries.name).toBe('平滑速率')
    expect(rateSeries.data).toEqual([1000, 1500, 2000, 3000])
    expect(rateSeries.lineStyle.type).toBe('dashed')
  })

  it('支持自定义图表高度与无障碍标签', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <CreationRateChart data={sampleData} height={360} ariaLabel="自定义码字速率图" />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '360')
    expect(chart).toHaveAttribute('aria-label', '自定义码字速率图')
  })

  it('在空数据场景下安全渲染空坐标轴与空序列', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <CreationRateChart data={[]} />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')
    expect(option.xAxis.data).toEqual([])
    expect(option.series[0].data).toEqual([])
    expect(option.series[1].data).toEqual([])
  })

  it('在 en-US 环境下全量国际化图例文案与坐标轴名称', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <CreationRateChart data={sampleData} />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', 'Creation Rate & Word Count Line Chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')
    expect(option.legend.data).toEqual(['Daily Words', 'Smoothed Velocity'])
    expect(option.series[0].name).toBe('Daily Words')
    expect(option.series[1].name).toBe('Smoothed Velocity')
    expect(option.yAxis[0].name).toBe('Words')
  })
})
