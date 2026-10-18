import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import EmotionWaveChart from './EmotionWaveChart'
import RhythmRadarChart from './RhythmRadarChart'
import CreationRateChart from './CreationRateChart'
import BarChart from './BarChart'
import PieChart from './PieChart'
import RadarChart from './RadarChart'
import GaugeChart from './GaugeChart'
import { I18nProvider } from '../../state/I18nContext'

vi.mock('./BaseChart', () => ({
  default: ({ option, ariaLabel }: { option: any; ariaLabel?: string }) => (
    <div data-testid="base-chart" aria-label={ariaLabel} data-option={JSON.stringify(option)} />
  ),
}))

describe('Specialized Narrative Analytics Charts & Base Charts i18n', () => {
  describe('EmotionWaveChart', () => {
    it('在 zh-CN 环境下使用默认情绪张力系列与11个标准节拍', () => {
      render(
        <I18nProvider initialLocale="zh-CN">
          <EmotionWaveChart />
        </I18nProvider>
      )

      const chart = screen.getByTestId('base-chart')
      expect(chart).toHaveAttribute('aria-label', '情绪起伏波形图')
      const option = JSON.parse(chart.getAttribute('data-option') || '{}')
      expect(option.series[0].name).toBe('情绪张力')
      expect(option.xAxis.data).toEqual([
        '开端', '伏笔', '微冲突', '试探', '积蓄', '爆发', '高潮', '喘息', '反扑', '决胜', '留白',
      ])
      expect(option.series[0].markLine.data[0].name).toBe('高潮警戒线')
      expect(option.series[0].markLine.data[0].label.formatter).toBe('高潮阈值 80')
    })

    it('在 en-US 环境下包含标杆基准曲线时正确国际化', () => {
      render(
        <I18nProvider initialLocale="en-US">
          <EmotionWaveChart benchmarkPoints={[40, 50, 60]} />
        </I18nProvider>
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

  describe('RhythmRadarChart', () => {
    it('在 zh-CN 环境下渲染六维网文节奏指标与系列名', () => {
      render(
        <I18nProvider initialLocale="zh-CN">
          <RhythmRadarChart />
        </I18nProvider>
      )

      const chart = screen.getByTestId('base-chart')
      expect(chart).toHaveAttribute('aria-label', '爽点节奏雷达图')
      const option = JSON.parse(chart.getAttribute('data-option') || '{}')
      expect(option.radar.indicator.map((i: any) => i.name)).toEqual([
        '爽点节奏', '打脸期待', '信息密度', '金手指展开', '章末钩子', '冲突升级',
      ])
      expect(option.series[0].name).toBe('节奏综合评估')
      expect(option.series[0].data[0].name).toBe('网文爽感指数')
    })

    it('在 en-US 环境下正确渲染英文雷达指标', () => {
      render(
        <I18nProvider initialLocale="en-US">
          <RhythmRadarChart />
        </I18nProvider>
      )

      const chart = screen.getByTestId('base-chart')
      expect(chart).toHaveAttribute('aria-label', 'Pacing & Climax Radar Chart')
      const option = JSON.parse(chart.getAttribute('data-option') || '{}')
      expect(option.radar.indicator.map((i: any) => i.name)).toEqual([
        'Pacing & Reward', 'Anticipation', 'Information Density', 'Core System', 'Chapter Cliffhanger', 'Conflict Escalation',
      ])
      expect(option.series[0].name).toBe('Rhythm Evaluation')
      expect(option.series[0].data[0].name).toBe('Catharsis Index')
    })
  })

  describe('CreationRateChart', () => {
    const mockData = [
      { date: '2026-10-01', words: 3000 },
      { date: '2026-10-02', words: 4500 },
    ]

    it('在 zh-CN 环境下渲染每日字数与平滑速率系列', () => {
      render(
        <I18nProvider initialLocale="zh-CN">
          <CreationRateChart data={mockData} />
        </I18nProvider>
      )

      const chart = screen.getByTestId('base-chart')
      expect(chart).toHaveAttribute('aria-label', '创作速率与字数统计折线图')
      const option = JSON.parse(chart.getAttribute('data-option') || '{}')
      expect(option.legend.data).toEqual(['每日字数', '平滑速率'])
      expect(option.yAxis[0].name).toBe('字数')
      expect(option.series[0].name).toBe('每日字数')
      expect(option.series[1].name).toBe('平滑速率')
    })

    it('在 en-US 环境下正确国际化图例与坐标轴', () => {
      render(
        <I18nProvider initialLocale="en-US">
          <CreationRateChart data={mockData} />
        </I18nProvider>
      )

      const chart = screen.getByTestId('base-chart')
      expect(chart).toHaveAttribute('aria-label', 'Creation Rate & Word Count Line Chart')
      const option = JSON.parse(chart.getAttribute('data-option') || '{}')
      expect(option.legend.data).toEqual(['Daily Words', 'Smoothed Velocity'])
      expect(option.yAxis[0].name).toBe('Words')
      expect(option.series[0].name).toBe('Daily Words')
      expect(option.series[1].name).toBe('Smoothed Velocity')
    })
  })

  describe('基础通用图表默认 aria-label 双语支持', () => {
    it('BarChart, PieChart, RadarChart, GaugeChart 默认英文 aria-label', () => {
      render(
        <I18nProvider initialLocale="en-US">
          <BarChart categories={['Ch1']} series={[{ name: 's1', data: [10] }]} />
          <PieChart data={[{ name: 'p1', value: 10 }]} />
          <RadarChart indicators={[{ name: 'ind', max: 100 }]} series={[{ name: 'r1', value: [50] }]} />
          <GaugeChart value={85} />
        </I18nProvider>
      )

      const charts = screen.getAllByTestId('base-chart')
      expect(charts[0]).toHaveAttribute('aria-label', 'Bar Chart')
      expect(charts[1]).toHaveAttribute('aria-label', 'Pie Chart')
      expect(charts[2]).toHaveAttribute('aria-label', 'Radar Chart')
      expect(charts[3]).toHaveAttribute('aria-label', 'Gauge Chart')
    })

    it('BarChart, PieChart, RadarChart, GaugeChart 默认中文 aria-label', () => {
      render(
        <I18nProvider initialLocale="zh-CN">
          <BarChart categories={['Ch1']} series={[{ name: 's1', data: [10] }]} />
          <PieChart data={[{ name: 'p1', value: 10 }]} />
          <RadarChart indicators={[{ name: 'ind', max: 100 }]} series={[{ name: 'r1', value: [50] }]} />
          <GaugeChart value={85} />
        </I18nProvider>
      )

      const charts = screen.getAllByTestId('base-chart')
      expect(charts[0]).toHaveAttribute('aria-label', '柱状图')
      expect(charts[1]).toHaveAttribute('aria-label', '饼图')
      expect(charts[2]).toHaveAttribute('aria-label', '雷达图')
      expect(charts[3]).toHaveAttribute('aria-label', '仪表盘')
    })
  })
})
