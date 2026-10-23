import { describe, expect, it } from 'vitest'
import {
  palette,
  chartSeries,
  buildMuiTheme,
  chartTextStyle,
  chartDefaults,
} from './theme'
import { ink, fontStack } from './ink'

describe('theme 主题系统与色板测试', () => {
  it('基础色板定义符合「墨」设计系统标准', () => {
    expect(palette.primary).toBe(ink.cinnabar)
    expect(palette.success).toBe(ink.teal)
    expect(palette.consistency).toBe(ink.cinnabar)
    expect(palette.quality).toBe(ink.teal)
    expect(palette.chartSeriesLight.length).toBe(8)
    expect(palette.chartSeriesDark.length).toBe(8)
  })

  it('chartSeries 根据暗色模式返回对应色板数组', () => {
    expect(chartSeries(false)).toBe(palette.chartSeriesLight)
    expect(chartSeries(true)).toBe(palette.chartSeriesDark)
  })

  it('buildMuiTheme 构建浅色模式主题配置', () => {
    const lightTheme = buildMuiTheme(false)

    expect(lightTheme.palette.mode).toBe('light')
    expect(lightTheme.palette.primary.main).toBe(ink.cinnabar)
    expect(lightTheme.palette.text.primary).toBe(ink.ink)
    expect(lightTheme.palette.text.secondary).toBe(ink.inkSoft)
    expect(lightTheme.palette.text.disabled).toBe(ink.inkFaint)
    expect(lightTheme.palette.divider).toBe(ink.line)
    expect(lightTheme.palette.background).toEqual({
      default: ink.paper,
      paper: ink.card,
    })
    expect(lightTheme.shape.borderRadius).toBe(12)
    expect(lightTheme.typography.fontFamily).toBe(fontStack.sans)
    expect(lightTheme.typography.h1.fontFamily).toBe(fontStack.serif)
    expect(lightTheme.components.MuiCard.styleOverrides.root.border).toContain(ink.line)
    expect(lightTheme.components.MuiButton.styleOverrides.root.textTransform).toBe('none')
  })

  it('buildMuiTheme 构建深色模式主题配置', () => {
    const darkTheme = buildMuiTheme(true)

    expect(darkTheme.palette.mode).toBe('dark')
    expect(darkTheme.palette.primary.main).toBe(ink.cinnabar)
    expect(darkTheme.palette.text.primary).toBe(ink.moonWhite)
    expect(darkTheme.palette.text.secondary).toBe(ink.moonSoft)
    expect(darkTheme.palette.text.disabled).toBe('#6B655A')
    expect(darkTheme.palette.divider).toBe(ink.nightLine)
    expect(darkTheme.palette.background).toEqual({
      default: ink.night,
      paper: ink.nightCard,
    })
    expect(darkTheme.components.MuiCard.styleOverrides.root.border).toContain(ink.nightLine)
  })

  it('chartTextStyle 与 chartDefaults 返回与模式对齐的图表默认配置', () => {
    const lightStyle = chartTextStyle(false)
    expect(lightStyle.color).toBe(ink.inkSoft)
    expect(lightStyle.fontFamily).toBe(fontStack.sans)

    const darkStyle = chartTextStyle(true)
    expect(darkStyle.color).toBe(ink.moonSoft)
    expect(darkStyle.fontFamily).toBe(fontStack.sans)

    const lightDefaults = chartDefaults(false)
    expect(lightDefaults.textStyle).toEqual(lightStyle)
    expect(lightDefaults.color).toEqual([...palette.chartSeriesLight])

    const darkDefaults = chartDefaults(true)
    expect(darkDefaults.textStyle).toEqual(darkStyle)
    expect(darkDefaults.color).toEqual([...palette.chartSeriesDark])
  })
})
