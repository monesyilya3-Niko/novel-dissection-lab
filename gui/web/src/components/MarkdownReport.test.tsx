import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import MarkdownReport from './MarkdownReport'

describe('MarkdownReport 报告富文本渲染组件', () => {
  it('渲染报告标题与基础段落', () => {
    const md = '这是段落内容，包含**粗体**与*斜体*。'
    render(<MarkdownReport title="全书质检分析总报告" markdown={md} />)

    expect(screen.getByText('全书质检分析总报告')).toBeInTheDocument()
    expect(screen.getByText(/这是段落内容/)).toBeInTheDocument()
    expect(screen.getByText('粗体')).toBeInTheDocument()
  })

  it('正确渲染 GFM 表格与列表', () => {
    const md = `
| 章节 | 评分 | 判定 |
| :--- | :--- | :--- |
| 第1章 | 95 | 优秀 |

- 伏笔回收
- 战力控制
`
    render(<MarkdownReport markdown={md} />)

    expect(screen.getByRole('table')).toBeInTheDocument()
    expect(screen.getByText('章节')).toBeInTheDocument()
    expect(screen.getByText('第1章')).toBeInTheDocument()
    expect(screen.getByText('伏笔回收')).toBeInTheDocument()
    expect(screen.getByText('战力控制')).toBeInTheDocument()
  })

  it('渲染超链接并携带安全性属性 target="_blank"', () => {
    const md = '详情参考 [文档链接](https://example.com/novel-doc)'
    render(<MarkdownReport markdown={md} />)

    const link = screen.getByRole('link', { name: '文档链接' })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('href', 'https://example.com/novel-doc')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noreferrer')
  })
})
