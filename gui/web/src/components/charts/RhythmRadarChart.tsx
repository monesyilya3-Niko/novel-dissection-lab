// 爽点节奏雷达图（Pacing & Climax Radar Chart）
import { useMemo } from 'react'
import BaseChart from './BaseChart'
import { useThemeMode } from '../../state/ThemeModeContext'
import { useI18n } from '../../state/I18nContext'
import { ink } from '../../ink'

export interface RhythmRadarChartProps {
  metrics?: {
    shuangdianPacing: number // 爽点节奏
    faceSlapAnticipation: number // 打脸期待
    infoDensity: number // 信息密度
    goldenFingerEvolution: number // 金手指展开
    hookRetention: number // 钩子留存
    conflictEscalation: number // 冲突升级
  }
  height?: number
  ariaLabel?: string
}

const DEFAULT_METRICS = {
  shuangdianPacing: 88,
  faceSlapAnticipation: 82,
  infoDensity: 74,
  goldenFingerEvolution: 90,
  hookRetention: 85,
  conflictEscalation: 79,
}

export default function RhythmRadarChart({
  metrics = DEFAULT_METRICS,
  height = 260,
  ariaLabel,
}: RhythmRadarChartProps) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()

  const option = useMemo(() => {
    const indicators = [
      { name: t('chart_rhythm_pacing', '爽点节奏'), max: 100 },
      { name: t('chart_rhythm_faceslap', '打脸期待'), max: 100 },
      { name: t('chart_rhythm_infodensity', '信息密度'), max: 100 },
      { name: t('chart_rhythm_goldenfinger', '金手指展开'), max: 100 },
      { name: t('chart_rhythm_hook', '章末钩子'), max: 100 },
      { name: t('chart_rhythm_conflict', '冲突升级'), max: 100 },
    ]
    const values = [
      metrics.shuangdianPacing,
      metrics.faceSlapAnticipation,
      metrics.infoDensity,
      metrics.goldenFingerEvolution,
      metrics.hookRetention,
      metrics.conflictEscalation,
    ]

    return {
      tooltip: {
        trigger: 'item' as const,
      },
      radar: {
        indicator: indicators,
        radius: '68%',
        splitNumber: 4,
        axisName: {
          color: isDark ? ink.moonSoft : ink.textSecondary,
          fontSize: 11,
          fontWeight: 600,
        },
        splitLine: {
          lineStyle: {
            color: isDark ? 'rgba(255, 255, 255, 0.08)' : 'rgba(0, 0, 0, 0.06)',
          },
        },
        splitArea: {
          show: true,
          areaStyle: {
            color: isDark
              ? ['rgba(255, 255, 255, 0.02)', 'rgba(255, 255, 255, 0.04)']
              : ['rgba(0, 0, 0, 0.01)', 'rgba(0, 0, 0, 0.02)'],
          },
        },
        axisLine: {
          lineStyle: {
            color: isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.08)',
          },
        },
      },
      series: [
        {
          name: t('chart_rhythm_series', '节奏综合评估'),
          type: 'radar' as const,
          data: [
            {
              value: values,
              name: t('chart_rhythm_item_name', '网文爽感指数'),
              itemStyle: { color: '#8B5CF6' },
              lineStyle: { width: 2, color: '#8B5CF6' },
              areaStyle: {
                color: 'rgba(139, 92, 246, 0.35)',
              },
            },
          ],
        },
      ],
    }
  }, [metrics, isDark, t])

  return <BaseChart option={option} height={height} ariaLabel={ariaLabel ?? t('chart_rhythm_aria', '爽点节奏雷达图')} />
}
