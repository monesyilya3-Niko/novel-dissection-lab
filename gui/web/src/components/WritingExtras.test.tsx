import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'
import WritingExtras from './WritingExtras'
import { I18nProvider } from '../state/I18nContext'
import { writeStorage, removeStorage } from '../safeStorage'

const mockOutlines = vi.fn()
const mockCharacters = vi.fn()
const mockNotes = vi.fn()
const mockStats = vi.fn()
const mockProjects = vi.fn()
const mockExport = vi.fn()

vi.mock('../api/client', () => ({
  writingApi: {
    projects: () => mockProjects(),
    outlines: (proj: string) => mockOutlines(proj),
    createOutline: vi.fn().mockResolvedValue({ id: 99, title: 'mocked' }),
    characters: (proj: string) => mockCharacters(proj),
    createCharacter: vi.fn().mockResolvedValue({ id: 99, name: 'mocked' }),
    notes: (proj: string) => mockNotes(proj),
    stats: (proj: string) => mockStats(proj),
    export: (proj: string, fmt: string) => mockExport(proj, fmt),
    analyzeTension: vi.fn().mockResolvedValue({
      segments: ['第1段'],
      tensionCurve: [50],
      benchmarkCurve: [50],
      benchmarkName: '经典标杆',
      climaxIndex: 0,
      climaxSegment: '第1段',
      maxTension: 50,
      avgTension: 50,
      tensionVariance: 0,
      benchmarkAlignmentScore: 85,
      flatZones: [],
      pacingFeedback: ['节奏良好'],
    }),
    analyzeGoldenThreeTension: vi.fn().mockResolvedValue({
      benchmark: 'classic',
      benchmarkName: '经典商业递进三章标杆',
      pointsPerChapter: 10,
      totalChapters: 3,
      totalChars: 3000,
      chaptersMetrics: [
        {
          chapterIndex: 1,
          charCount: 1000,
          segments: ['第1章第1段'],
          tensionCurve: [60],
          benchmarkCurve: [60],
          maxTension: 60,
          avgTension: 60,
          tensionVariance: 0,
          climaxIndex: 0,
          climaxSegment: '第1章第1段',
          openingScore: 60,
          hookScore: 65,
          flatZones: [],
          chapterVerdict: '黄金开局',
        },
      ],
      handoffs: [
        {
          fromChapter: 1,
          toChapter: 2,
          endTension: 65,
          startTension: 60,
          drop: 5,
          status: 'SMOOTH',
          comment: '承接平滑',
        },
      ],
      combinedCurve: [60],
      combinedBenchmarkCurve: [60],
      combinedAlignmentScore: 88,
      globalClimax: { chapterIndex: 1, segmentIndex: 1, maxTension: 60 },
      verdict: 'EXCELLENT',
      verdictTitle: '黄金三章成色：极佳',
      cliffhangerRating: 'STRONG',
      recommendations: ['节奏推进优异'],
    }),
    estimateReaderRetention: vi.fn().mockResolvedValue({
      benchmark: 'classic',
      benchmarkName: '经典商业递进三章标杆',
      pointsPerChapter: 10,
      totalChapters: 3,
      totalChars: 3000,
      retentionCurve: [100.0, 92.0, 88.0, 84.0],
      finalRetentionRate: 84.0,
      totalDropPct: 16.0,
      overallGrade: 'S',
      gradeDescription: '商业留存成色极佳',
      chaptersRetention: [
        {
          chapterIndex: 1,
          charCount: 1000,
          startRetention: 100.0,
          endRetention: 92.0,
          chapterChurnPct: 8.0,
          retentionRate: 92.0,
          hotspotsCount: 0,
          avgTension: 60,
          maxTension: 70,
        },
      ],
      dropoffHotspots: [
        {
          chapterIndex: 2,
          segmentIndex: 0,
          segmentLabel: '第2章第1段 (0-10%)',
          riskLevel: 'HIGH',
          estimatedDropPct: 6.5,
          reason: '承接前章张力骤降，引发失速',
          fixSuggestion: '章首快速回钩',
        },
      ],
      retentionAdvice: ['保持首章入局速度，中段补一次小高潮'],
    }),
  },
  toolsApi: {
    getHooks: vi.fn().mockResolvedValue({
      totalCount: 1,
      hooks: [
        {
          id: 'HK-001',
          name: '退婚逆袭',
          genre: 'xianxia',
          first300Words: '前300字钩子内容',
          chapter1Beat: '第一章节拍内容',
          chapter2Beat: '第二章节拍内容',
          chapter3Beat: '第三章节拍内容',
        },
      ],
    }),
    generateNames: vi.fn().mockResolvedValue({
      kind: 'character',
      style: 'xianxia',
      gender: 'all',
      count: 1,
      names: ['叶凌云'],
    }),
  },
  friendlyError: (e: unknown) => String(e),
}))

