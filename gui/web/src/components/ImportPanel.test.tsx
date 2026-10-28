import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import ImportPanel from './ImportPanel'
import { I18nProvider } from '../state/I18nContext'

const mockUploadBook = vi.fn()
const mockImportSampleBook = vi.fn()
const mockListSamples = vi.fn()

const mockAppState = {
  book: null as unknown,
  uploadBook: mockUploadBook,
  importSampleBook: mockImportSampleBook,
}

vi.mock('../state/AppContext', () => ({
  useApp: () => mockAppState,
  useAppOptional: () => mockAppState,
}))

vi.mock('../api/client', () => ({
  listSamples: () => mockListSamples(),
}))

describe('ImportPanel 导入面板组件', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockListSamples.mockResolvedValue([
      { name: 'sample_xuanhuan.txt', genre: '玄幻修真', chapters: 12 },
    ])
  })

  it('渲染拖拽上传区域及选择文件按钮', async () => {
    mockAppState.book = null
    render(<ImportPanel />)

    expect(screen.getByText('导入 .txt 书籍')).toBeInTheDocument()
    expect(screen.getByText('拖拽到此处，或点击选择文件')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '选择文件' })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/玄幻修真 · 12 章/)).toBeInTheDocument()
    })
  })

  it('拦截非 .txt 格式文件并展示错误提示', async () => {
    mockAppState.book = null
    render(<ImportPanel />)

    const file = new File(['fake docx'], 'test.docx', { type: 'application/docx' })
    const dropZone = screen.getByText('导入 .txt 书籍').closest('div')!

    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [file],
      },
    })

    await waitFor(() => {
      expect(screen.getByText(/暂不支持 Word 文档导入|仅支持 .txt 文件导入/)).toBeInTheDocument()
    })
    expect(mockUploadBook).not.toHaveBeenCalled()
  })

  it('拖拽有效 .txt 文件能调用 uploadBook 接口', async () => {
    mockAppState.book = null
    mockUploadBook.mockResolvedValueOnce(undefined)
    render(<ImportPanel />)

    const file = new File(['第一章 剑出青云\n正文内容'], 'novel.txt', { type: 'text/plain' })
    const dropZone = screen.getByText('导入 .txt 书籍').closest('div')!

    fireEvent.drop(dropZone, {
      dataTransfer: {
        files: [file],
      },
    })

    await waitFor(() => {
      expect(mockUploadBook).toHaveBeenCalledWith(file)
    })
  })

  it('展示导入成功提示信息', () => {
    mockAppState.book = {
      bookId: 'b1',
      title: '斗破苍穹',
      totalChapters: 1200,
      chapters: [],
    }
    render(<ImportPanel />)

    expect(screen.getByText(/已导入《斗破苍穹》 · 1200 章/)).toBeInTheDocument()
  })

  it('点击内置示例语料芯片能触发 importSampleBook', async () => {
    mockAppState.book = null
    mockImportSampleBook.mockResolvedValueOnce(undefined)
    render(<ImportPanel />)

    await waitFor(() => {
      expect(screen.getByText(/玄幻修真 · 12 章/)).toBeInTheDocument()
    })

    const sampleChip = screen.getByText(/玄幻修真 · 12 章/)
    fireEvent.click(sampleChip)

    await waitFor(() => {
      expect(mockImportSampleBook).toHaveBeenCalledWith('sample_xuanhuan.txt')
    })
  })

  it('en-US 环境下渲染全量英文提示与动作', async () => {
    mockAppState.book = null
    render(
      <I18nProvider initialLocale="en-US">
        <ImportPanel />
      </I18nProvider>,
    )

    expect(screen.getByText('Import .txt Book')).toBeInTheDocument()
    expect(screen.getByText('Drag & drop here, or click to choose file')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Choose File' })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/玄幻修真 · 12 ch\./)).toBeInTheDocument()
    })
  })
})
