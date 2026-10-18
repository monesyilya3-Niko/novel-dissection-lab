import { render, screen, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import ReaderPanel from './ReaderPanel'
import { I18nProvider } from '../state/I18nContext'
import type { Chapter, Book } from '../types'

const mockSelectChapter = vi.fn()
let mockCurrentChapter: Chapter | null = null
let mockSelectedChapter: number | null = null
let mockBook: Book | null = null

vi.mock('../state/AppContext', () => ({
  useApp: () => ({
    currentChapter: mockCurrentChapter,
    selectedChapter: mockSelectedChapter,
    book: mockBook,
    selectChapter: mockSelectChapter,
  }),
}))

describe('ReaderPanel 内容阅读器双语国际化与翻章导航测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockCurrentChapter = null
    mockSelectedChapter = null
    mockBook = null
  })

  it('未选择章节时在 zh-CN 和 en-US 下分别展示空态提示', () => {
    const { rerender } = render(
      <I18nProvider initialLocale="zh-CN">
        <ReaderPanel />
      </I18nProvider>
    )
    expect(screen.getByText('请在左侧选择章节开始阅读')).toBeInTheDocument()

    rerender(
      <I18nProvider initialLocale="en-US">
        <ReaderPanel />
      </I18nProvider>
    )
    expect(screen.getByText('Please select a chapter on the left to start reading')).toBeInTheDocument()
  })

  it('zh-CN 环境下正确展示章节标题与翻章操作', () => {
    mockBook = {
      id: 'book-1',
      title: '测试书籍',
      author: '作者',
      totalChapters: 10,
    } as any
    mockSelectedChapter = 2
    mockCurrentChapter = {
      index: 2,
      title: '第二章 风雪夜归人',
      text: '寒风呼啸。\n一行人行进在山谷之间。',
    } as any

    render(
      <I18nProvider initialLocale="zh-CN">
        <ReaderPanel />
      </I18nProvider>
    )

    // 章节标题
    expect(screen.getByText('第2章 第二章 风雪夜归人')).toBeInTheDocument()

    // 翻上一章
    const prevBtn = screen.getByRole('button', { name: '上一章' })
    expect(prevBtn).toBeInTheDocument()
    fireEvent.click(prevBtn)
    expect(mockSelectChapter).toHaveBeenCalledWith(1)

    // 翻下一章
    const nextBtn = screen.getByRole('button', { name: '下一章' })
    expect(nextBtn).toBeInTheDocument()
    fireEvent.click(nextBtn)
    expect(mockSelectChapter).toHaveBeenCalledWith(3)
  })

  it('en-US 环境下展示英文章节格式与操作提示', () => {
    mockBook = {
      id: 'book-1',
      title: 'Test Book',
      author: 'Author',
      totalChapters: 10,
    } as any
    mockSelectedChapter = 5
    mockCurrentChapter = {
      index: 5,
      title: 'The Calm Before the Storm',
      text: 'The wind was quiet.\nSilence gripped the empty streets.',
    } as any

    render(
      <I18nProvider initialLocale="en-US">
        <ReaderPanel />
      </I18nProvider>
    )

    // 英文章节标题
    expect(screen.getByText('Chapter 5: The Calm Before the Storm')).toBeInTheDocument()

    // 英文 tooltip / aria-label
    expect(screen.getByRole('button', { name: 'Previous Chapter' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Next Chapter' })).toBeInTheDocument()
  })
})
