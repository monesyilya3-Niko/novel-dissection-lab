import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RhythmRadarChart, { DEFAULT_METRICS } from './RhythmRadarChart'
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

describe('RhythmRadarChart 爽点节奏雷达图组件', () => {
  it('无数据时展示空态占位而非假数据', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <RhythmRadarChart />
      </I18nProvider>,
    )

    expect(screen.queryByTestId('base-chart')).toBeNull()
    expect(screen.getByRole('img', { name: '爽点节奏雷达图' })).toHaveTextContent('暂无数据，请先测算')
  })

  it('showDemo/isDemo 展示预设假数据', () => {
    for (const extra of [{ showDemo: true } as any, { isDemo: true } as any]) {
      const { container, unmount } = render(
        <I18nProvider initialLocale="zh-CN">
          <RhythmRadarChart {...extra} />
        </I18nProvider>,
      )

      const chart = container.querySelector('[data-testid="base-chart"]')!
      const option = JSON.parse(chart.getAttribute('data-option') || '{}')
      expect(option.series[0].data[0].value).toEqual([
        DEFAULT_METRICS.shuangdianPacing,
        DEFAULT_METRICS.faceSlapAnticipation,
        DEFAULT_METRICS.infoDensity,
        DEFAULT_METRICS.goldenFingerEvolution,
        DEFAULT_METRICS.hookRetention,
        DEFAULT_METRICS.conflictEscalation,
      ])
      expect(option.radar.indicator).toEqual([
        { name: '爽点节奏', max: 100 },
        { name: '打脸期待', max: 100 },
        { name: '信息密度', max: 100 },
        { name: '金手指展开', max: 100 },
        { name: '章末钩子', max: 100 },
        { name: '冲突升级', max: 100 },
      ])
      expect(option.radar.radius).toBe('68%')
      expect(option.radar.splitNumber).toBe(4)
      expect(option.radar.splitArea.show).toBe(true)
      const series = option.series[0]
      expect(series.name).toBe('节奏综合评估')
      expect(series.data[0].name).toBe('网文爽感指数')
      expect(series.data[0].itemStyle.color).toBe('#8B5CF6')
      unmount()
    }
  })

  it('支持传入自定义六维指标、高度与无障碍标签', () => {
    const customMetrics = {
      shuangdianPacing: 95,
      faceSlapAnticipation: 90,
      infoDensity: 80,
      goldenFingerEvolution: 85,
      hookRetention: 92,
      conflictEscalation: 88,
    }

    render(
      <I18nProvider initialLocale="zh-CN">
        <RhythmRadarChart
          metrics={customMetrics}
          height={300}
          ariaLabel="自定义网文节奏雷达"
        />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '300')
    expect(chart).toHaveAttribute('aria-label', '自定义网文节奏雷达')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')
    expect(option.series[0].data[0].value).toEqual([95, 90, 80, 85, 92, 88])
  })

  it('在 en-US 环境下无数据时空态与有数据时全量国际化', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <RhythmRadarChart />
      </I18nProvider>,
    )
    expect(screen.getByRole('img', { name: 'Pacing & Climax Radar Chart' })).toHaveTextContent('No data yet.')

    render(
      <I18nProvider initialLocale="en-US">
        <RhythmRadarChart showDemo />
      </I18nProvider>,
    )

    const charts = screen.getAllByTestId('base-chart')
    const chart = charts[charts.length - 1]
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.radar.indicator).toEqual([
      { name: 'Pacing & Reward', max: 100 },
      { name: 'Anticipation', max: 100 },
      { name: 'Information Density', max: 100 },
      { name: 'Core System', max: 100 },
      { name: 'Chapter Cliffhanger', max: 100 },
      { name: 'Conflict Escalation', max: 100 },
    ])
    expect(option.series[0].name).toBe('Rhythm Evaluation')
    expect(option.series[0].data[0].name).toBe('Catharsis Index')
  })
})
