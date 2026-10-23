// 情绪起伏波形图（Emotion Tension Wave Chart）
import { useMemo } from 'react'
import BaseChart from './BaseChart'
import { useThemeMode } from '../../state/ThemeModeContext'
import { useI18n } from '../../state/I18nContext'
import { ink } from '../../ink'

export interface EmotionWaveChartProps {
  tensionPoints?: number[] // 0-100 的张力值列表
  benchmarkPoints?: number[] // 可选：神作标杆张力基准曲线（重叠对比）
  benchmarkName?: string
  labels?: string[]
  height?: number
  ariaLabel?: string
}

const DEFAULT_WAVE = [30, 45, 40, 65, 55, 85, 92, 70, 88, 95, 60]

export default function EmotionWaveChart({
  tensionPoints = DEFAULT_WAVE,
  benchmarkPoints,
  benchmarkName,
  labels,
  height = 240,
  ariaLabel,
}: EmotionWaveChartProps) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()

  const resolvedBenchmarkName = benchmarkName ?? t('chart_wave_benchmark_default', '神作标杆基准')

  const effectiveLabels = useMemo(() => {
    if (labels && labels.length > 0) return labels
    return [
      t('chart_wave_lbl_opening', '开端'),
      t('chart_wave_lbl_foreshadow', '伏笔'),
      t('chart_wave_lbl_microconflict', '微冲突'),
      t('chart_wave_lbl_testing', '试探'),
      t('chart_wave_lbl_accumulation', '积蓄'),
      t('chart_wave_lbl_outburst', '爆发'),
      t('chart_wave_lbl_climax', '高潮'),
      t('chart_wave_lbl_breather', '喘息'),
      t('chart_wave_lbl_counterattack', '反扑'),
      t('chart_wave_lbl_resolution', '决胜'),
      t('chart_wave_lbl_linger', '留白'),
    ]
  }, [labels, t])

  const option = useMemo(() => {
    const hasBenchmark = Boolean(benchmarkPoints && benchmarkPoints.length > 0)
    return {
      tooltip: {
        trigger: 'axis' as const,
        formatter: (params: any) => {
          const list = Array.isArray(params) ? params : [params]
          const header = list[0]?.name || ''
          const lines = list.map((p: any) => `${p.marker} ${p.seriesName}: <b>${p.value}</b> / 100`).join('<br/>')
          return `${header}<br/>${lines}`
        },
      },
      legend: {
        show: hasBenchmark,
        top: 0,
        right: 10,
        textStyle: { color: isDark ? ink.moonSoft : ink.textSecondary, fontSize: 11 },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '8%',
        top: hasBenchmark ? '18%' : '12%',
        containLabel: true,
      },
      xAxis: {
        type: 'category' as const,
        boundaryGap: false,
        data: effectiveLabels,
        axisLine: { lineStyle: { color: isDark ? ink.nightLine : ink.hairline } },
        axisLabel: { color: isDark ? ink.moonSoft : ink.textTertiary, fontSize: 11 },
      },
      yAxis: {
        type: 'value' as const,
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' } },
        axisLabel: { color: isDark ? ink.moonSoft : ink.textTertiary, fontSize: 11 },
      },
      series: [
        {
          name: hasBenchmark ? t('chart_wave_series_current', '当前章节') : t('chart_wave_series_tension', '情绪张力'),
          type: 'line' as const,
          smooth: 0.35,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: { color: '#E11D48' },
          lineStyle: { width: 3, color: '#E11D48' },
          areaStyle: {
            color: {
              type: 'linear' as const,
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(225, 29, 72, 0.45)' },
                { offset: 0.7, color: 'rgba(225, 29, 72, 0.12)' },
                { offset: 1, color: 'rgba(225, 29, 72, 0.01)' },
              ],
            },
          },
          markLine: {
            symbol: 'none' as const,
            data: [
              {
                yAxis: 80,
                name: t('chart_wave_mark_climax_line', '高潮警戒线'),
                lineStyle: { color: '#D97706', type: 'dashed' as const },
                label: { formatter: t('chart_wave_mark_climax_thresh', '高潮阈值 80'), position: 'insideEndTop' as const, fontSize: 10 },
              },
            ],
          },
          data: tensionPoints,
        },
        ...(hasBenchmark && benchmarkPoints ? [{
          name: resolvedBenchmarkName,
          type: 'line' as const,
          smooth: 0.35,
          symbol: 'diamond',
          symbolSize: 5,
          itemStyle: { color: '#0284C7' },
          lineStyle: { width: 2, type: 'dashed' as const, color: '#0284C7' },
          data: benchmarkPoints,
        }] : []),
      ],
    }
  }, [tensionPoints, benchmarkPoints, resolvedBenchmarkName, effectiveLabels, isDark, t])

  return <BaseChart option={option} height={height} ariaLabel={ariaLabel ?? t('chart_wave_aria', '情绪起伏波形图')} />
}
