import { describe, expect, it } from 'vitest'
import {
  inkPaletteLight,
  inkPaletteDark,
  getInkPalette,
  inkTextStyle,
  inkTooltip,
} from './inkPalette'
import { ink } from '../ink'

describe('inkPalette 墨色系图表配色与 ECharts 样式工具测试', () => {
  it('浅色图表色板 inkPaletteLight 定义 8 色且首色为主强调点缀色', () => {
    expect(inkPaletteLight).toHaveLength(8)
    expect(inkPaletteLight[0]).toBe(ink.cinnabar)
    expect(inkPaletteLight[1]).toBe(ink.teal)
    expect(inkPaletteLight[2]).toBe(ink.gold)
    // 包含经典国风/墨色扩展：黛蓝、赭石、苔绿、紫苑、陶土
    expect(inkPaletteLight[3]).toBe('#3A7CA5')
    expect(inkPaletteLight[4]).toBe('#8A6D3B')
  })

  it('暗色图表色板 inkPaletteDark 定义 8 色且进行夜读提亮', () => {
    expect(inkPaletteDark).toHaveLength(8)
    expect(inkPaletteDark[0]).toBe('#E06C5B')
    expect(inkPaletteDark[1]).toBe('#4DB6A0')
    expect(inkPaletteDark[2]).toBe(ink.goldBright)
    expect(inkPaletteDark[3]).toBe('#6BA3C7')
    expect(inkPaletteDark[4]).toBe('#C9A86A')
  })

  it('getInkPalette 按 isDark 参数准确选择对应色板', () => {
    expect(getInkPalette(false)).toBe(inkPaletteLight)
    expect(getInkPalette(true)).toBe(inkPaletteDark)
  })

  it('inkTextStyle 生成符合 MUI 字体栈与主题对比度的文本样式', () => {
    const lightStyle = inkTextStyle(false)
    expect(lightStyle.fontSize).toBe(12)
    expect(lightStyle.fontFamily).toContain('Noto Sans SC')
    expect(lightStyle.color).toBe(ink.inkSoft)

    const darkStyle = inkTextStyle(true)
    expect(darkStyle.fontSize).toBe(12)
    expect(darkStyle.color).toBe(ink.moonSoft)
  })

  it('inkTooltip 生成墨纸质感的高对比度浮层提示框配置', () => {
    const lightTip = inkTooltip(false)
    expect(lightTip.backgroundColor).toBe(ink.card)
    expect(lightTip.borderColor).toBe(ink.line)
    expect(lightTip.borderWidth).toBe(1)
    expect(lightTip.textStyle.color).toBe(ink.ink)
    expect(lightTip.textStyle.fontSize).toBe(12)
    expect(lightTip.extraCssText).toContain('box-shadow')
    expect(lightTip.extraCssText).toContain('border-radius: 8px')

    const darkTip = inkTooltip(true)
    expect(darkTip.backgroundColor).toBe(ink.nightCard)
    expect(darkTip.borderColor).toBe(ink.nightLine)
    expect(darkTip.textStyle.color).toBe(ink.moonWhite)
  })
})
