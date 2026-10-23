import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import StylePanel from './StylePanel'
import { I18nProvider } from '../state/I18nContext'
import { styleApi } from '../api/client'

vi.mock('../api/client', () => ({
  styleApi: {
    list: vi.fn(),
    analyze: vi.fn(),
    save: vi.fn(),
    delete: vi.fn(),
  },
  friendlyError: (e: unknown) => String(e),
}))

const mockList = vi.mocked(styleApi.list)
const mockAnalyze = vi.mocked(styleApi.analyze)
const mockSave = vi.mocked(styleApi.save)
const mockDelete = vi.mocked(styleApi.delete)

describe('StylePanel 文风面板双语国际化与功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockList.mockResolvedValue({
      styles: [
        {
          name: '悬疑冷峻风',
          createdAt: '2026-10-18T00:00:00Z',
          metrics: { avg_sentence_length: 15, dialogue_ratio: 0.28 },
        },
      ],
    })
  })

  it('zh-CN 语言环境下正确展示中文标签、指南说明与风格分析流程', async () => {
    mockAnalyze.mockResolvedValueOnce({
      metrics: {
        avgSentenceLength: 14,
        dialogueRatio: 0.32,
        emotionDensity: 5.1,
        avgParagraphLength: 68,
        shortParagraphRatio: 0.25,
        totalChars: 650,
      },
    })

    render(
      <I18nProvider initialLocale="zh-CN">
        <StylePanel />
      </I18nProvider>
    )

    // 选项卡
    expect(screen.getByRole('button', { name: '风格分析' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '风格库' })).toBeInTheDocument()

    // 说明与输入框
    expect(screen.getByText(/从一段样本文本里提取可量化的风格指标/)).toBeInTheDocument()
    expect(screen.getByLabelText('风格名称')).toBeInTheDocument()
    expect(screen.getByLabelText('文本样本')).toBeInTheDocument()

    // 输入并分析
    fireEvent.change(screen.getByLabelText('风格名称'), { target: { value: '我的测试风' } })
    fireEvent.change(screen.getByLabelText('文本样本'), {
      target: { value: '风雪漫天，刀光如练。黑衣人拔剑出鞘，直指中军大帐！这便是江湖的宿命。' },
    })

    const analyzeBtn = screen.getByRole('button', { name: '分析风格' })
    fireEvent.click(analyzeBtn)

    // 分析指标展示
    expect(await screen.findByText('风格指标')).toBeInTheDocument()
    expect(screen.getByText(/平均句长：/)).toBeInTheDocument()
    expect(screen.getByText(/对话占比：/)).toBeInTheDocument()
    expect(screen.getByText(/情绪密度：/)).toBeInTheDocument()

    // 保存风格卡
    const saveBtn = screen.getByRole('button', { name: '保存风格卡' })
    mockSave.mockResolvedValueOnce({ ok: true } as any)
    fireEvent.click(saveBtn)
    await waitFor(() => {
      expect(mockSave).toHaveBeenCalledWith({
        name: '我的测试风',
        style_card: expect.anything(),
      })
    })
  })

  it('en-US 语言环境下全量渲染英文面板、指标与风格库', async () => {
    render(
      <I18nProvider initialLocale="en-US">
        <StylePanel />
      </I18nProvider>
    )

    // 英文选项卡
    expect(screen.getByRole('button', { name: 'Style Analysis' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Style Library' })).toBeInTheDocument()

    // 英文表单与指南
    expect(screen.getByLabelText('Style Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Text Sample')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Analyze Style' })).toBeInTheDocument()

    // 切换到风格库
    fireEvent.click(screen.getByRole('button', { name: 'Style Library' }))
    expect(await screen.findByText('悬疑冷峻风')).toBeInTheDocument()
    expect(screen.getByText(/Sentence 15 chars \| Dialogue 28%/)).toBeInTheDocument()
    const deleteBtn = screen.getByRole('button', { name: 'Delete' })
    expect(deleteBtn).toBeInTheDocument()
    vi.spyOn(window, 'confirm').mockReturnValueOnce(true)
    mockDelete.mockResolvedValueOnce({ ok: true } as any)
    fireEvent.click(deleteBtn)
    expect(mockDelete).toHaveBeenCalledWith('悬疑冷峻风')
  })

  it('风格库为空时在 en-US 环境下展示英文提示', async () => {
    mockList.mockResolvedValueOnce({ styles: [] })

    render(
      <I18nProvider initialLocale="en-US">
        <StylePanel />
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('button', { name: 'Style Library' }))
    expect(await screen.findByText('No style cards yet. Create one in "Style Analysis".')).toBeInTheDocument()
  })
})
