import { describe, it, expect } from 'vitest'
import { setActiveLocale, tGlobal, getActiveLocale } from './translations'

describe('tGlobal 无 Context 翻译访问器（2026-11-02）', () => {
  it('默认中文', () => {
    setActiveLocale('zh-CN')
    expect(getActiveLocale()).toBe('zh-CN')
    expect(tGlobal('error_action_port_busy')).toMatch(/端口/)
  })

  it('切到英文后取英文文案', () => {
    setActiveLocale('en-US')
    expect(getActiveLocale()).toBe('en-US')
    expect(tGlobal('error_action_port_busy')).toMatch(/Port is busy/i)
    expect(tGlobal('error_action_file_too_large')).toMatch(/100MB/i)
  })

  it('未知 key 回落 fallback，再回落 key 本身', () => {
    setActiveLocale('zh-CN')
    expect(tGlobal('__not_exist__', '兜底')).toBe('兜底')
    expect(tGlobal('__not_exist__')).toBe('__not_exist__')
  })
})
