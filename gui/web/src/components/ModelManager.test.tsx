import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import ModelManager from './ModelManager'
import { I18nProvider } from '../state/I18nContext'

const mockList = vi.fn()
const mockPresets = vi.fn()
const mockAdd = vi.fn()
const mockUpdate = vi.fn()
const mockDelete = vi.fn()
const mockSetKey = vi.fn()
const mockTest = vi.fn()

vi.mock('../api/client', () => ({
  modelApi: {
    list: () => mockList(),
    presets: () => mockPresets(),
    add: (body: Record<string, unknown>) => mockAdd(body),
    update: (id: string, body: Record<string, unknown>) => mockUpdate(id, body),
    delete: (id: string) => mockDelete(id),
    setKey: (id: string, apiKey: string) => mockSetKey(id, apiKey),
    test: (id: string) => mockTest(id),
  },
  friendlyError: (e: unknown) => (e instanceof Error ? e.message : String(e)),
}))

describe('ModelManager 模型管理面板', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // 后端返回的是 **dict**（scripts/model_config.PRESETS 原样透传），
    // 不是数组。测试原先用数组 mock，正好掩盖了「presets.length 对 dict 是
    // undefined → 快速预设整块不渲染」的缺陷（2026-11-05 修）。
    mockPresets.mockResolvedValue({
      presets: {
        deepseek: {
          label: 'DeepSeek 官方',
          protocol: 'openai',
          base_url: 'https://api.deepseek.com/v1',
          model_name: 'deepseek-chat',
        },
      },
    })
  })

  it('初始加载时展示加载态，模型为空时展示空配置引导', async () => {
    mockList.mockResolvedValueOnce({ models: [] })

    render(<ModelManager />)

    // 等待数据加载完成
    await waitFor(() => {
      expect(screen.getByText('暂无模型配置，点击「添加模型」开始')).toBeInTheDocument()
    })
    expect(screen.getByText('模型管理')).toBeInTheDocument()
    expect(screen.getByText('添加模型')).toBeInTheDocument()
  })

  it('展示模型列表及其协议、Key状态、角色和访问信息', async () => {
    mockList.mockResolvedValueOnce({
      models: [
        {
          id: 'gpt-4o-main',
          label: 'GPT-4o 旗舰',
          protocol: 'openai',
          baseUrl: 'https://api.openai.com/v1',
          modelName: 'gpt-4o',
          roles: ['writer', 'critic'],
          hasKey: true,
          note: '生产主力',
        },
      ],
    })

    render(<ModelManager />)

    await waitFor(() => {
      expect(screen.getByText('GPT-4o 旗舰')).toBeInTheDocument()
    })
    expect(screen.getByText('gpt-4o-main')).toBeInTheDocument()
    expect(screen.getByText('openai')).toBeInTheDocument()
    expect(screen.getByText('已配 Key')).toBeInTheDocument()
    expect(screen.getByText(/gpt-4o @ https:\/\/api\.openai\.com\/v1/)).toBeInTheDocument()
    expect(screen.getByText(/角色：writer, critic/)).toBeInTheDocument()

    // 操作按钮
    expect(screen.getByText('测试')).toBeInTheDocument()
    expect(screen.getByText('密钥')).toBeInTheDocument()
    expect(screen.getByText('编辑')).toBeInTheDocument()
    expect(screen.getByText('删除')).toBeInTheDocument()
  })

  it('打开添加模型对话框，应用快速预设并提交添加', async () => {
    mockList.mockResolvedValue({ models: [] })
    mockAdd.mockResolvedValueOnce({ success: true })

    render(<ModelManager />)

    await waitFor(() => {
      expect(screen.getByText('添加模型')).toBeInTheDocument()
    })

    // 点击添加模型按钮
    fireEvent.click(screen.getByText('添加模型'))

    // 弹窗出现
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByText('快速选择预设：')).toBeInTheDocument()
    expect(screen.getByText('DeepSeek 官方')).toBeInTheDocument()

    // 点击预设快速填充
    fireEvent.click(screen.getByText('DeepSeek 官方'))

    // 检查表单已自动填入
    const idInput = screen.getByLabelText('模型 ID') as HTMLInputElement
    expect(idInput.value).toBe('deepseek')

    const labelInput = screen.getByLabelText('显示名称') as HTMLInputElement
    expect(labelInput.value).toBe('DeepSeek 官方')

    // 提交添加
    const submitBtn = screen.getByRole('button', { name: '添加' })
    expect(submitBtn).toBeEnabled()
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(mockAdd).toHaveBeenCalledWith({
        id: 'deepseek',
        label: 'DeepSeek 官方',
        protocol: 'openai',
        base_url: 'https://api.deepseek.com/v1',
        model_name: 'deepseek-chat',
      })
      expect(screen.getByText('模型已添加')).toBeInTheDocument()
    })
  })

  it('打开编辑模型对话框，锁定 ID 并提交修改', async () => {
    mockList.mockResolvedValue({
      models: [
        {
          id: 'custom-claude',
          label: 'Claude 3.5 Sonnet',
          protocol: 'anthropic',
          baseUrl: 'https://api.anthropic.com',
          modelName: 'claude-3-5-sonnet',
          roles: ['analyst'],
          hasKey: false,
          note: '旧备注',
        },
      ],
    })
    mockUpdate.mockResolvedValueOnce({ success: true })

    render(<ModelManager />)

    await waitFor(() => {
      expect(screen.getByText('Claude 3.5 Sonnet')).toBeInTheDocument()
    })

    // 点击编辑
    fireEvent.click(screen.getByText('编辑'))

    // 对话框弹出
    expect(screen.getByText('编辑模型: custom-claude')).toBeInTheDocument()
    const idInput = screen.getByLabelText('模型 ID') as HTMLInputElement
    expect(idInput).toBeDisabled()
    expect(idInput.value).toBe('custom-claude')

    // 修改显示名称
    const labelInput = screen.getByLabelText('显示名称') as HTMLInputElement
    fireEvent.change(labelInput, { target: { value: 'Claude 3.5 Sonnet Updated' } })

    // 保存
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith(
        'custom-claude',
        expect.objectContaining({
          id: 'custom-claude',
          label: 'Claude 3.5 Sonnet Updated',
        }),
      )
      expect(screen.getByText('模型已更新')).toBeInTheDocument()
    })
  })

  it('配置并保存 API Key', async () => {
    mockList.mockResolvedValue({
      models: [
        {
          id: 'm1',
          label: 'Model 1',
          protocol: 'openai',
          baseUrl: 'https://api.test.com',
          modelName: 'm-1',
          roles: [],
          hasKey: false,
        },
      ],
    })
    mockSetKey.mockResolvedValueOnce({ success: true })

    render(<ModelManager />)

    await waitFor(() => {
      expect(screen.getByText('密钥')).toBeInTheDocument()
    })

    // 点击密钥按钮
    fireEvent.click(screen.getByText('密钥'))

    expect(screen.getByText('设置 API Key: m1')).toBeInTheDocument()

    // 输入密码
    const keyInput = screen.getByLabelText('API Key')
    fireEvent.change(keyInput, { target: { value: 'sk-secret-key-12345' } })

    // 点击保存
    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(mockSetKey).toHaveBeenCalledWith('m1', 'sk-secret-key-12345')
      expect(screen.getByText('API Key 已保存')).toBeInTheDocument()
    })
  })

  it('测试模型连通性：成功与失败分支验证', async () => {
    mockList.mockResolvedValue({
      models: [
        {
          id: 'm-test',
          label: 'Test Model',
          protocol: 'openai',
          baseUrl: 'https://api.test.com',
          modelName: 'm-test',
          roles: [],
          hasKey: true,
        },
      ],
    })

    // 成功案例
    mockTest.mockResolvedValueOnce({ success: true })

    render(<ModelManager />)

    await waitFor(() => {
      expect(screen.getByText('测试')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('测试'))

    await waitFor(() => {
      expect(mockTest).toHaveBeenCalledWith('m-test')
      expect(screen.getByText('m-test 连接成功')).toBeInTheDocument()
    })

    // 失败案例
    mockTest.mockResolvedValueOnce({ success: false, error: 'Network timeout (504)' })

    fireEvent.click(screen.getByText('测试'))

    await waitFor(() => {
      expect(screen.getByText(/m-test\s*连接失败.*Network timeout/)).toBeInTheDocument()
    })
  })

  it('删除模型需用户确认，取消则不执行删除，确认则调用接口', async () => {
    mockList.mockResolvedValue({
      models: [
        {
          id: 'm-to-delete',
          label: 'To Delete',
          protocol: 'openai',
          baseUrl: 'https://api.test.com',
          modelName: 'm-to-delete',
          roles: [],
          hasKey: false,
        },
      ],
    })
    mockDelete.mockResolvedValueOnce({ success: true })

    const confirmSpy = vi.spyOn(window, 'confirm')

    render(<ModelManager />)

    await waitFor(() => {
      expect(screen.getByText('删除')).toBeInTheDocument()
    })

    // 1. 取消删除
    confirmSpy.mockReturnValueOnce(false)
    fireEvent.click(screen.getByText('删除'))
    expect(confirmSpy).toHaveBeenCalledWith('确认删除模型 m-to-delete？')
    expect(mockDelete).not.toHaveBeenCalled()

    // 2. 确认删除
    confirmSpy.mockReturnValueOnce(true)
    fireEvent.click(screen.getByText('删除'))
    expect(confirmSpy).toHaveBeenCalledWith('确认删除模型 m-to-delete？')

    await waitFor(() => {
      expect(mockDelete).toHaveBeenCalledWith('m-to-delete')
      expect(screen.getByText('m-to-delete 已删除')).toBeInTheDocument()
    })

    confirmSpy.mockRestore()
  })

  it('en-US 国际化语言下全界面双语渲染', async () => {
    mockList.mockResolvedValue({
      models: [
        {
          id: 'deepseek-v3',
          label: 'DeepSeek V3',
          protocol: 'openai',
          baseUrl: 'https://api.deepseek.com',
          modelName: 'deepseek-chat',
          roles: ['writer'],
          hasKey: true,
        },
      ],
    })

    render(
      <I18nProvider initialLocale="en-US">
        <ModelManager />
      </I18nProvider>,
    )

    await waitFor(() => {
      expect(screen.getByText('Model Management')).toBeInTheDocument()
    })

    expect(screen.getByText('Add Model')).toBeInTheDocument()
    expect(screen.getByText('Key Set')).toBeInTheDocument()
    expect(screen.getByText(/Roles:\s*writer/)).toBeInTheDocument()
    expect(screen.getByText('Test')).toBeInTheDocument()
    expect(screen.getByText('API Key')).toBeInTheDocument()
    expect(screen.getByText('Edit')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()

    // 打开 Add Model 弹窗测试英文标签
    fireEvent.click(screen.getByText('Add Model'))
    expect(screen.getByText(/Quick Presets/i)).toBeInTheDocument()
    expect(screen.getByLabelText('Model ID')).toBeInTheDocument()
    expect(screen.getByLabelText('Display Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Protocol')).toBeInTheDocument()
    expect(screen.getByLabelText('Base URL')).toBeInTheDocument()
    expect(screen.getByLabelText('Model Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Notes')).toBeInTheDocument()
    expect(screen.getByText('Cancel')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add' })).toBeInTheDocument()
  })
})
