import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import QcVisuals from './QcVisuals'
import { I18nProvider } from '../state/I18nContext'
import type { QcLayer, QcIssue } from '../types'

vi.mock('./charts/BaseChart', () => ({
  default: ({ option, ariaLabel }: { option: any; ariaLabel?: string }) => (
    <div data-testid="base-chart" aria-label={ariaLabel} data-option={JSON.stringify(option)} />
  ),
}))

vi.mock('../state/AppContext', () => ({
  useApp: () => ({ qualityPassLine: 75 }),
}))

const mockLayers: QcLayer[] = [
  {
    layer: 'L1',
    label: '格式规范',
    score: 85,
    dimensions: [
      {
        key: 'd1',
        label: '排版',
        layer: 'L1',
        score: 90,
        issues: [],
        raw: {
          perChapter: {
            '1': 10,
            '2': 8,
          },
        },
      },
    ],
  },
  {
    layer: 'L2',
    label: '角色连贯',
    score: 70,
    dimensions: [
      {
        key: 'd2',
        label: '台词指纹',
        layer: 'L2',
        score: 70,
        issues: [],
        raw: {
          perChapter: {
            '1': 6,
            '2': 9,
          },
        },
      },
    ],
  },
]

const mockIssues: QcIssue[] = [
  {
    type: 'voice',
    severity: 'critical',
    chapter: 1,
    detail: 'OOC error',
  },
  {
    type: 'format',
    severity: 'medium',
    chapter: 2,
    detail: 'spacing error',
  },
]

describe('QcVisuals', () => {
  it('当 layers 为空时返回 null', () => {
    const { container } = render(<QcVisuals layers={[]} issues={[]} />)
    expect(container.firstChild).toBeNull()
  })

  it('中文默认环境下完整渲染条形总览、热力图与严重度分布', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <QcVisuals layers={mockLayers} issues={mockIssues} />
      </I18nProvider>
    )

    // 12维得分总览
    expect(screen.getByText(/十二维得分总览（红 = 低于合格线 75）/)).toBeInTheDocument()
    // 章节 × 维度 得分率热力图
    expect(screen.getByText('章节 × 维度 得分率热力图')).toBeInTheDocument()
    expect(screen.getByText(/仅含提供章节粒度的 2 个维度/)).toBeInTheDocument()
    // 章节问题分布
    expect(screen.getByText('章节问题分布（按严重度）')).toBeInTheDocument()

    // 检查 BaseChart 的 aria-label（使用 findAllByTestId 等待 Suspense lazy 加载完成）
    const charts = await screen.findAllByTestId('base-chart')
    expect(charts).toHaveLength(3)
    expect(charts[0]).toHaveAttribute('aria-label', '十二维得分总览条形图')
    expect(charts[1]).toHaveAttribute('aria-label', '章节维度得分率热力图')
    expect(charts[2]).toHaveAttribute('aria-label', '章节问题分布柱状图')

    // 检查热力图的 option 中是否包含中文章节名与 visualMap
    const heatOption = JSON.parse(charts[1].getAttribute('data-option') || '{}')
    expect(heatOption.xAxis.data).toEqual(['第1章', '第2章'])
    expect(heatOption.visualMap.text).toEqual(['得分率高', '低'])

    // 检查问题分布的 option 中是否包含严重度 label
    const issueOption = JSON.parse(charts[2].getAttribute('data-option') || '{}')
    expect(issueOption.legend.data).toEqual(['严重', '高', '中', '低'])
    expect(issueOption.xAxis.data).toEqual(['第1章', '第2章'])
  })

  it('英文 (en-US) 环境下完整渲染英文标题、说明与图表标签', async () => {
    render(
      <I18nProvider initialLocale="en-US">
        <QcVisuals layers={mockLayers} issues={mockIssues} />
      </I18nProvider>
    )

    // 英文标题与描述
    expect(screen.getByText(/12-Dimensional Score Overview \(Red = Below Pass Line 75\)/)).toBeInTheDocument()
    expect(screen.getByText('Chapter × Dimension Score Rate Heatmap')).toBeInTheDocument()
    expect(screen.getByText(/Contains 2 dimensions with chapter granularity/)).toBeInTheDocument()
    expect(screen.getByText('Chapter Issue Distribution (by Severity)')).toBeInTheDocument()

    const charts = await screen.findAllByTestId('base-chart')
    expect(charts).toHaveLength(3)
    expect(charts[0]).toHaveAttribute('aria-label', '12-Dimensional Score Overview Bar Chart')
    expect(charts[1]).toHaveAttribute('aria-label', 'Chapter-Dimension Score Rate Heatmap')
    expect(charts[2]).toHaveAttribute('aria-label', 'Chapter Issue Distribution Bar Chart')

    // 检查英文 xAxis 章节与 visualMap
    const heatOption = JSON.parse(charts[1].getAttribute('data-option') || '{}')
    expect(heatOption.xAxis.data).toEqual(['Ch.1', 'Ch.2'])
    expect(heatOption.visualMap.text).toEqual(['High', 'Low'])

    // 检查英文严重度标签
    const issueOption = JSON.parse(charts[2].getAttribute('data-option') || '{}')
    expect(issueOption.legend.data).toEqual(['Critical', 'High', 'Medium', 'Low'])
    expect(issueOption.xAxis.data).toEqual(['Ch.1', 'Ch.2'])
  })
})
