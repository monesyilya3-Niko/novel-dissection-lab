import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import ChapterList from './ChapterList'
import { I18nProvider } from '../state/I18nContext'

const mockSelectChapter = vi.fn()

const mockAppState = {
  book: null as unknown,
  selectedChapter: null as number | null,
  selectChapter: mockSelectChapter,
  batchStates: {} as Record<string, { status: string }>,
}

vi.mock('../state/AppContext', () => ({
  useApp: () => mockAppState,
}))

describe('ChapterList 章节列表组件', () => {
  it('未导入书籍时展示空提示', () => {
    mockAppState.book = null
    render(<ChapterList />)
    expect(screen.getByText('尚未导入书籍')).toBeInTheDocument()
  })

  it('en-US 环境下未导入书籍展示英文空提示', () => {
    mockAppState.book = null
    render(
      <I18nProvider initialLocale="en-US">
        <ChapterList />
      </I18nProvider>,
    )
    expect(screen.getByText('No book imported yet')).toBeInTheDocument()
  })

  it('渲染章节列表与不同状态徽标，点击触发选中章节', () => {
    mockAppState.book = {
      bookId: 'b1',
      title: '绝世剑神',
      totalChapters: 3,
      chapters: [
        { index: 1, title: '第一章 剑出青云', batchCount: 2 },
        { index: 2, title: '第二章 宗门大比', batchCount: 1 },
        { index: 3, title: '第三章 试炼深渊', batchCount: 1 },
      ],
    }
    mockAppState.selectedChapter = 2
    mockAppState.batchStates = {
      'c1-b0': { status: 'success' },
      'c1-b1': { status: 'success' },
      'c2-b0': { status: 'running' },
      'c3-b0': { status: 'failed' },
    }

    render(<ChapterList />)

    // 验证章节标题和序号
    expect(screen.getByText(/第1章\s*剑出青云/)).toBeInTheDocument()
    expect(screen.getByText(/第2章\s*宗门大比/)).toBeInTheDocument()
    expect(screen.getByText(/第3章\s*试炼深渊/)).toBeInTheDocument()

    // 验证状态计算：第1章全完成、第2章部分、第3章失败
    expect(screen.getByText('完成')).toBeInTheDocument()
    expect(screen.getByText('部分')).toBeInTheDocument()
    expect(screen.getByText('失败')).toBeInTheDocument()

    // 点击第 1 章
    const firstChapterBtn = screen.getByText(/第1章\s*剑出青云/).closest('div[role="button"]')
    expect(firstChapterBtn).toBeInTheDocument()
    if (firstChapterBtn) {
      fireEvent.click(firstChapterBtn)
      expect(mockSelectChapter).toHaveBeenCalledWith(1)
    }
  })

  it('en-US 环境下渲染英文章节序号与完成状态', () => {
    mockAppState.book = {
      bookId: 'b1',
      title: 'Dungeon Crawler',
      totalChapters: 1,
      chapters: [
        { index: 1, title: 'Chapter 1 Descent', batchCount: 1 },
      ],
    }
    mockAppState.selectedChapter = 1
    mockAppState.batchStates = {
      'c1-b0': { status: 'success' },
    }

    render(
      <I18nProvider initialLocale="en-US">
        <ChapterList />
      </I18nProvider>,
    )

    expect(screen.getByText(/Ch\.1\s*Chapter 1 Descent/)).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()
    expect(screen.getByText(/1\s*Batches/i)).toBeInTheDocument()
  })
})
