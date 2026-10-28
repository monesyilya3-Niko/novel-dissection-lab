// 创作速率与字数统计折线图（ECharts 封装）
import { useMemo } from 'react'
import BaseChart from './BaseChart'
import { useThemeMode } from '../../state/ThemeModeContext'
import { useI18n } from '../../state/I18nContext'
import { ink } from '../../ink'

export interface DailyStatPoint {
  date: string
  words: number
  chapters?: number
}

export interface CreationRateChartProps {
  data: DailyStatPoint[]
  height?: number
  ariaLabel?: string
}

function formatDateLabel(raw: string): string {
  // Handle YYYY-MM-DD, YYYY/MM/DD, ISO timestamps, or pre-sliced MM-DD
  // Extract YYYY/M/D or MM/D by matching date-like prefix
  const trimmed = raw.trim()
  if (!trimmed) return trimmed
  // ISO-ish: YYYY-MM-DD or YYYY/MM/DD (optionally followed by T/space + time)
  const m = trimmed.match(/^(\d{4})[/-](\d{1,2})[/-](\d{1,2})/)
  if (m) return `${m[2].padStart(2, '0')}-${m[3].padStart(2, '0')}`
  // Already MM-DD or DD-like short label
  return trimmed
}

export default function CreationRateChart({ data, height = 260, ariaLabel }: CreationRateChartProps) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()

  const aria = ariaLabel ?? t('chart_rate_aria', '创作速率与字数统计折线图')
  const isEmpty = !data || data.length === 0

  const option = useMemo(() => {
    if (isEmpty) return null
    const dates = data.map((d) => formatDateLabel(d.date))
    const words = data.map((d) => d.words)
    // 计算移动速率（字/天平滑）
    const rates = words.map((_, i, arr) => {
      const slice = arr.slice(Math.max(0, i - 2), i + 1)
      const avg = slice.reduce((a, b) => a + b, 0) / slice.length
      return Math.round(avg)
    })

    const dailyWordsLabel = t('chart_rate_daily_words', '每日字数')
    const velocityLabel = t('chart_rate_velocity', '平滑速率')

    return {
      tooltip: {
        trigger: 'axis' as const,
        axisPointer: { type: 'cross' as const },
      },
      legend: {
        data: [dailyWordsLabel, velocityLabel],
        top: 0,
        textStyle: { color: isDark ? ink.moonSoft : ink.textSecondary },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '8%',
        top: '16%',
        containLabel: true,
      },
      xAxis: {
        type: 'category' as const,
        data: dates,
        axisLine: { lineStyle: { color: isDark ? ink.nightLine : ink.hairline } },
        axisLabel: { color: isDark ? ink.moonSoft : ink.textTertiary, fontSize: 11 },
      },
      yAxis: [
        {
          type: 'value' as const,
          name: t('chart_rate_y_words', '字数'),
          splitLine: { lineStyle: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' } },
          axisLabel: { color: isDark ? ink.moonSoft : ink.textTertiary, fontSize: 11 },
        },
      ],
      series: [
        {
          name: dailyWordsLabel,
          type: 'line' as const,
          smooth: true,
          data: words,
          itemStyle: { color: '#2563EB' },
          areaStyle: {
            color: {
              type: 'linear' as const,
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(37, 99, 235, 0.35)' },
                { offset: 1, color: 'rgba(37, 99, 235, 0.02)' },
              ],
            },
          },
        },
        {
          name: velocityLabel,
          type: 'line' as const,
          smooth: true,
          lineStyle: { width: 2, type: 'dashed' as const },
          itemStyle: { color: '#059669' },
          data: rates,
        },
      ],
    }
  }, [data, isDark, t, isEmpty])

  if (isEmpty) {
    return (
      <div
        style={{
          width: '100%',
          height,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: isDark ? ink.moonSoft : ink.textTertiary,
          fontSize: 14,
        }}
        role="img"
        aria-label={aria}
      >
        {t('chart_rate_empty', '暂无数据，请先创作')}
      </div>
    )
  }

  return <BaseChart option={option!} height={height} ariaLabel={aria} />
}
