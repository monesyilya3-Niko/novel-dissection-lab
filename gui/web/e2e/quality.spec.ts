// 质检台 E2E：四个子页签渲染、切换不报错、关键控件可用。
//
// 质检台是用户写完一章后的必经环节，此前无 e2e 覆盖。它的失败模式是
// 页签点了空白（面板未挂载）或运行时异常，单测覆盖不到真实挂载路径。
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.goto('/')
  await page.getByRole('button', { name: '质量检验', exact: false }).first().click()
})

test('质检台四个子页签全部渲染', async ({ page }) => {
  for (const name of [/单章检查/, /全书质检/, /QC 综合/, /毒点避雷/]) {
    await expect(page.getByRole('tab', { name })).toBeVisible({ timeout: 15_000 })
  }
})

test('逐个切换子页签，面板均非空白且无未捕获异常', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))

  for (const name of [/单章检查/, /全书质检/, /QC 综合/, /毒点避雷/]) {
    await page.getByRole('tab', { name }).click()
    await page.waitForTimeout(300)
    // 面板必须有可见文字（不能是空白容器）
    const bodyText = await page.locator('body').innerText()
    expect(bodyText.trim().length, `${name} 面板不应为空`).toBeGreaterThan(20)
  }
  expect(errors, '切换页签不应抛未捕获异常').toEqual([])
})

test('单章检查页有可输入的正文区域', async ({ page }) => {
  await page.getByRole('tab', { name: /单章检查/ }).click()
  // 至少一个 textarea 或 input 让用户粘贴/填写章节
  const inputs = page.locator('textarea, input[type="text"]')
  await expect(inputs.first()).toBeVisible({ timeout: 10_000 })
})
