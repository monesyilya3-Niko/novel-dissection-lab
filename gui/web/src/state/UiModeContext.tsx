// UI 模式上下文：simple（简洁）/ advanced（进阶）双持久化。
//
// 设计（2026-10-28）：
// - 以 localStorage `novellab.ui.mode` 为主读（safeStorage 防御隐私模式抛错）。
// - 后端 settings.json 的 `ui.mode` 为备读（跨设备/清缓存恢复）；前端每次 setMode
//   时双写：先写 localStorage，再 best-effort PUT /api/system/settings {ui:{mode}}。
// - 新手推断：App 层根据 overview.totalBooks===0 && overview.totalAssets<5 计算
//   defaultMode 传入；若本地已有存储则以存储为准（用户显式偏好 wins）。
// - isHydrated 标志用于避免首帧闪烁或在存储未就绪时做分支渲染。

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { readStorage, writeStorage } from '../safeStorage'
import { systemApi } from '../api/client'

export type UIMode = 'simple' | 'advanced'

const STORAGE_KEY = 'novellab.ui.mode'

function isValidMode(v: unknown): v is UIMode {
  return v === 'simple' || v === 'advanced'
}

function readStored(): UIMode | null {
  const v = readStorage(STORAGE_KEY)
  return isValidMode(v) ? v : null
}

interface UiModeState {
  mode: UIMode
  setMode: (m: UIMode) => void
  isHydrated: boolean
}

const UiModeContext = createContext<UiModeState | null>(null)

export function UiModeProvider({
  children,
  defaultMode,
}: {
  children: ReactNode
  defaultMode?: UIMode
}) {
  const [mode, setModeState] = useState<UIMode>(() => readStored() ?? defaultMode ?? 'simple')
  const [isHydrated, setIsHydrated] = useState(false)

  // 当 overview 异步就绪后，若用户从未显式选择（无 localStorage 记录），
  // 则跟随 App 传入的 defaultMode（新手→simple）。已有存储的偏好始终优先。
  useEffect(() => {
    const stored = readStored()
    if (stored === null && defaultMode && mode !== defaultMode) {
      setModeState(defaultMode)
      writeStorage(STORAGE_KEY, defaultMode)
    }
  }, [defaultMode, mode])

  useEffect(() => {
    setIsHydrated(true)
  }, [])

  const setMode = useCallback((m: UIMode) => {
    if (!isValidMode(m)) return
    setModeState(m)
    writeStorage(STORAGE_KEY, m)
    // 双持久化：后端备存，失败静默（离线/未登录不阻断交互）
    systemApi.updateSettings({ ui: { mode: m } }).catch(() => {
      /* best-effort */
    })
  }, [])

  const value = useMemo<UiModeState>(() => ({ mode, setMode, isHydrated }), [mode, setMode, isHydrated])

  return <UiModeContext.Provider value={value}>{children}</UiModeContext.Provider>
}

export function useUiMode(): UiModeState {
  const ctx = useContext(UiModeContext)
  if (!ctx) throw new Error('useUiMode 必须在 UiModeProvider 内使用')
  return ctx
}

/** 可选版本：在 Provider 之外返回 null（供需跨 Provider 边界的工具使用）。 */
export function useUiModeOptional(): UiModeState | null {
  return useContext(UiModeContext)
}
