import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ReaderRetentionChart from './ReaderRetentionChart'
import { I18nProvider } from '../../state/I18nContext'
import type { DropoffHotspot } from '../../api/client'

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

describe('ReaderRetentionChart 读者留存流失预测图组件', () => {
  it('默认模式下渲染衰减留存曲线与 S/A/及格三条阈值辅助线', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <ReaderRetentionChart />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '商业网文读者留存流失预测图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    const mainSeries = option.series[0]
    expect(mainSeries.name).toBe('读者留存率')
    expect(mainSeries.itemStyle.color).toBe('#0EA5E9')
    expect(mainSeries.data[0]).toBe(100.0)
    expect(mainSeries.markLine.data).toHaveLength(3)
    expect(mainSeries.markLine.data[0].yAxis).toBe(68)
    expect(mainSeries.markLine.data[1].yAxis).toBe(52)
    expect(mainSeries.markLine.data[2].yAxis).toBe(38)
  })

  it('传入自定义分段标签与高危跳出点（Hotspots）时正确打标', () => {
    const mockHotspots: DropoffHotspot[] = [
      {
        chapterIndex: 2,
        segmentIndex: 0,
        segmentLabel: '第2章第1段 (0-10%)',
        riskLevel: 'CRITICAL',
        estimatedDropPct: 12.5,
        reason: '承接前章张力骤降 45 分，引发断崖式失速',
        fixSuggestion: '避免在章首平推大段背景',
      },
    ]

    const customCurve = [100.0, 92.0, 80.0, 75.0]
    const customLabels = ['开局', '第1章', '第2章开头', '第2章高潮']

    render(
      <I18nProvider initialLocale="zh-CN">
        <ReaderRetentionChart
          retentionCurve={customCurve}
          labels={customLabels}
          hotspots={mockHotspots}
          height={300}
        />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '300')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.xAxis.data).toEqual(customLabels)
    const mainSeries = option.series[0]
    expect(mainSeries.data).toEqual(customCurve)
    expect(mainSeries.markPoint.data).toHaveLength(1)
    expect(mainSeries.markPoint.data[0].itemStyle.color).toBe('#E11D48')
  })

  it('英文国际化环境下正确渲染 aria-label', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <ReaderRetentionChart />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label')
  })
})
