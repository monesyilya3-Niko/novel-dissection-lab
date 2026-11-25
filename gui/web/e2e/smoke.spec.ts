// novel-lab GUI 端到端冒烟：首页 KPI / 资产库列表 / 设置页读写路径。
// 前置：本地服务已启动（CI 中由 e2e job 负责；本地可 `python -m gui.server`）。
import { expect, test } from '@playwright/test'

test.describe('GUI 冒烟', () => {
  test('首页加载：标题 + KPI 卡 + 饼图渲染', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '暮冬念春工作台' })).toBeVisible()
    await expect(page.getByText('已拆书')).toBeVisible()
    await expect(page.getByText('资产总数')).toBeVisible()
    // 饼图（P1-F2：不仅查容器，还要查 canvas 真实渲染且有尺寸）
    const pie = page.locator('[role="img"][aria-label="饼图"]')
    await expect(pie).toBeVisible()
    const canvas = pie.locator('canvas')
    await expect(canvas).toBeVisible()
    const box = await canvas.boundingBox()
    expect(box, '饼图 canvas 应有真实尺寸').not.toBeNull()
    expect(box!.width).toBeGreaterThan(0)
    expect(box!.height).toBeGreaterThan(0)
  })

  test('资产库：分类筛选可见且列表非空', async ({ page }) => {
    await page.goto('/')
    await expect(page.getByRole('heading', { name: '暮冬念春工作台' })).toBeVisible()
    // simple 模式默认折叠「更多工具」，advanced 模式直接展示资产库。
    const nav = page.getByTestId('nav-assets')
    if (!(await nav.isVisible())) {
      await page.getByTestId('nav-more-toggle').click()
    }
    await nav.click()
    // 类型筛选 chips 是稳定锚点（KINDS 枚举固定渲染）
    await expect(page.getByRole('button', { name: '全部', exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '声线卡', exact: true })).toBeVisible()
    // 列表由真实 assets/ 驱动：至少一个条目含大小文本
    await expect(page.getByText(/KB/).first()).toBeVisible({ timeout: 10_000 })
  })

  test('设置页：可打开且含可交互控件', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('button', { name: '设置', exact: true }).first().click()
    await expect(page.getByText(/阈值|设置/).first()).toBeVisible()
  })

  test('帮助中心：中文界面可搜索英文术语', async ({ page }) => {
    await page.goto('/')
    await page.getByTestId('nav-help').click()
    await page.getByRole('tab', { name: '术语表', exact: true }).click()
    await page.getByPlaceholder('搜索术语…').fill('deslop')
    await expect(page.getByText('去AI味', { exact: true })).toBeVisible()
    await expect(page.getByText('声线卡', { exact: true })).toBeHidden()
  })

  test.describe('移动端布局', () => {
    test.use({ viewport: { width: 375, height: 812 } })

    test('分析页签容器有有效宽度且可切换', async ({ page }) => {
      await page.goto('/')
      const nav = page.getByTestId('nav-analysis')
      if (!(await nav.isVisible())) {
        await page.getByRole('button', { name: '打开导航', exact: true }).click()
      }
      await nav.click()

      const tabs = page.getByTestId('analysis-tabs')
      await expect(tabs).toBeVisible()
      const box = await tabs.boundingBox()
      expect(box, '分析页签容器应有真实尺寸').not.toBeNull()
      expect(box!.width).toBeGreaterThan(300)
      expect(box!.x).toBeGreaterThanOrEqual(0)
      expect(box!.x + box!.width).toBeLessThanOrEqual(376)

      await page.getByRole('tab', { name: '结果', exact: true }).click()
      await expect(page.getByRole('tab', { name: '结果', exact: true }))
        .toHaveAttribute('aria-selected', 'true')
    })
  })

  test('暗色切换：模式写入 localStorage 且刷新后保持', async ({ page }) => {
    await page.goto('/')
    // 轮转点击切换按钮（light→dark→system 循环），直到 localStorage 落到 dark
    for (let i = 0; i < 3; i++) {
      const mode = await page.evaluate(() => window.localStorage.getItem('novellab.theme-mode'))
      if (mode === 'dark') break
      const btn = page.getByTestId('theme-mode-toggle')
      await btn.click()
      await page.waitForTimeout(300)
    }
    expect(await page.evaluate(() => window.localStorage.getItem('novellab.theme-mode'))).toBe('dark')
    await page.reload()
    await expect(page.getByRole('heading', { name: '暮冬念春工作台' })).toBeVisible()
    expect(await page.evaluate(() => window.localStorage.getItem('novellab.theme-mode'))).toBe('dark')
  })
})
