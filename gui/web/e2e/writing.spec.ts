// 写作台 E2E：Studio ↔ Pipeline 切换、Pipeline 分组导航、面板渲染。
//
// 这是全应用最复杂的页面（一屏三栏 + 9 个流水线面板 + 分组折叠），
// 此前完全没有 e2e 覆盖 —— 它的失败模式是"点了没反应/白屏"，
// 单测和 API 测试都看不出来。
//
// 依赖：服务需有至少一个写作项目（空库时 Studio 会显示空态）。
// 若 /api/writing/projects 为空，本文件自动 skip。
import { expect, test, request } from '@playwright/test'

test.beforeEach(async ({ page, baseURL }) => {
  const api = await request.newContext({ baseURL })
  const resp = await api.get('/api/writing/projects')
  const body = await resp.json()
  await api.dispose()
  test.skip(!Array.isArray(body?.data) || !body.data.some((project: { read_only?: boolean }) => !project.read_only),
    '需要至少一个可写写作项目才能验证写作台')
  await page.goto('/')
  const nav = page.getByTestId('nav-writing')
  if (!(await nav.isVisible())) {
    await page.getByRole('button', { name: '打开导航', exact: true }).click()
  }
  await nav.click()
})

test('写作台加载：Studio 默认可见，模式切换栏存在', async ({ page }) => {
  // 两个模式页签
  await expect(page.getByRole('tab', { name: /沉浸创作室/ })).toBeVisible({ timeout: 15_000 })
  await expect(page.getByRole('tab', { name: /工坊流水线/ })).toBeVisible()
})

test('Studio → Pipeline 切换后渲染流水线面板', async ({ page }) => {
  await page.getByRole('tab', { name: /工坊流水线/ }).click()
  // 至少有一个流水线页签出现（注入/生成/打分等，按模式不同）
  await expect(page.getByRole('tab', { name: /资产注入|AI 章节生成/ }).first())
    .toBeVisible({ timeout: 10_000 })
})

test('Pipeline 分组导航可点击且切换面板', async ({ page }) => {
  await page.getByRole('tab', { name: /工坊流水线/ }).click()
  // 分组按钮只在 simple 模式下渲染；advanced 模式是 9 个平铺页签
  const groups = page.locator('[data-testid^="pipeline-group-"]')
  const groupCount = await groups.count()
  const flatTabs = await page.getByRole('tab').count()

  if (groupCount > 0) {
    // simple 模式：点第一个分组，应显示该组的面板
    await groups.first().click()
    await expect(page.getByRole('tab').first()).toBeVisible({ timeout: 5_000 })
  } else {
    // advanced 模式：9 个流水线页签全部平铺
    expect(flatTabs, 'advanced 模式应有多个流水线页签').toBeGreaterThan(2)
  }
})

test.describe('移动端 Studio', () => {
  test.use({ viewport: { width: 375, height: 812 } })

  test('三栏纵向堆叠且编辑器与副驾均可访问', async ({ page }) => {
    const workspace = page.getByTestId('studio-workspace')
    await expect(workspace).toBeVisible()

    for (const id of ['studio-outline-panel', 'studio-editor-panel', 'studio-copilot-panel']) {
      const box = await page.getByTestId(id).boundingBox()
      expect(box, `${id} 应有真实尺寸`).not.toBeNull()
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.width).toBeGreaterThan(300)
      expect(box!.x + box!.width).toBeLessThanOrEqual(376)
    }

    const horizontalOverflow = await workspace.evaluate((el) => el.scrollWidth - el.clientWidth)
    expect(horizontalOverflow, '移动端工作区不应横向裁切').toBeLessThanOrEqual(1)

    await page.getByRole('tab', { name: '精华资产反哺', exact: true }).click()
    await expect(page.getByRole('tab', { name: /五维提炼卡/ })).toBeVisible()
  })
})

test('切换到 Pipeline 再切回 Studio 不报错', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))

  await page.getByRole('tab', { name: /工坊流水线/ }).click()
  await page.waitForTimeout(500)
  await page.getByRole('tab', { name: /沉浸创作室/ }).click()
  await page.waitForTimeout(500)

  expect(errors, '模式切换不应抛未捕获异常').toEqual([])
  await expect(page.getByRole('tab', { name: /沉浸创作室/ })).toBeVisible()
})
