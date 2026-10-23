import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ProgressPanel from './ProgressPanel'
import { I18nProvider } from '../state/I18nContext'

const mockAppState = {
  book: null as unknown,
  batchStates: {} as Record<string, { status: string }>,
  status: { status: 'idle', done: 0, total: 0, cursor: '' },
}

vi.mock('../state/AppContext', () => ({
  useApp: () => mockAppState,
}))

describe('ProgressPanel 分析进度面板组件', () => {
  it('未导入书籍时渲染空提示', () => {
    mockAppState.book = null
    render(<ProgressPanel />)
    expect(screen.getByText('请先导入书籍')).toBeInTheDocument()
  })

  it('en-US 环境下未导入书籍渲染英文空提示', () => {
    mockAppState.book = null
    render(
      <I18nProvider initialLocale="en-US">
        <ProgressPanel />
      </I18nProvider>,
    )
    expect(screen.getByText('Please import a book first')).toBeInTheDocument()
  })

  it('渲染进度条、计算完成批次与章×批状态矩阵', () => {
    mockAppState.book = {
      bookId: 'b1',
      title: '诡秘之主',
      totalChapters: 2,
      chapters: [
        { index: 1, title: '第一章 绯红', batchCount: 2 },
        { index: 2, title: '第二章 局势', batchCount: 2 },
      ],
    }
    mockAppState.batchStates = {
      'c1-b0': { status: 'success' },
      'c1-b1': { status: 'success' },
      'c2-b0': { status: 'running' },
      'c2-b1': { status: 'pending' },
    }
    mockAppState.status = { status: 'running', done: 2, total: 4, cursor: 'c2-b0' }

    render(<ProgressPanel />)

    expect(screen.getByText('分析进度')).toBeInTheDocument()
    // 2 / 4 批 · 50%
    expect(screen.getByText(/2\s*\/\s*4\s*批\s*·\s*50%/)).toBeInTheDocument()
    // 当前状态与检查点
    expect(screen.getByText(/当前状态：运行中 · 断点 c2-b0/)).toBeInTheDocument()

    // 章节行
    expect(screen.getByText('第1章')).toBeInTheDocument()
    expect(screen.getByText('第2章')).toBeInTheDocument()

    // 图例标签
    expect(screen.getByText('等待')).toBeInTheDocument()
    expect(screen.getByText('运行中')).toBeInTheDocument()
    expect(screen.getByText('成功')).toBeInTheDocument()
    expect(screen.getByText('失败')).toBeInTheDocument()
    expect(screen.getByText('跳过')).toBeInTheDocument()
  })

  it('en-US 环境下渲染英文进度与图例', () => {
    mockAppState.book = {
      bookId: 'b1',
      title: 'Dune',
      totalChapters: 1,
      chapters: [
        { index: 1, title: 'Chapter 1 Arrakis', batchCount: 1 },
      ],
    }
    mockAppState.batchStates = {
      'c1-b0': { status: 'success' },
    }
    mockAppState.status = { status: 'success', done: 1, total: 1, cursor: 'c1-b0' }

    render(
      <I18nProvider initialLocale="en-US">
        <ProgressPanel />
      </I18nProvider>,
    )

    expect(screen.getByText('Analysis Progress')).toBeInTheDocument()
    expect(screen.getByText(/1\s*\/\s*1\s*batches\s*·\s*100%/i)).toBeInTheDocument()
    expect(screen.getByText(/Current Status：Success · Checkpoint c1-b0/i)).toBeInTheDocument()
    expect(screen.getByText('Ch.1')).toBeInTheDocument()

    expect(screen.getByText('Pending')).toBeInTheDocument()
    expect(screen.getByText('Running')).toBeInTheDocument()
    expect(screen.getByText('Success')).toBeInTheDocument()
  })
})
