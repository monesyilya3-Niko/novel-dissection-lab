import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import AdminWorkbench from './AdminWorkbench'
import { I18nProvider } from '../state/I18nContext'
import { adminApi } from '../api/client'

vi.mock('../api/client', () => ({
  adminApi: {
    me: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    dashboard: vi.fn(),
    books: vi.fn(),
    deleteBook: vi.fn(),
    assets: vi.fn(),
    deleteAsset: vi.fn(),
    reports: vi.fn(),
    audit: vi.fn(),
    changePassword: vi.fn(),
    sessions: vi.fn(),
    revokeSession: vi.fn(),
  },
  friendlyError: vi.fn((e) => String(e)),
  onAdminUnauthorized: vi.fn(),
  ApiError: class ApiError extends Error {
    code: number
    constructor(msg: string, code = 0) {
      super(msg)
      this.code = code
    }
  },
}))

describe('AdminWorkbench 管理工作台双语国际化与运维功能测试', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    vi.mocked(adminApi.dashboard).mockResolvedValue({
      version: '1.0.0',
      python: '3.13',
      startedAt: '2026-10-17 10:00:00',
      uptimeSeconds: 7320, // 2h 2m
      books: {
        total: 5,
        analyzing: 1,
        items: [
          { bookId: 'b1', title: '诡秘之主', totalChapters: 120, status: 'ready' },
        ],
      },
      assetsTotal: 42,
      assetsByKind: {
        voice_card: 10,
        genre_pack: 5,
      },
      reportsTotal: 12,
      diskTotalBytes: 52428800,
      diskBytes: {
        assets: 10485760,
        books: 41943040,
      },
      recentAudit: [
        { ts: '2026-10-17 12:00:00', username: 'admin', ip: '127.0.0.1', action: 'admin.login', detail: '成功登录' },
      ],
    })

    vi.mocked(adminApi.books).mockResolvedValue([
      { bookId: 'b1', title: '宿命之环', totalChapters: 80, status: 'ready' },
      { bookId: 'b2', title: '斗破苍穹', totalChapters: 1200, status: 'analyzing' },
    ])

    vi.mocked(adminApi.assets).mockResolvedValue({
      total: 2,
      items: [
        { id: 'a1', name: '快节奏悬疑笔法', kind: 'voice' as const, path: '/a1', size: 1024, mtime: 123456 },
        { id: 'a2', name: '赛博朋克题材包', kind: 'genre_pack' as const, path: '/a2', size: 2048, mtime: 123456 },
      ],
    })

    vi.mocked(adminApi.audit).mockResolvedValue([
      { ts: '2026-10-17 12:00:00', username: 'admin', ip: '127.0.0.1', action: 'admin.login', detail: '成功登录' },
    ])

    vi.mocked(adminApi.sessions).mockResolvedValue([
      { id: 'sess-001', username: 'admin', ip: '127.0.0.1', createdAt: '2026-10-17 10:00:00', expiresAt: '2026-10-17 22:00:00', current: true },
      { id: 'sess-002', username: 'operator', ip: '127.0.0.1', createdAt: '2026-10-17 11:00:00', expiresAt: '2026-10-17 23:00:00', current: false },
    ])
  })

  it('未登录状态下以 zh-CN 渲染登录界面表单及说明', async () => {
    vi.mocked(adminApi.me).mockRejectedValue(new Error('unauthorized'))

    render(
      <I18nProvider initialLocale="zh-CN">
        <AdminWorkbench />
      </I18nProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('管理后台')).toBeInTheDocument()
    })

    expect(screen.getByText('ADMIN CONSOLE')).toBeInTheDocument()
    expect(screen.getByText(/后台管理仅限本机访问/)).toBeInTheDocument()
    expect(screen.getByLabelText('用户名')).toBeInTheDocument()
    expect(screen.getByLabelText('密码')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '登 录' })).toBeInTheDocument()
  })

  it('未登录状态下以 en-US 渲染登录界面表单及英文提示', async () => {
    vi.mocked(adminApi.me).mockRejectedValue(new Error('unauthorized'))

    render(
      <I18nProvider initialLocale="en-US">
        <AdminWorkbench />
      </I18nProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('Admin Console')).toBeInTheDocument()
    })

    expect(screen.getByText(/Console access is restricted to localhost/)).toBeInTheDocument()
    expect(screen.getByLabelText('Username')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign In' })).toBeInTheDocument()
  })

  it('登录成功后以 zh-CN 渲染六大面板 Tabs 与仪表盘数据', async () => {
    vi.mocked(adminApi.me).mockResolvedValue({ loggedIn: true, username: 'admin', mustChangePassword: false })

    render(
      <I18nProvider initialLocale="zh-CN">
        <AdminWorkbench />
      </I18nProvider>
    )

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: '仪表盘' })).toBeInTheDocument()
    })

    expect(screen.getByRole('tab', { name: '书库管理' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '资产管理' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '操作日志' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '会话管理' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: '安全设置' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '退出' })).toBeInTheDocument()

    // 仪表盘内容异步加载完成
    await waitFor(() => {
      expect(screen.getByText('系统仪表盘')).toBeInTheDocument()
    })
    expect(screen.getByText('书籍')).toBeInTheDocument()
    expect(screen.getByText('资产')).toBeInTheDocument()
    expect(screen.getByText('报告')).toBeInTheDocument()
    expect(screen.getByText('数据占用')).toBeInTheDocument()
    expect(screen.getByText('磁盘占用')).toBeInTheDocument()
    expect(screen.getByText('最近书籍')).toBeInTheDocument()
    expect(screen.getByText('最近操作')).toBeInTheDocument()
    expect(screen.getByText('1 本分析中')).toBeInTheDocument()
    expect(screen.getByText('运行 2 小时 2 分')).toBeInTheDocument()
  })

  it('以 en-US 渲染六大面板 Tabs、英文指标卡与各管理面板切换', async () => {
    vi.mocked(adminApi.me).mockResolvedValue({ loggedIn: true, username: 'admin', mustChangePassword: false })

    render(
      <I18nProvider initialLocale="en-US">
        <AdminWorkbench />
      </I18nProvider>
    )

    await waitFor(() => {
      expect(screen.getByRole('tab', { name: 'Dashboard' })).toBeInTheDocument()
    })

    expect(screen.getByRole('tab', { name: 'Books' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Assets' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Audit Logs' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Sessions' })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: 'Security' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Logout' })).toBeInTheDocument()

    // 英文仪表盘内容验证
    await waitFor(() => {
      expect(screen.getByText('System Dashboard')).toBeInTheDocument()
    })
    expect(screen.getAllByText('Books').length).toBeGreaterThanOrEqual(2)
    expect(screen.getAllByText('Assets').length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Reports')).toBeInTheDocument()
    expect(screen.getByText('Disk Usage')).toBeInTheDocument()
    expect(screen.getByText('1 analyzing')).toBeInTheDocument()
    expect(screen.getByText('Uptime 2h 2m')).toBeInTheDocument()

    // 切换至书库管理 (Books)
    fireEvent.click(screen.getByRole('tab', { name: 'Books' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Book Management/ })).toBeInTheDocument()
    })
    expect(screen.getByText('Title')).toBeInTheDocument()
    expect(screen.getByText('Chapters')).toBeInTheDocument()
    expect(screen.getByText('Status')).toBeInTheDocument()
    expect(screen.getByText('Actions')).toBeInTheDocument()
    expect(screen.getByText('宿命之环')).toBeInTheDocument()

    // 切换至资产管理 (Assets)
    fireEvent.click(screen.getByRole('tab', { name: 'Assets' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Asset Management/ })).toBeInTheDocument()
    })
    expect(screen.getByText('快节奏悬疑笔法')).toBeInTheDocument()
    expect(screen.getByText('Voice Cards')).toBeInTheDocument()

    // 切换至操作日志 (Audit Logs)
    fireEvent.click(screen.getByRole('tab', { name: 'Audit Logs' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Audit Logs/ })).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Filter by Action')).toBeInTheDocument()
    expect(screen.getByLabelText('Filter by User')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Filter' })).toBeInTheDocument()

    // 切换至在线会话 (Sessions)
    fireEvent.click(screen.getByRole('tab', { name: 'Sessions' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /Active Sessions/ })).toBeInTheDocument()
    })
    expect(screen.getByText('Session ID (Prefix)')).toBeInTheDocument()
    expect(screen.getByText('Created At')).toBeInTheDocument()
    expect(screen.getByText('Expires At')).toBeInTheDocument()
    expect(screen.getByText('Current')).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: 'Revoke' }).length).toBeGreaterThan(0)

    // 切换至安全设置 (Security)
    fireEvent.click(screen.getByRole('tab', { name: 'Security' }))
    await waitFor(() => {
      expect(screen.getByRole('heading', { name: 'Change Password' })).toBeInTheDocument()
    })
    expect(screen.getByLabelText('Current Password')).toBeInTheDocument()
    expect(screen.getByLabelText('New Password (at least 8 chars)')).toBeInTheDocument()
    expect(screen.getByLabelText('Confirm New Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Change Password' })).toBeInTheDocument()
    expect(screen.getByText('Security Specifications')).toBeInTheDocument()
    expect(screen.getByText(/Password stored with PBKDF2-HMAC-SHA256/)).toBeInTheDocument()
  })

  it('强制改密状态下显示警告条并锁定其他标签页', async () => {
    vi.mocked(adminApi.me).mockResolvedValue({ loggedIn: true, username: 'admin', mustChangePassword: true })

    render(
      <I18nProvider initialLocale="zh-CN">
        <AdminWorkbench />
      </I18nProvider>
    )

    await waitFor(() => {
      expect(screen.getByText('首次登录请立即修改初始密码，修改完成前其他功能不可用。')).toBeInTheDocument()
    })

    // 其他 Tab 应处于 disabled 状态
    expect(screen.getByRole('tab', { name: '仪表盘' })).toBeDisabled()
    expect(screen.getByRole('tab', { name: '书库管理' })).toBeDisabled()

    // 且当前 Tab 停留在安全设置
    expect(screen.getByRole('heading', { name: '修改密码' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '修改密码' })).toBeInTheDocument()
    expect(screen.getByLabelText('原密码')).toBeInTheDocument()
  })
})
