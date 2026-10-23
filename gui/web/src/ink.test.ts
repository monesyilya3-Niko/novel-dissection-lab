import { describe, expect, it } from 'vitest'
import {
  ink,
  fontStack,
  card,
  glassCard,
  ambientGradient,
  cardHover,
  fadeUp,
  stagger,
} from './ink'

describe('ink 墨水设计系统视觉 Token 与样式工厂测试', () => {
  it('定义完备的 v4 简约白语义色板', () => {
    expect(ink.bg).toBe('#F7F7F8')
    expect(ink.surface).toBe('#FFFFFF')
    expect(ink.surfaceDeep).toBe('#F1F1F4')
    expect(ink.text).toBe('#18181B')
    expect(ink.textSecondary).toBe('#52525B')
    expect(ink.textTertiary).toBe('#A1A1AA')
    expect(ink.hairline).toBe('#E9E9EC')
    expect(ink.primary).toBe('#18181B')
    expect(ink.primaryHover).toBe('#000000')
    expect(ink.primarySoft).toBe('#F4F4F5')
    expect(ink.accent).toBe('#2563EB')
    expect(ink.accentHover).toBe('#1D4ED8')
    expect(ink.accentSoft).toBe('#EFF4FF')
    expect(ink.success).toBe('#16A34A')
    expect(ink.warning).toBe('#B45309')
    expect(ink.error).toBe('#DC2626')
  })

  it('保留 v3 兼容别名且正确映射到新语义值', () => {
    expect(ink.paper).toBe(ink.surface)
    expect(ink.card).toBe(ink.surface)
    expect(ink.ink).toBe(ink.text)
    expect(ink.inkSoft).toBe(ink.textSecondary)
    expect(ink.inkFaint).toBe(ink.textTertiary)
    expect(ink.line).toBe(ink.hairline)
    expect(ink.cinnabar).toBe(ink.accent)
    expect(ink.gold).toBe(ink.warning)
  })

  it('暗色模式夜读色板保持高可读性与低眩光', () => {
    expect(ink.night).toBe('#0B0B0D')
    expect(ink.nightCard).toBe('#141417')
    expect(ink.nightLine).toBe('#26262B')
    expect(ink.moonWhite).toBe('#FAFAFA')
    expect(ink.moonSoft).toBe('#A3A3AD')
  })

  it('字体栈规范覆盖衬线、非衬线与等宽字体', () => {
    expect(fontStack.serif).toContain('Noto Serif SC')
    expect(fontStack.sans).toContain('Inter')
    expect(fontStack.mono).toContain('JetBrains Mono')
  })

  it('card 标准卡片样式结构正确', () => {
    expect(card.backgroundColor).toBe('#FFFFFF')
    expect(card.border).toBe('1px solid #E9E9EC')
    expect(card.borderRadius).toBe(12)
    expect(card.boxShadow).toBeDefined()
  })

  it('glassCard 玻璃拟态根据亮暗模式计算毛玻璃背景与透明度边框', () => {
    const lightGlass = glassCard(false)
    expect(lightGlass.backdropFilter).toBe('blur(16px)')
    expect(lightGlass.backgroundColor).toContain('rgba(255, 255, 255')
    expect(lightGlass.border).toContain('rgba(0, 0, 0, 0.06)')
    expect(lightGlass.borderRadius).toBe(14)

    const darkGlass = glassCard(true)
    expect(darkGlass.backdropFilter).toBe('blur(16px)')
    expect(darkGlass.backgroundColor).toContain('rgba(20, 20, 23')
    expect(darkGlass.border).toContain('rgba(255, 255, 255, 0.08)')
    expect(darkGlass.borderRadius).toBe(14)
  })

  it('ambientGradient 氛围渐变根据亮暗模式生成径向渐变网格', () => {
    const lightGrad = ambientGradient(false)
    expect(lightGrad).toContain('radial-gradient')
    expect(lightGrad).toContain('rgba(37, 99, 235')

    const darkGrad = ambientGradient(true)
    expect(darkGrad).toContain('radial-gradient')
    expect(darkGrad).toContain('rgba(5, 150, 105')
  })

  it('cardHover 包含平滑微动过渡与阴影扩散属性', () => {
    expect(cardHover.transition).toContain('cubic-bezier')
    expect(cardHover['&:hover'].transform).toBe('translateY(-2px)')
    expect(cardHover['&:hover'].boxShadow).toContain('rgba(16, 16, 20')
  })

  it('fadeUp 与 stagger 动效计算正确的延迟与上限截断', () => {
    expect(fadeUp.animation).toContain('fadeUp 0.4s')
    expect(fadeUp['@keyframes fadeUp']).toBeDefined()

    // index = 0 -> delay = 0s
    const s0 = stagger(0)
    expect(s0.animationDelay).toBe('0s')

    // index = 5 -> delay = 0.25s
    const s5 = stagger(5, 0.05)
    expect(s5.animationDelay).toBe('0.25s')

    // index = 20 (20 * 0.05 = 1.0s) -> 截断在最大 0.5s
    const s20 = stagger(20, 0.05)
    expect(s20.animationDelay).toBe('0.5s')
  })
})
