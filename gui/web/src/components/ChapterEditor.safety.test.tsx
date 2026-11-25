import { act, render } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ChapterEditor from './ChapterEditor'

const mocks = vi.hoisted(() => ({
  options: null as null | {
    onUpdate: (event: { editor: unknown }) => void
  },
  editor: {
    isDestroyed: false,
    state: { doc: null as unknown },
    storage: { characterCount: { characters: () => 2 } },
    getText: vi.fn(() => '真稿'),
    commands: {
      clearContent: vi.fn(),
      setContent: vi.fn(),
    },
  },
}))

vi.mock('@tiptap/react', () => ({
  useEditor: (options: typeof mocks.options) => {
    mocks.options = options
    return mocks.editor
  },
  EditorContent: () => <div data-testid="editor-content" />,
}))

vi.mock('../api/client', () => ({
  toolsApi: { checkPoison: vi.fn() },
  writingApi: { deslop: vi.fn() },
  essenceApi: { checkConstitution: vi.fn() },
  friendlyError: (e: unknown) => String(e),
}))

describe('ChapterEditor 读取安全', () => {
  beforeEach(() => {
    mocks.options = null
    mocks.editor.isDestroyed = false
    mocks.editor.state = { doc: {} }
    mocks.editor.getText.mockReset().mockReturnValue('真稿')
    mocks.editor.commands.clearContent.mockClear()
    mocks.editor.commands.setContent.mockClear()
  })

  it.each([
    ['编辑器已销毁', () => { mocks.editor.isDestroyed = true }],
    ['state.doc 缺失', () => { mocks.editor.state = { doc: null } }],
    ['getText 抛错', () => { mocks.editor.getText.mockImplementation(() => { throw new Error('destroyed') }) }],
  ])('%s 时不把正文同步为空串', (_label, breakEditor) => {
    const onChange = vi.fn()
    breakEditor()
    render(<ChapterEditor value="真稿" onChange={onChange} />)

    act(() => mocks.options?.onUpdate({ editor: mocks.editor }))

    expect(onChange).not.toHaveBeenCalled()
    expect(mocks.editor.commands.clearContent).not.toHaveBeenCalled()
    expect(mocks.editor.commands.setContent).not.toHaveBeenCalled()
  })

  it('合法空正文仍正常同步为清空', () => {
    const onChange = vi.fn()
    mocks.editor.getText.mockReturnValue('')
    render(<ChapterEditor value="真稿" onChange={onChange} />)

    act(() => mocks.options?.onUpdate({ editor: mocks.editor }))

    expect(onChange).toHaveBeenCalledWith('')
  })
})
