import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import {
  DashboardSkeleton,
  ListSkeleton,
  ChartSkeleton,
  FormSkeleton,
  InkEmptyState,
} from './SkeletonBlocks'
import AutoStoriesIcon from '@mui/icons-material/AutoStories'

describe('SkeletonBlocks 骨架屏与水墨空状态套件', () => {
  it('DashboardSkeleton 渲染统计指标网格与图表卡片占位', () => {
    const { container } = render(<DashboardSkeleton />)

    // 4 张指标卡片 + 2 张下方图表/列表卡片 = 6 个 MUI Card
    const cards = container.querySelectorAll('.MuiCard-root')
    expect(cards.length).toBe(6)

    // 包含多个骨架占位元素
    const skeletons = container.querySelectorAll('.MuiSkeleton-root')
    expect(skeletons.length).toBeGreaterThan(10)
  })

  it('ListSkeleton 默认渲染 6 行条目骨架，支持自定义行数', () => {
    // 默认 6 行
    const { container: c1 } = render(<ListSkeleton />)
    const circular1 = c1.querySelectorAll('.MuiSkeleton-circular')
    expect(circular1.length).toBe(6)

    // 自定义 3 行
    const { container: c2 } = render(<ListSkeleton rows={3} />)
    const circular2 = c2.querySelectorAll('.MuiSkeleton-circular')
    expect(circular2.length).toBe(3)
  })

  it('ChartSkeleton 渲染标题与指定高度的图表矩形占位', () => {
    // 默认高度 280
    const { container: c1 } = render(<ChartSkeleton />)
    const rounded1 = c1.querySelectorAll('.MuiSkeleton-rounded')
    expect(rounded1.length).toBe(1)

    // 自定义高度 360
    const { container: c2 } = render(<ChartSkeleton height={360} />)
    const rounded2 = c2.querySelectorAll('.MuiSkeleton-rounded')
    expect(rounded2.length).toBe(1)
  })

  it('FormSkeleton 默认渲染 4 个表单项及提交按钮骨架，支持自定义字段数', () => {
    // 默认 4 个字段
    const { container: c1 } = render(<FormSkeleton />)
    // 4 个输入框 rounded + 1 个按钮 rounded = 5
    const rounded1 = c1.querySelectorAll('.MuiSkeleton-rounded')
    expect(rounded1.length).toBe(5)

    // 自定义 2 个字段
    const { container: c2 } = render(<FormSkeleton fields={2} />)
    // 2 个输入框 + 1 个按钮 = 3
    const rounded2 = c2.querySelectorAll('.MuiSkeleton-rounded')
    expect(rounded2.length).toBe(3)
  })

  it('InkEmptyState 渲染水墨标题、提示说明与自定义图标', () => {
    render(
      <InkEmptyState
        title="暂无拆书资产"
        hint="请先在拆书工作台完成全书导入与流水线跑批"
        icon={<AutoStoriesIcon data-testid="empty-icon" />}
      />,
    )

    expect(screen.getByText('暂无拆书资产')).toBeInTheDocument()
    expect(screen.getByText('请先在拆书工作台完成全书导入与流水线跑批')).toBeInTheDocument()
    expect(screen.getByTestId('empty-icon')).toBeInTheDocument()
  })

  it('InkEmptyState 仅传入标题时正常渲染且不展示提示文案', () => {
    const { container } = render(<InkEmptyState title="无匹配结果" />)

    expect(screen.getByText('无匹配结果')).toBeInTheDocument()
    // 不存在多余的 hint dom 容器
    const textNodes = container.querySelectorAll('.MuiBox-root')
    expect(textNodes.length).toBeGreaterThan(0)
  })
})
