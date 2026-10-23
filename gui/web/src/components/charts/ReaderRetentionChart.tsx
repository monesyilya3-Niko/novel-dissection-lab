// 商业网文读者留存流失预测图（Reader Retention & Churn Curve Chart）
import { useMemo } from 'react'
import BaseChart from './BaseChart'
import { useThemeMode } from '../../state/ThemeModeContext'
import { useI18n } from '../../state/I18nContext'
import { ink } from '../../ink'
import type { DropoffHotspot } from '../../api/client'

export interface ReaderRetentionChartProps {
  retentionCurve?: number[] // 0-100 的读者留存率衰减列表
  labels?: string[]
  hotspots?: DropoffHotspot[]
  height?: number
  ariaLabel?: string
}

const DEFAULT_CURVE = [100.0, 92.5, 88.0, 84.5, 81.0, 78.5, 75.0, 72.0, 68.5, 65.0]

export default function ReaderRetentionChart({
  retentionCurve = DEFAULT_CURVE,
  labels,
  hotspots = [],
  height = 260,
  ariaLabel,
}: ReaderRetentionChartProps) {
  const { isDark } = useThemeMode()
  const { t } = useI18n()

  const effectiveLabels = useMemo(() => {
    if (labels && labels.length > 0) return labels
    return retentionCurve.map((_, idx) => (idx === 0 ? t('chart_retention_start', '开局') : `${t('chart_retention_point', '切片')} ${idx}`))
  }, [labels, retentionCurve, t])

  const hotspotMap = useMemo(() => {
    const map = new Map<number, DropoffHotspot>()
    for (const h of hotspots) {
      // 曲线第 0 点是初始 100%，第 i 个 segment 对应曲线下标 i + 1
      const curveIndex = h.segmentIndex + 1
      map.set(curveIndex, h)
    }
    return map
  }, [hotspots])

  const markPoints = useMemo(() => {
    const pts: any[] = []
    hotspotMap.forEach((h, idx) => {
      if (idx < retentionCurve.length) {
        const isCritical = h.riskLevel === 'CRITICAL'
        pts.push({
          coord: [idx, retentionCurve[idx]],
          value: isCritical ? `-${h.estimatedDropPct}%` : `-${h.estimatedDropPct}%`,
          itemStyle: {
            color: isCritical ? '#E11D48' : '#F59E0B',
          },
          tooltip: {
            formatter: () => `${h.segmentLabel}<br/><b>${h.riskLevel}</b>: 预估跳出 ${h.estimatedDropPct}%<br/>原因: ${h.reason}`,
          },
        })
      }
    })
    return pts
  }, [hotspotMap, retentionCurve])

  const option = useMemo(() => {
    return {
      tooltip: {
        trigger: 'axis' as const,
        formatter: (params: any) => {
          const list = Array.isArray(params) ? params : [params]
          const p = list[0]
          if (!p) return ''
          const dataIdx = p.dataIndex
          const val = Number(p.value ?? 0).toFixed(1)
          const churn = (100.0 - Number(val)).toFixed(1)
          let tip = `<b>${p.name}</b><br/>${p.marker} ${t('chart_retention_rate', '读者留存率')}: <b>${val}%</b> (累计流失 ${churn}%)`
          const hs = hotspotMap.get(dataIdx)
          if (hs) {
            tip += `<br/><span style="color:${hs.riskLevel === 'CRITICAL' ? '#E11D48' : '#F59E0B'};font-weight:600;">[${hs.riskLevel}] ${hs.reason}</span>`
          }
          return tip
        },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '8%',
        top: '12%',
        containLabel: true,
      },
      xAxis: {
        type: 'category' as const,
        boundaryGap: false,
        data: effectiveLabels,
        axisLine: { lineStyle: { color: isDark ? ink.nightLine : ink.hairline } },
        axisLabel: {
          color: isDark ? ink.moonSoft : ink.textTertiary,
          fontSize: 11,
          interval: effectiveLabels.length > 20 ? Math.floor(effectiveLabels.length / 10) : 0,
        },
      },
      yAxis: {
        type: 'value' as const,
        min: 0,
        max: 100,
        splitLine: { lineStyle: { color: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' } },
        axisLabel: {
          color: isDark ? ink.moonSoft : ink.textTertiary,
          fontSize: 11,
          formatter: '{value}%',
        },
      },
      series: [
        {
          name: t('chart_retention_rate', '读者留存率'),
          type: 'line' as const,
          smooth: 0.35,
          symbol: 'circle',
          symbolSize: 6,
          itemStyle: { color: '#0EA5E9' },
          lineStyle: { width: 3, color: '#0EA5E9' },
          areaStyle: {
            color: {
              type: 'linear' as const,
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: 'rgba(14, 165, 233, 0.35)' },
                { offset: 0.7, color: 'rgba(14, 165, 233, 0.08)' },
                { offset: 1, color: 'rgba(14, 165, 233, 0.0)' },
              ],
            },
          },
          markLine: {
            silent: true,
            symbol: 'none',
            data: [
              {
                yAxis: 68,
                lineStyle: { type: 'dashed' as const, color: '#10B981', width: 1.5 },
                label: { formatter: 'S级线 (68%)', position: 'insideEndTop' as const, color: '#10B981', fontSize: 10 },
              },
              {
                yAxis: 52,
                lineStyle: { type: 'dashed' as const, color: '#0EA5E9', width: 1.5 },
                label: { formatter: 'A级线 (52%)', position: 'insideEndTop' as const, color: '#0EA5E9', fontSize: 10 },
              },
              {
                yAxis: 38,
                lineStyle: { type: 'dashed' as const, color: '#F59E0B', width: 1.5 },
                label: { formatter: '及格线 (38%)', position: 'insideEndTop' as const, color: '#F59E0B', fontSize: 10 },
              },
            ],
          },
          markPoint: {
            data: markPoints,
          },
          data: retentionCurve,
        },
      ],
    }
  }, [effectiveLabels, hotspotMap, isDark, markPoints, retentionCurve, t])

  return (
    <BaseChart
      option={option}
      height={height}
      ariaLabel={ariaLabel ?? t('chart_retention_aria', '商业网文读者留存流失预测图')}
    />
  )
}
