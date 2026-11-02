// 国际化语言 Context：zh-CN / en-US，localStorage 持久化。
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { readStorage, writeStorage } from '../safeStorage'
import { TRANSLATIONS, setActiveLocale, type Locale } from '../i18n/translations'
export type { Locale }

const STORAGE_KEY = 'novellab.locale'

export type TranslationParams = Record<string, string | number>

function interpolateParams(text: string, params?: TranslationParams): string {
  if (!params) return text
  let res = text
  for (const [k, v] of Object.entries(params)) {
    res = res.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v))
  }
  return res
}

interface I18nState {
  locale: Locale
  setLocale: (l: Locale) => void
  toggleLocale: () => void
  t: (key: string, fallback?: string, params?: TranslationParams) => string
}

const I18nContext = createContext<I18nState | null>(null)

function readStoredLocale(): Locale {
  const v = readStorage(STORAGE_KEY)
  return v === 'en-US' || v === 'zh-CN' ? v : 'zh-CN'
}

export function I18nProvider({
  children,
  initialLocale,
}: {
  children: ReactNode
  initialLocale?: Locale
}) {
  const [locale, setLocaleState] = useState<Locale>(() => initialLocale ?? readStoredLocale())
  // prop 变化时同步（供测试/嵌入方切换 initialLocale）。用「渲染期比对上一次的 prop」
  // 而不是 effect + setState：后者会多渲染一帧，并被 react-hooks 判为 cascading render。
  // 手动切换语言不受影响——该分支只在 initialLocale 这个 prop 真的变了才触发。
  const [lastInitialLocale, setLastInitialLocale] = useState(initialLocale)
  if (initialLocale !== lastInitialLocale) {
    setLastInitialLocale(initialLocale)
    if (initialLocale) {
      setLocaleState(initialLocale)
    }
  }

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l)
    writeStorage(STORAGE_KEY, l)
  }, [])

  const toggleLocale = useCallback(() => {
    const next: Locale = locale === 'zh-CN' ? 'en-US' : 'zh-CN'
    setLocale(next)
  }, [locale, setLocale])

  // 把当前语言同步到模块级快照，供 api/client.ts 等纯函数读取。
  // 放在 useState 之后、t 定义之前，保证同一次渲染里 friendlyError 看到的是新语言。
  setActiveLocale(locale)

  const t = useCallback(
    (key: string, fallback?: string, params?: TranslationParams): string => {
      const entry = TRANSLATIONS[key]
      const raw = entry && entry[locale] !== undefined ? entry[locale] : (fallback ?? key)
      return interpolateParams(raw, params)
    },
    [locale],
  )

  const value = useMemo<I18nState>(
    () => ({ locale, setLocale, toggleLocale, t }),
    [locale, setLocale, toggleLocale, t],
  )

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

export function useI18n(): I18nState {
  const ctx = useContext(I18nContext)
  if (!ctx) {
    // 降级兜底：在未挂载 Provider 的隔离单测中提供安全 fallback
    return {
      locale: 'zh-CN',
      setLocale: () => {},
      toggleLocale: () => {},
      t: (key: string, fallback?: string, params?: TranslationParams) => {
        const entry = TRANSLATIONS[key]
        const raw = entry && entry['zh-CN'] !== undefined ? entry['zh-CN'] : (fallback ?? key)
        return interpolateParams(raw, params)
      },
    }
  }
  return ctx
}
