import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AdvancedWorkbench from './AdvancedWorkbench'
import { I18nProvider } from '../state/I18nContext'
import { advancedApi, assetApi } from '../api/client'

vi.mock('../api/client', () => ({
  advancedApi: {
    distillStatus: vi.fn(),
    distillRun: vi.fn(),
    batchStatus: vi.fn(),
  },
  assetApi: {
    list: vi.fn(),
    detail: vi.fn(),
    update: vi.fn(),
  },
  friendlyError: vi.fn((e) => String(e)),
}))

describe('AdvancedWorkbench 高级功能工坊双语支持', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(advancedApi.distillStatus).mockResolvedValue({
      canDistill: true,
      books: ['book-A', 'book-B'],
      distilledAssets: ['distilled-A'],
    })
    vi.mocked(advancedApi.batchStatus).mockResolvedValue({
      books: [
        {
          name: 'Book-1',
          passCount: 5,
          hasAssets: true,
          passes: { pass1_structure: true, pass2_character: true },
        },
      ],
    })
    vi.mocked(assetApi.list).mockResolvedValue({
      items: [
        { id: 'v1', name: 'voice-1', kind: 'voice' },
      ],
    })
  })

  it('zh-CN 默认环境下渲染中文顶层 Tabs 与四大子面板', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <AdvancedWorkbench />
      </I18nProvider>
    )

    // 四大 Tab 标签
    expect(screen.getByRole('tab', { name: '蒸馏' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '批量状态' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '资产编辑' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '平台适配' })).toBeInTheDocument()

    // 默认处于蒸馏页签
    expect(screen.getByRole('heading', { name: '题材蒸馏' })).toBeInTheDocument()
    expect(screen.getByLabelText('题材')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '执行蒸馏' })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/可蒸馏书目：/)).toBeInTheDocument()
      expect(screen.getByText('可蒸馏')).toBeInTheDocument()
    })

    // 切换到批量状态
    fireEvent.click(screen.getByRole('tab', { name: '批量状态' }))
    expect(await screen.findByRole('heading', { name: '批量拆书状态' })).toBeInTheDocument()
    expect(screen.getByText('已有资产')).toBeInTheDocument()
    expect(screen.getByText('P1 结构')).toBeInTheDocument()

    // 切换到资产编辑
    fireEvent.click(screen.getByRole('tab', { name: '资产编辑' }))
    expect(await screen.findByRole('heading', { name: '资产编辑' })).toBeInTheDocument()
    expect(screen.getByLabelText('选择资产')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '加载' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '保存' })).toBeInTheDocument()
    expect(screen.getByLabelText('资产 JSON 内容')).toBeInTheDocument()
  })

  it('en-US 语言环境下全量渲染英文 Tabs 与子面板文案', async () => {
    render(
      <I18nProvider initialLocale="en-US">
        <AdvancedWorkbench />
      </I18nProvider>
    )

    // 英文四大 Tab
    expect(screen.getByRole('tab', { name: 'Distillation' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Batch Status' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Asset Editor' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Platform Adaptation' })).toBeInTheDocument()

    // 英文蒸馏面板
    expect(screen.getByRole('heading', { name: 'Genre Distillation' })).toBeInTheDocument()
    expect(screen.getByLabelText('Genre')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Execute Distillation' })).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText(/Available Books:/)).toBeInTheDocument()
      expect(screen.getByText('Ready to Distill')).toBeInTheDocument()
    })

    // 切换到英文批量状态面板
    fireEvent.click(screen.getByRole('tab', { name: 'Batch Status' }))
    expect(await screen.findByRole('heading', { name: 'Batch Deconstruction Status' })).toBeInTheDocument()
    expect(screen.getByText('Assets Present')).toBeInTheDocument()
    expect(screen.getByText('P1 Structure')).toBeInTheDocument()

    // 切换到英文资产编辑面板
    fireEvent.click(screen.getByRole('tab', { name: 'Asset Editor' }))
    expect(await screen.findByRole('heading', { name: 'Asset Editor' })).toBeInTheDocument()
    expect(screen.getByLabelText('Select Asset')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Load' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Save' })).toBeInTheDocument()
    expect(screen.getByLabelText('Asset JSON Content')).toBeInTheDocument()
  })

  it('AssetEditPanel 防跨资产误写守卫、未保存加载确认与 Ctrl+S 快捷保存', async () => {
    vi.mocked(assetApi.list).mockResolvedValue({
      items: [
        { id: 'v1', name: '资产A', kind: 'voice' },
        { id: 'v2', name: '资产B', kind: 'voice' },
      ],
    })
    vi.mocked(assetApi.detail)
      .mockResolvedValueOnce({ content: { owner: 'asset-A' } } as any)
      .mockResolvedValueOnce({ content: { owner: 'asset-B' } } as any)
    vi.mocked(assetApi.update).mockResolvedValue({ ok: true } as any)

    const confirmSpy = vi.spyOn(window, 'confirm')

    render(
      <I18nProvider initialLocale="zh-CN">
        <AdvancedWorkbench />
      </I18nProvider>
    )

    fireEvent.click(screen.getByRole('tab', { name: '资产编辑' }))
    const selectInput = await screen.findByLabelText('选择资产')

    // 1. 选择资产 A 并点击加载
    fireEvent.mouseDown(selectInput)
    fireEvent.click(await screen.findByRole('option', { name: '资产A（声线卡）' }))
    fireEvent.click(screen.getByRole('button', { name: '加载' }))

    const editor = await screen.findByLabelText('资产 JSON 内容')
    await waitFor(() => {
      expect((editor as HTMLTextAreaElement).value).toContain('"asset-A"')
    })

    // 2. 修改资产 A 的 JSON，然后将下拉框切到资产 B（不点加载），直接按 Ctrl+S 保存
    fireEvent.change(editor, { target: { value: '{\n  "owner": "asset-A-edited"\n}' } })
    fireEvent.mouseDown(selectInput)
    fireEvent.click(await screen.findByRole('option', { name: '资产B（声线卡）' }))

    // 出现跨资产保护提示，且按 Ctrl+S 必须保存到已加载的 v1（绝不能误写到 v2！）
    expect(screen.getByText(/当前编辑器仍为已加载资产「voice:v1」/)).toBeInTheDocument()
    fireEvent.keyDown(editor, { key: 's', ctrlKey: true })

    await waitFor(() => {
      expect(assetApi.update).toHaveBeenCalledTimes(1)
      expect(assetApi.update).toHaveBeenCalledWith('voice', 'v1', { owner: 'asset-A-edited' })
    })

    // 3. 再次改脏后点击「加载」资产 B：若取消确认则不丢弃修改；确认后才加载资产 B
    fireEvent.change(editor, { target: { value: '{\n  "owner": "unsaved-change"\n}' } })
    confirmSpy.mockReturnValueOnce(false)
    fireEvent.click(screen.getByRole('button', { name: '加载' }))
    expect(confirmSpy).toHaveBeenCalled()
    expect((editor as HTMLTextAreaElement).value).toContain('unsaved-change')

    confirmSpy.mockReturnValueOnce(true)
    fireEvent.click(screen.getByRole('button', { name: '加载' }))
    await waitFor(() => {
      expect((editor as HTMLTextAreaElement).value).toContain('"asset-B"')
    })

    confirmSpy.mockRestore()
  })
})
