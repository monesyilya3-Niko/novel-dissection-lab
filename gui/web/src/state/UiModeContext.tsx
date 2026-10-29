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

  // 当 overview 异步就绪后，若用户从未显式选择（无 localStorage 记录），
  // 则跟随 App 传入的 defaultMode（新手→simple）。
  //
  // 关键：这里**不能**把 defaultMode 写进 localStorage。推断值只是初始展示，
  // 用户一旦自己切过一次才算显式偏好。若在此写入，新手会被永久钉在 simple，
  // 后来即使有了书也再回不到 advanced（推断逻辑再也无法生效）。
  // 2026-10-29 实测确认这是真实缺陷；同时该 effect 里的 setState 也是
  // react-hooks 报的 cascading render 来由。
  const [lastDefault, setLastDefault] = useState<UIMode | undefined>(defaultMode)
  if (defaultMode !== lastDefault) {
    // 渲染期同步跟随（React 官方推荐用「派生 state 比对」代替 effect + setState）
    setLastDefault(defaultMode)
    if (defaultMode && readStored() === null && mode !== defaultMode) {
      setModeState(defaultMode)
    }
  }

  const setMode = useCallback((m: UIMode) => {
    if (!isValidMode(m)) return
    setModeState(m)
    writeStorage(STORAGE_KEY, m)
    // 双持久化：后端备存，失败静默（离线/未登录不阻断交互）
    systemApi.updateSettings({ ui: { mode: m } }).catch(() => {
      /* best-effort */
    })
  }, [])

  const value = useMemo<UiModeState>(
    () => ({ mode, setMode, isHydrated: true }),
    [mode, setMode],
  )

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
