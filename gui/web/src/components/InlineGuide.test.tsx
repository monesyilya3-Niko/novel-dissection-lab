import { render, screen, fireEvent } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import InlineGuide from './InlineGuide'
import { I18nProvider } from '../state/I18nContext'

describe('InlineGuide 就地功能说明双语国际化与交互测试', () => {
  it('zh-CN 环境下折叠与展开功能说明', () => {
    render(
      <I18nProvider initialLocale="zh-CN">
        <InlineGuide
          what="这是一个测试功能的一句话说明"
          steps={['步骤一：配置参数', '步骤二：点击运行']}
          tips={['注意：运行期间请勿关闭页面']}
          example="示例输入：主角在风雪中抵达客栈"
        />
      </I18nProvider>
    )

    // 默认展示一句话
    expect(screen.getByText('这是一个测试功能的一句话说明')).toBeInTheDocument()

    // 展开按钮 aria-label 默认为"展开说明"
    const toggleBtn = screen.getByRole('button', { name: '展开说明' })
    expect(toggleBtn).toBeInTheDocument()

    // 点击展开
    fireEvent.click(toggleBtn)
    expect(screen.getByRole('button', { name: '收起说明' })).toBeInTheDocument()
    expect(screen.getByText('步骤一：配置参数')).toBeInTheDocument()
    expect(screen.getByText('步骤二：点击运行')).toBeInTheDocument()
    expect(screen.getByText(/注意：运行期间请勿关闭页面/)).toBeInTheDocument()
    expect(screen.getByText('示例')).toBeInTheDocument()
    expect(screen.getByText('示例输入：主角在风雪中抵达客栈')).toBeInTheDocument()
  })

  it('en-US 环境下展示英文 aria-label 与示例标识', () => {
    render(
      <I18nProvider initialLocale="en-US">
        <InlineGuide
          what="One-line summary of what this tool does"
          steps={['Step 1: Set parameters', 'Step 2: Click run']}
          example="Example input: The hero arrives at the inn in a blizzard"
          defaultOpen={true}
        />
      </I18nProvider>
    )

    // 默认展开状态下 aria-label 为 Collapse guide
    expect(screen.getByRole('button', { name: 'Collapse guide' })).toBeInTheDocument()
    expect(screen.getByText('Example')).toBeInTheDocument()
    expect(screen.getByText('Example input: The hero arrives at the inn in a blizzard')).toBeInTheDocument()
  })
})
