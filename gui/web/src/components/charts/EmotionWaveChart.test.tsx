import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EmotionWaveChart from './EmotionWaveChart'
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

describe('EmotionWaveChart 情绪起伏波形图组件', () => {
  it('默认模式下渲染11个标准节拍、情绪张力单曲线与高潮警戒线', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <EmotionWaveChart showDemo />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', '情绪起伏波形图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.legend.show).toBe(false)
    expect(option.xAxis.data).toEqual([
      '开端', '伏笔', '微冲突', '试探', '积蓄', '爆发', '高潮', '喘息', '反扑', '决胜', '留白',
    ])

    const mainSeries = option.series[0]
    expect(mainSeries.name).toBe('情绪张力')
    expect(mainSeries.data).toHaveLength(11)
    expect(mainSeries.itemStyle.color).toBe('#E11D48')
    expect(mainSeries.markLine.data[0].yAxis).toBe(80)
    expect(mainSeries.markLine.data[0].label.formatter).toBe('高潮阈值 80')
  })

  it('支持双曲线神作标杆基准比对模式并显式展示图例', () => {
    const benchmark = [35, 50, 45, 60, 70, 80, 95, 65, 85, 90, 55]
    render(
      <I18nProvider initialLocale="zh-CN">
        <EmotionWaveChart
          tensionPoints={[20, 30, 40]}
          benchmarkPoints={benchmark}
          benchmarkName="《诡秘之主》标杆基准"
        />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.legend.show).toBe(true)
    expect(option.series).toHaveLength(2)

    // 系列 0：当前章节
    expect(option.series[0].name).toBe('当前章节')
    expect(option.series[0].data).toEqual([20, 30, 40])

    // 系列 1：神作标杆曲线
    expect(option.series[1].name).toBe('《诡秘之主》标杆基准')
    expect(option.series[1].data).toEqual(benchmark)
    expect(option.series[1].symbol).toBe('diamond')
    expect(option.series[1].lineStyle.type).toBe('dashed')
  })

  it('支持传入自定义节拍标签、自定义高度与无障碍标签', () => {
    const customLabels = ['起', '承', '转', '合']
    render(
      <I18nProvider initialLocale="zh-CN">
        <EmotionWaveChart
          tensionPoints={[20, 50, 80, 40]}
          labels={customLabels}
          height={320}
          ariaLabel="自定义张力波形图"
        />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('data-height', '320')
    expect(chart).toHaveAttribute('aria-label', '自定义张力波形图')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')
    expect(option.xAxis.data).toEqual(customLabels)
  })

  it('在 en-US 环境下全量翻译标准节拍、图例与警戒线标签', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <EmotionWaveChart showDemo benchmarkPoints={[40, 60, 80]} />
      </I18nProvider>,
    )

    const chart = screen.getByTestId('base-chart')
    expect(chart).toHaveAttribute('aria-label', 'Emotional Tension Wave Chart')
    const option = JSON.parse(chart.getAttribute('data-option') || '{}')

    expect(option.series[0].name).toBe('Current Chapter')
    expect(option.series[1].name).toBe('Masterpiece Benchmark')
    expect(option.xAxis.data).toEqual([
      'Opening', 'Foreshadowing', 'Micro-conflict', 'Testing', 'Buildup', 'Outburst', 'Climax', 'Breather', 'Counterattack', 'Resolution', 'Afterglow',
    ])
    expect(option.series[0].markLine.data[0].name).toBe('Climax Warning Line')
    expect(option.series[0].markLine.data[0].label.formatter).toBe('Climax Threshold 80')
  })
})
