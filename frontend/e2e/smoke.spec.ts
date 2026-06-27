import { test, expect } from '@playwright/test'

const BASE = process.env.E2E_BASE_URL || 'http://43.98.185.179'
const EMAIL = `e2e_${Date.now()}@test.local`
const PASS = 'testpass123'

test.describe('Spider雷达 E2E', () => {
  test('register, login, browse market', async ({ page }) => {
    await page.goto(`${BASE}/register`)
    await page.locator('#reg-email').fill(EMAIL)
    await page.locator('#reg-password').fill(PASS)
    await page.getByRole('button', { name: '注册并登录' }).click()
    await expect(page).toHaveURL(/\/\/?$/)
    await expect(page.getByRole('heading', { name: '总览' })).toBeVisible()

    await page.getByRole('link', { name: '🛒 账号市场' }).click()
    await expect(page.getByText('购买账号').first()).toBeVisible({ timeout: 15000 })

    await page.getByRole('link', { name: '个人资料' }).click()
    await page.locator('#profile-nickname').fill('E2E 昵称')
    await page.getByRole('button', { name: '保存昵称' }).click()
    await expect(page.getByText('已保存')).toBeVisible()
    await expect(page.getByRole('main').getByText(EMAIL)).toBeVisible()
  })

  test('login with existing flow', async ({ page }) => {
    const email = `e2e_login_${Date.now()}@test.local`
    await page.goto(`${BASE}/register`)
    await page.locator('#reg-email').fill(email)
    await page.locator('#reg-password').fill(PASS)
    await page.getByRole('button', { name: '注册并登录' }).click()
    await expect(page.getByRole('heading', { name: '总览' })).toBeVisible()

    await page.getByRole('button', { name: '退出登录' }).click()
    await page.locator('#login-email').fill(email)
    await page.locator('#login-password').fill(PASS)
    await page.getByRole('button', { name: '登录' }).click()
    await expect(page.getByRole('heading', { name: '总览' })).toBeVisible()
  })
})
