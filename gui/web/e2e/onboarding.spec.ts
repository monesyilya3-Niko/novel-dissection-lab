// 空库首启引导 E2E：OnboardingWizard 在「无书籍 + 无资产 + 未标记 onboarded」时出现。
//
// 运行要求：必须跑在空库的隔离服务上（单文件独占一次隔离服务）：
//   bash scripts/e2e_isolated.sh e2e/onboarding.spec.ts
// 若与 journey 等导入书籍的用例共享同一服务，库非空时本文件自动 skip
// （用例内先查 /api/overview 做前置断言），避免 flaky。
//
// 2026-11-01 重写：向导从 3 步改为 4 步，存储键从 novellab.onboarded='1'
// 改为 novellab.onboarded.v2='{done,dismissedAt}'，s2 主按钮不再是「去导入」
// 而是「下一步」（跳转移到独立的 shortcut 按钮）。旧断言全部失效，
// e2e 跑起来会红——那是用例过时，不是功能坏了。
import { expect, test, request } from '@playwright/test'

export const ONBOARDED_KEY_V2 = 'novellab.onboarded.v2'

/** 读取 v2 存储并解析；未写入时返回 null。 */
async function readOnboardState(page: import('@playwright/test').Page) {
  const raw = await page.evaluate((k) => window.localStorage.getItem(k), ONBOARDED_KEY_V2)
  if (!raw) return null
  try {
    return JSON.parse(raw) as { done: boolean; dismissedAt: number }
  } catch {
    return null
  }
}

test.beforeEach(async ({ page, baseURL }) => {
  const api = await request.newContext({ baseURL })
  const resp = await api.get('/api/overview')
  const body = await resp.json()
  await api.dispose()
  // 注意：Playwright 的 request 是原生 JSON（snake_case），前端 client.ts 才做
  // camelCase 转换——这里必须用后端的 total_books / total_assets。
  test.skip(
    body?.data?.total_books !== 0 || body?.data?.total_assets !== 0,
    '需要空库（total_books/total_assets 均为 0），请单独隔离运行本文件',
  )
  // 全新浏览器上下文 localStorage 为空 → onboarded 未标记（Playwright 默认每用例新上下文）
  await page.goto('/')
})

test('空库首访显示引导向导，四步走完后不再出现', async ({ page }) => {
  // s1 欢迎
  await expect(page.getByText('欢迎使用暮冬念春')).toBeVisible({ timeout: 15_000 })
  await page.getByRole('button', { name: '下一步' }).click()

  // s2 导入并拆书：主按钮是「下一步」（不再直接跳走），另有 shortcut 按钮
  await expect(page.getByText('第一步：导入并拆书')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByTestId('onboarding-shortcut-cta')).toBeVisible()
  await page.getByTestId('onboarding-primary-cta').click()

  // s3 资产与质检
  await expect(page.getByText('第二步：查看资产与质检')).toBeVisible({ timeout: 10_000 })
  await page.getByTestId('onboarding-primary-cta').click()

  // s4 下一步做什么（三选一卡片）
  await expect(page.getByText('下一步做什么')).toBeVisible({ timeout: 10_000 })
  await expect(page.getByTestId('onboarding-action-analysis')).toBeVisible()
  await expect(page.getByTestId('onboarding-action-assets')).toBeVisible()
  await expect(page.getByTestId('onboarding-action-writing')).toBeVisible()
  // 点卡片即完成并跳转
  await page.getByTestId('onboarding-action-analysis').click()

  // 向导关闭且已写入 v2 存储
  await expect(page.getByText('欢迎使用暮冬念春')).toBeHidden({ timeout: 10_000 })
  const state = await readOnboardState(page)
  expect(state?.done, 'v2 存储应标记已完成').toBe(true)
  expect(typeof state?.dismissedAt, 'v2 存储应带时间戳').toBe('number')

  // 刷新后不再弹出
  await page.reload()
  await expect(page.getByText('欢迎使用暮冬念春')).toBeHidden({ timeout: 15_000 })
})

test('s2 捷径按钮直接跳转到对应工作台并完成引导', async ({ page }) => {
  await expect(page.getByText('欢迎使用暮冬念春')).toBeVisible({ timeout: 15_000 })
  await page.getByRole('button', { name: '下一步' }).click()
  await expect(page.getByText('第一步：导入并拆书')).toBeVisible({ timeout: 10_000 })

  // 空库默认未配模型 → 捷径文案为「去配置模型」，点击应完成引导并落到系统页
  const shortcut = page.getByTestId('onboarding-shortcut-cta')
  await expect(shortcut).toBeVisible()
  await shortcut.click()

  await expect(page.getByText('欢迎使用暮冬念春')).toBeHidden({ timeout: 10_000 })
  const state = await readOnboardState(page)
  expect(state?.done).toBe(true)
})

test('空库首访可随时跳过引导', async ({ page }) => {
  await expect(page.getByText('欢迎使用暮冬念春')).toBeVisible({ timeout: 15_000 })
  await page.getByRole('button', { name: '跳过' }).click()
  await expect(page.getByText('欢迎使用暮冬念春')).toBeHidden({ timeout: 10_000 })
  const state = await readOnboardState(page)
  expect(state?.done).toBe(true)
})