vi.mock('../state/ThemeModeContext', () => ({
  useThemeMode: () => ({ isDark: false }),
}))

vi.mock('./charts/CreationRateChart', () => ({
  default: () => <div data-testid="creation-rate-chart">CreationRateChart</div>,
}))
vi.mock('./charts/EmotionWaveChart', () => ({
  default: () => <div data-testid="emotion-wave-chart">EmotionWaveChart</div>,
}))
vi.mock('./charts/RhythmRadarChart', () => ({
  default: () => <div data-testid="rhythm-radar-chart">RhythmRadarChart</div>,
}))
vi.mock('./charts/ReaderRetentionChart', () => ({
  default: () => <div data-testid="reader-retention-chart">ReaderRetentionChart</div>,
}))

describe('WritingExtras 创作扩展工作台', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockProjects.mockResolvedValue([
      { id: 'p1', name: 'test-project', readOnly: false },
    ])
    mockOutlines.mockResolvedValue([
      { id: 1, project: 'test-project', kind: 'chapter', title: '第1章 惊变', summary: '主角觉醒', status: 'planned', sortOrder: 0, createdAt: '', updatedAt: '' },
    ])
    mockCharacters.mockResolvedValue([
      { id: 1, project: 'test-project', name: '林凡', role: '主角', description: '坚毅勇敢', extra: '{}', createdAt: '', updatedAt: '' },
    ])
    mockNotes.mockResolvedValue([
      { id: 1, project: 'test-project', title: '金手指伏笔', content: '古玉在第三章激活', createdAt: '', updatedAt: '' },
    ])
    mockStats.mockResolvedValue({
      totalWords: 5200,
      todayWords: 1200,
      streakDays: 3,
      totalChapters: 3,
      todayChapters: 1,
      history: [],
    })
  })

  it('无项目时提示先在写作页签新建项目', async () => {
    mockProjects.mockResolvedValueOnce([])
    render(<WritingExtras />)
    await waitFor(() => {
      expect(screen.getByText('请先在「写作」页签新建写作项目')).toBeInTheDocument()
    })
  })

  it('有项目时默认渲染项目标签页及大纲列表', async () => {
    render(<WritingExtras />)
    await waitFor(() => {
      expect(screen.getByText('大纲架构')).toBeInTheDocument()
      expect(screen.getByText('人物卡与关系')).toBeInTheDocument()
      expect(screen.getByText('灵感便签')).toBeInTheDocument()
      expect(screen.getByText('创作者仪表盘')).toBeInTheDocument()
      expect(screen.getByText('规范导出')).toBeInTheDocument()
    })

    // 默认展示大纲列表
    await waitFor(() => {
      expect(screen.getByText('第1章 惊变')).toBeInTheDocument()
    })
  })

  it('切换标签页到人物卡、便签、仪表盘与规范导出', async () => {
    render(<WritingExtras />)
    await waitFor(() => {
      expect(screen.getByText('大纲架构')).toBeInTheDocument()
    })

    // 切换到人物卡与关系
    fireEvent.click(screen.getByText('人物卡与关系'))
    await waitFor(() => {
      expect(screen.getByText('林凡')).toBeInTheDocument()
      expect(screen.getByText('坚毅勇敢')).toBeInTheDocument()
    })

    // 切换到灵感便签
    fireEvent.click(screen.getByText('灵感便签'))
    await waitFor(() => {
      expect(screen.getByText('金手指伏笔')).toBeInTheDocument()
      expect(screen.getByText('古玉在第三章激活')).toBeInTheDocument()
    })

    // 切换到创作者仪表盘
    fireEvent.click(screen.getByText('创作者仪表盘'))
    await waitFor(() => {
      expect(screen.getByText('全书总字数')).toBeInTheDocument()
      expect(screen.getByTestId('creation-rate-chart')).toBeInTheDocument()
      expect(screen.getByTestId('emotion-wave-chart')).toBeInTheDocument()
      expect(screen.getByTestId('rhythm-radar-chart')).toBeInTheDocument()
    })

    // 切换到规范导出
    fireEvent.click(screen.getByText('规范导出'))
    await waitFor(() => {
      expect(screen.getByText('导出全书作品')).toBeInTheDocument()
      expect(screen.getByText('导出 Word (.docx)')).toBeInTheDocument()
      expect(screen.getByText('导出 EPUB (.epub)')).toBeInTheDocument()
      expect(screen.getByText('导出 Shunn 文稿')).toBeInTheDocument()
      expect(screen.getByText('导出 Markdown (.md)')).toBeInTheDocument()
    })
  })

  it('在大纲架构中点击引用黄金三章模板并应用', async () => {
    render(<WritingExtras />)
    await waitFor(() => {
      expect(screen.getByText('大纲架构')).toBeInTheDocument()
    })

    const templateBtn = screen.getByText('🚀 引用黄金三章模板')
    fireEvent.click(templateBtn)

    await waitFor(() => {
      expect(screen.getByText('🚀 黄金三章开篇模型库')).toBeInTheDocument()
      expect(screen.getByText('一键应用为前三章大纲')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('一键应用为前三章大纲'))
  })

  it('在人物卡弹窗中点击随机名按钮自动填入名字', async () => {
    render(<WritingExtras />)
    await waitFor(() => {
      expect(screen.getByText('人物卡与关系')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('人物卡与关系'))
    await waitFor(() => {
      expect(screen.getByText('新建人物卡')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('新建人物卡'))
    await waitFor(() => {
      expect(screen.getByText('新建人物卡档案')).toBeInTheDocument()
      expect(screen.getByText('🎲 随机名')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('🎲 随机名'))
    await waitFor(() => {
      const nameInput = screen.getByLabelText('姓名') as HTMLInputElement
      expect(nameInput.value).toBe('叶凌云')
    })
  })

  it('在 en-US 语言环境下渲染英文项目标签、仪表盘与多格式导出卡片', async () => {
    writeStorage('novellab.locale', 'en-US')
    try {
      render(
        <I18nProvider>
          <WritingExtras />
        </I18nProvider>
      )

      await waitFor(() => {
        expect(screen.getByText('Outline & Structure')).toBeInTheDocument()
        expect(screen.getByText('Characters & Relations')).toBeInTheDocument()
        expect(screen.getByText('Inspiration Notes')).toBeInTheDocument()
        expect(screen.getByText('Creator Dashboard')).toBeInTheDocument()
        expect(screen.getByText('Manuscript Export')).toBeInTheDocument()
        expect(screen.getByText('Add Volume / Chapter')).toBeInTheDocument()
        expect(screen.getByText('🚀 First 3 Chapters Template')).toBeInTheDocument()
      })

      // 切换到 Characters & Relations
      fireEvent.click(screen.getByText('Characters & Relations'))
      await waitFor(() => {
        expect(screen.getByText('New Character Card')).toBeInTheDocument()
        expect(screen.getByText('林凡')).toBeInTheDocument()
      })

      // 切换到 Inspiration Notes
      fireEvent.click(screen.getByText('Inspiration Notes'))
      await waitFor(() => {
        expect(screen.getByText('Quick Note')).toBeInTheDocument()
        expect(screen.getByText('金手指伏笔')).toBeInTheDocument()
      })

      // 切换到 Creator Dashboard
      fireEvent.click(screen.getByText('Creator Dashboard'))
      await waitFor(() => {
        expect(screen.getByText('Creator Analytics Dashboard')).toBeInTheDocument()
        expect(screen.getByText("Today's Words")).toBeInTheDocument()
        expect(screen.getByText('Total Book Words')).toBeInTheDocument()
        expect(screen.getByText('Writing Streak')).toBeInTheDocument()
        expect(screen.getByText("Today's Chapters")).toBeInTheDocument()
        expect(screen.getByTestId('creation-rate-chart')).toBeInTheDocument()
      })

      // 切换到 Manuscript Export
      fireEvent.click(screen.getByText('Manuscript Export'))
      await waitFor(() => {
        expect(screen.getByText('Export Entire Book')).toBeInTheDocument()
        expect(screen.getByText('Export Word (.docx)')).toBeInTheDocument()
        expect(screen.getByText('Export EPUB (.epub)')).toBeInTheDocument()
        expect(screen.getByText('Export Shunn Manuscript')).toBeInTheDocument()
        expect(screen.getByText('Export Markdown (.md)')).toBeInTheDocument()
        expect(screen.getByText('Export Plain Text (.txt)')).toBeInTheDocument()
      })
    } finally {
      removeStorage('novellab.locale')
    }
  })

  it('黄金三章连环比对弹窗正常交互与示范数据载入', async () => {
    render(<WritingExtras />)
    await waitFor(() => {
      expect(screen.getByText('创作者仪表盘')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('创作者仪表盘'))

    await waitFor(() => {
      expect(screen.getByText('黄金三章连环比对')).toBeInTheDocument()
    })

    // 点击打开黄金三章比对弹窗
    fireEvent.click(screen.getByText('黄金三章连环比对'))

    await waitFor(() => {
      expect(screen.getByText('黄金三章张力曲线重叠比对')).toBeInTheDocument()
      expect(screen.getByText('载入示范三章范例')).toBeInTheDocument()
    })

    // 点击载入示范数据
    fireEvent.click(screen.getByText('载入示范三章范例'))

    await waitFor(() => {
      expect(screen.getByText('黄金三章成色：极佳')).toBeInTheDocument()
      expect(screen.getByText('黄金三章专家修改建议：')).toBeInTheDocument()
      expect(screen.getByText('节奏推进优异')).toBeInTheDocument()
    })
  })

  it('读者留存预测弹窗正常交互、示范载入与结果全景渲染', async () => {
    render(<WritingExtras />)
    await waitFor(() => {
      expect(screen.getByText('创作者仪表盘')).toBeInTheDocument()
    })
    fireEvent.click(screen.getByText('创作者仪表盘'))

    await waitFor(() => {
      expect(screen.getByText('读者留存预测')).toBeInTheDocument()
    })

    // 打开读者留存预测弹窗
    fireEvent.click(screen.getByText('读者留存预测'))

    await waitFor(() => {
      expect(screen.getByText('商业网文读者留存流失预测模型')).toBeInTheDocument()
      expect(screen.getByText('载入示范高留存三章 (S/A级)')).toBeInTheDocument()
      expect(screen.getByText('载入示范断崖失速三章 (高危跳出)')).toBeInTheDocument()
      expect(screen.getByText('开始读者留存测算')).toBeInTheDocument()
    })

    // 载入高留存示范并测算
    fireEvent.click(screen.getByText('载入示范高留存三章 (S/A级)'))

    await waitFor(() => {
      expect(screen.getByText('商业成色与读者留存全景')).toBeInTheDocument()
      expect(screen.getByTestId('reader-retention-chart')).toBeInTheDocument()
      expect(screen.getByText('综合评级 S · 商业留存成色极佳')).toBeInTheDocument()
      expect(screen.getByText('终局预计留存率: 84%')).toBeInTheDocument()
      expect(screen.getByText('累计流失漏斗: 16%')).toBeInTheDocument()
      expect(screen.getByText('弃读跳出高危风险点与挽留改法：')).toBeInTheDocument()
      expect(screen.getByText(/第2章第1段/)).toBeInTheDocument()
      expect(screen.getByText('战略防跳出与留存优化建议：')).toBeInTheDocument()
      expect(screen.getByText('保持首章入局速度，中段补一次小高潮')).toBeInTheDocument()
    })

    // 收起结果面板
    fireEvent.click(screen.getByText('关闭'))
    await waitFor(() => {
      expect(screen.queryByText('商业成色与读者留存全景')).not.toBeInTheDocument()
    })
  })
})

