import { describe, expect, it } from 'vitest'
import { TRANSLATIONS } from './translations'

describe('TRANSLATIONS 国际化双语词典对齐与完整性校验', () => {
  const entries = Object.entries(TRANSLATIONS)

  it('词典收录超过 300 条中英文双语词条', () => {
    expect(entries.length).toBeGreaterThan(300)
  })

  it('每个词条必须同时包含合法的 zh-CN 与 en-US 字符串（除 analysis_chap_suffix 英文后置为空外全量非空）', () => {
    const missing: string[] = []

    for (const [key, val] of entries) {
      if (typeof val['zh-CN'] !== 'string' || val['zh-CN'].trim() === '') {
        missing.push(`Key "${key}" 缺失或空的 zh-CN`)
      }
      if (typeof val['en-US'] !== 'string') {
        missing.push(`Key "${key}" 缺失 en-US`)
      } else if (val['en-US'].trim() === '' && key !== 'analysis_chap_suffix') {
        missing.push(`Key "${key}" en-US 意外为空字符串`)
      }
    }

    expect(missing).toEqual([])
  })

  it('双语词条中的动态参数插值占位符 {param} 必须完全对齐', () => {
    const paramRegex = /\{([a-zA-Z0-9_]+)\}/g
    const mismatches: string[] = []

    for (const [key, val] of entries) {
      const zhParams = new Set(Array.from(val['zh-CN'].matchAll(paramRegex), (m) => m[1]))
      const enParams = new Set(Array.from(val['en-US'].matchAll(paramRegex), (m) => m[1]))

      // 比较两语言的参数集合
      const diff1 = [...zhParams].filter((p) => !enParams.has(p))
      const diff2 = [...enParams].filter((p) => !zhParams.has(p))

      if (diff1.length > 0 || diff2.length > 0) {
        mismatches.push(
          `Key "${key}" 参数不一致: zh-CN 含有 [${[...zhParams].join(', ')}], en-US 含有 [${[...enParams].join(', ')}]`,
        )
      }
    }

    expect(mismatches).toEqual([])
  })

  it('词条中不存在未闭合的花括号单侧语法错误', () => {
    const broken: string[] = []
    const singleBrace = /\{[^}]*$/

    for (const [key, val] of entries) {
      if (singleBrace.test(val['zh-CN'])) {
        broken.push(`Key "${key}" zh-CN 存在未闭合的花括号`)
      }
      if (singleBrace.test(val['en-US'])) {
        broken.push(`Key "${key}" en-US 存在未闭合的花括号`)
      }
    }

    expect(broken).toEqual([])
  })

  it('核心品牌与基石标识中英对照严格符合系统定义', () => {
    expect(TRANSLATIONS.brand_name['zh-CN']).toBe('暮冬念春')
    expect(TRANSLATIONS.brand_name['en-US']).toBe('Exoscribe')

    expect(TRANSLATIONS.brand_subtitle['zh-CN']).toBe('全功能工作台')
    expect(TRANSLATIONS.brand_subtitle['en-US']).toBe('The Vernal Engine for Fiction')

    expect(TRANSLATIONS.brand_initial['zh-CN']).toBe('暮')
    expect(TRANSLATIONS.brand_initial['en-US']).toBe('E')

    expect(TRANSLATIONS.nav_home['zh-CN']).toBe('首页')
    expect(TRANSLATIONS.nav_home['en-US']).toBe('Home')
  })
})
