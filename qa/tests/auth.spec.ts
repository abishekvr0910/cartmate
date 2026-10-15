import { test, expect } from '@playwright/test';

test.describe('Authentication & Session Journey', () => {
  test('unauthenticated visitor is prompted with Auth modal', async ({ page }) => {
    // Clear any residual session
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    const authModal = page.locator('[role="dialog"][aria-modal="true"]');
    await expect(authModal).toBeVisible({ timeout: 10000 });
    await expect(authModal.getByRole('heading', { level: 2 })).toBeVisible();
  });

  test('user can log in via OTP and log out cleanly with server revocation', async ({ page }, testInfo) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    const authModal = page.locator('[role="dialog"][aria-modal="true"]');
    await expect(authModal).toBeVisible({ timeout: 10000 });

    // Fill in Polish phone number
    const identifierInput = authModal.locator('input[type="text"]').first();
    await identifierInput.fill(testInfo.project.name === 'mobile-chrome' ? '+48600111223' : '+48600111222');

    // Click request OTP button
    const requestOtpBtn = authModal.locator('button[type="submit"]');
    await requestOtpBtn.click();

    // Local console-provider runs disclose the code; staging must supply a controlled test code.
    const codeInput = authModal.locator('input[maxlength="6"]');
    await expect(codeInput).toBeVisible({ timeout: 8000 });

    const hint = process.env.CARTMATE_E2E_OTP_CODE
      ? null
      : await authModal.getByText(/Kod testowy:/).textContent({ timeout: 5000 }).catch(() => null);
    const code = process.env.CARTMATE_E2E_OTP_CODE || hint?.match(/\b\d{6}\b/)?.[0];
    expect(code, 'A controlled OTP code is required; never bypass verification').toMatch(/^\d{6}$/);
    await codeInput.fill(code!);

    // Click verify OTP
    const verifyBtn = authModal.locator('button[type="submit"]');
    await verifyBtn.click();

    // Modal closes and user enters main radar view
    await expect(authModal).not.toBeVisible({ timeout: 8000 });
    const profileBtn = page.getByRole('navigation').getByRole('button', { name: /Profil|Profile/i });
    await expect(profileBtn).toBeVisible({ timeout: 8000 });

    // Check token is stored in localStorage
    const storedToken = await page.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(storedToken).toBeTruthy();

    // Navigate to profile and log out
    await profileBtn.click();
    const logoutBtn = page.getByRole('button', { name: /Wyloguj/i }).first();
    await expect(logoutBtn).toBeVisible({ timeout: 5000 });
    await logoutBtn.click();

    // Verify auth modal is displayed again and token is revoked
    await expect(authModal).toBeVisible({ timeout: 8000 });
    const clearedToken = await page.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(clearedToken).toBeNull();

    // Assert token is revoked on server
    const revokedResponse = await page.request.get('/api/users/me', {
      headers: { Authorization: `Bearer ${storedToken}` },
    });
    expect(revokedResponse.status()).toBe(401);
  });
});
