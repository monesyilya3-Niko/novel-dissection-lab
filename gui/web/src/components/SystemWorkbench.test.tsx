import { render, screen, fireEvent, waitFor, waitForElementToBeRemoved } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import SystemWorkbench from './SystemWorkbench'
import { I18nProvider } from '../state/I18nContext'
import { systemApi, modelApi } from '../api/client'

vi.mock('../api/client', () => ({
  systemApi: {
    status: vi.fn(),
    compliance: vi.fn(),
    settings: vi.fn(),
  },
  modelApi: {
    list: vi.fn(),
    presets: vi.fn(),
    add: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    setKey: vi.fn(),
    test: vi.fn(),
  },
  friendlyError: vi.fn((e) => String(e)),
}))

describe('SystemWorkbench 系统与合规工作台双语国际化支持', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(systemApi.status).mockResolvedValue({
      disk: {
        assetsBytes: 2048000,
        reportsBytes: 1024000,
        corpusBytes: 512000,
        novelBytes: 256000,
        dbBytes: 128000,
        totalBytes: 3968000,
      },
      counts: {
        assets: 42,
        reports: 12,
        bookNames: ['斗破苍穹', '诡秘之主'],
      },
      model: {
        configured: true,
        models: [
          { id: 'gpt-4o', name: 'OpenAI GPT-4o' },
        ],
      },
      paths: {
        workspace: '/data/workspace',
      },
    })

    vi.mocked(systemApi.compliance).mockResolvedValue({
      summary: {
        total: 10,
        passed: 8,
        warned: 1,
        rejected: 1,
      },
      results: [
        {
          name: 'asset_01.json',
          verdict: 'PASS',
          errors: [],
          warns: [],
        },
      ],
    })

    vi.mocked(systemApi.settings).mockResolvedValue({
      port: 8080,
      batchSize: 5000,
      paths: {
        dataDir: '/data',
      },
      envOverrides: {
        OPENAI_API_KEY: 'sk-***',
      },
    })

    vi.mocked(modelApi.list).mockResolvedValue({
      models: [
        {
          id: 'gpt-4o',
          label: 'GPT-4 Omni',
          protocol: 'openai',
          baseUrl: 'https://api.openai.com/v1',
          modelName: 'gpt-4o',
          roles: ['chat', 'reasoning'],
          hasKey: true,
        },
      ],
    })

    vi.mocked(modelApi.presets).mockResolvedValue({
      presets: [
        {
          name: 'deepseek-chat',
          label: 'DeepSeek Chat',
          protocol: 'openai',
          baseUrl: 'https://api.deepseek.com/v1',
          modelName: 'deepseek-chat',
        },
      ],
    })
  })

  it('zh-CN 默认环境下渲染中文顶层 Tabs 与四大子面板', async () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <SystemWorkbench />
      </I18nProvider>
    )

    // 四大 Tab 标签
    expect(screen.getByRole('tab', { name: '系统状态' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '版权合规' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '模型配置' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '设置' })).toBeInTheDocument()

    // 默认处于系统状态页签
    expect(await screen.findByRole('heading', { name: '系统状态' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '刷新' })).toBeInTheDocument()
    expect(screen.getByText('磁盘占用')).toBeInTheDocument()
    expect(screen.getByText('数据统计')).toBeInTheDocument()
    expect(screen.getByText('模型状态')).toBeInTheDocument()
    expect(screen.getByText('已配置')).toBeInTheDocument()
    expect(screen.getByText(/资产 42 个/)).toBeInTheDocument()

    // 切换到版权合规页签
    fireEvent.click(screen.getByRole('tab', { name: '版权合规' }))
    expect(await screen.findByRole('heading', { name: '版权合规扫描' })).toBeInTheDocument()
    const scanBtn = screen.getByRole('button', { name: '全量扫描' })
    expect(scanBtn).toBeInTheDocument()
    fireEvent.click(scanBtn)
    await waitFor(() => {
      expect(screen.getByText(/共 10 个资产：8 PASS \/ 1 WARN \/ 1 REJECT/)).toBeInTheDocument()
      expect(screen.getByText('asset_01.json')).toBeInTheDocument()
    })

    // 切换到设置页签
    fireEvent.click(screen.getByRole('tab', { name: '设置' }))
    expect(await screen.findByRole('heading', { name: '系统设置' })).toBeInTheDocument()
    expect(screen.getByText('服务')).toBeInTheDocument()
    expect(screen.getByText('环境变量覆盖')).toBeInTheDocument()
    expect(screen.getByText(/设置修改请通过环境变量/)).toBeInTheDocument()

    // 切换到模型配置页签
    fireEvent.click(screen.getByRole('tab', { name: '模型配置' }))
    expect(await screen.findByRole('heading', { name: '模型管理' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '添加模型' })).toBeInTheDocument()
    expect(screen.getByText('已配 Key')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '测试' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '密钥' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '编辑' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '删除' })).toBeInTheDocument()

    // 打开添加模型对话框检查中文文案并关闭
    fireEvent.click(screen.getByRole('button', { name: '添加模型' }))
    expect(await screen.findByText('快速选择预设：')).toBeInTheDocument()
    expect(screen.getByLabelText('模型 ID')).toBeInTheDocument()
    expect(screen.getByLabelText('显示名称')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '取消' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '添加' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '取消' }))
    await waitForElementToBeRemoved(() => screen.queryByRole('dialog'))
  })

  it('en-US 语言环境下全量渲染英文 Tabs 与子面板文案', async () => {
    render(
      <I18nProvider initialLocale="en-US">
        <SystemWorkbench />
      </I18nProvider>
    )

    // 英文四大 Tab
    expect(screen.getByRole('tab', { name: 'System Status' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Copyright Compliance' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Model Config' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Settings' })).toBeInTheDocument()

    // 默认处于英文系统状态页签
    expect(await screen.findByRole('heading', { name: 'System Status' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Refresh' })).toBeInTheDocument()
    expect(screen.getByText('Disk Usage')).toBeInTheDocument()
    expect(screen.getByText('Data Statistics')).toBeInTheDocument()
    expect(screen.getByText('Model Status')).toBeInTheDocument()
    expect(screen.getByText('Configured')).toBeInTheDocument()
    expect(screen.getByText(/Assets: 42/)).toBeInTheDocument()

    // 切换到英文版权合规面板
    fireEvent.click(screen.getByRole('tab', { name: 'Copyright Compliance' }))
    expect(await screen.findByRole('heading', { name: 'Copyright Compliance Scan' })).toBeInTheDocument()
    const scanBtn = screen.getByRole('button', { name: 'Full Scan' })
    expect(scanBtn).toBeInTheDocument()
    fireEvent.click(scanBtn)
    await waitFor(() => {
      expect(screen.getByText(/Total 10 assets: 8 PASS \/ 1 WARN \/ 1 REJECT/)).toBeInTheDocument()
      expect(screen.getByText('asset_01.json')).toBeInTheDocument()
    })

    // 切换到英文设置面板
    fireEvent.click(screen.getByRole('tab', { name: 'Settings' }))
    expect(await screen.findByRole('heading', { name: 'System Settings' })).toBeInTheDocument()
    expect(screen.getByText('Services')).toBeInTheDocument()
    expect(screen.getByText('Environment Overrides')).toBeInTheDocument()
    expect(screen.getByText(/To modify settings, use environment variables/)).toBeInTheDocument()

    // 切换到英文模型管理面板
    fireEvent.click(screen.getByRole('tab', { name: 'Model Config' }))
    expect(await screen.findByRole('heading', { name: 'Model Management' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add Model' })).toBeInTheDocument()
    expect(screen.getByText('Key Set')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Test' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'API Key' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Edit' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument()

    // 打开添加模型对话框检查英文文案
    fireEvent.click(screen.getByRole('button', { name: 'Add Model' }))
    expect(await screen.findByText('Quick Presets:')).toBeInTheDocument()
    expect(screen.getByLabelText('Model ID')).toBeInTheDocument()
    expect(screen.getByLabelText('Display Name')).toBeInTheDocument()
    expect(screen.getByLabelText('Protocol')).toBeInTheDocument()
    expect(screen.getByLabelText('Base URL')).toBeInTheDocument()
    expect(screen.getByLabelText('Model Name')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Add' })).toBeInTheDocument()

    // 关闭对话框
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }))
    await waitForElementToBeRemoved(() => screen.queryByRole('dialog'))
  })
})

