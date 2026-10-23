import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import RhythmRadarChart from './RhythmRadarChart'
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
  it('默认模式下渲染预设六维爽感数值与雷达指标', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <RhythmRadarChart />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '爽点节奏雷达图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    // 6 个雷达维度
    expect(option.radar.indicator).toEqual([
      { name: '爽点节奏', max: 100 },
      { name: '打脸期待', max: 100 },
      { name: '信息密度', max: 100 },
      { name: '金手指展开', max: 100 },
      { name: '章末钩子', max: 100 },
      { name: '冲突升级', max: 100 },
    ])

    // 雷达图背景与分割
    expect(option.radar.radius).toBe('68%')
    expect(option.radar.splitNumber).toBe(4)
    expect(option.radar.splitArea.show).toBe(true)

    // 数据序列
    const series = option.series[0]
    expect(series.name).toBe('节奏综合评估')
    expect(series.data[0].name).toBe('网文爽感指数')
    expect(series.data[0].value).toEqual([88, 82, 74, 90, 85, 79])
    expect(series.data[0].itemStyle.color).toBe('#8B5CF6')
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

  it('在 en-US 环境下全量国际化六维指标名称与系列文案', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <RhythmRadarChart />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', 'Pacing & Climax Radar Chart')
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
