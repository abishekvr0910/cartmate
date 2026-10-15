import { test, expect } from '@playwright/test';

test.describe('Populated profile and session contracts', () => {
  test('blocked-person profile renders without crashing', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (error) => errors.push(error.message));
    const headers = { Authorization: 'Bearer token_zuzanna' };
    const block = await page.request.post('/api/users/usr_marek/block', {
      headers,
      data: { reason: 'isolated browser contract test' },
    });
    expect(block.status()).toBe(200);
    try {
      await page.goto('/');
      await page.evaluate(() => {
        localStorage.setItem('cartmate_token', 'token_zuzanna');
        localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
      });
      await page.reload();
      await page.getByRole('navigation').getByRole('button', { name: /Profil|Profile/ }).click();
      await expect(page.getByText('Marek Nowak', { exact: true }).first()).toBeVisible();
      expect(errors).toEqual([]);
    } finally {
      const unblock = await page.request.delete('/api/users/usr_marek/block', { headers });
      expect(unblock.status()).toBe(200);
    }
  });

  test('log out other devices preserves this device', async ({ page }, testInfo) => {
    const phone = testInfo.project.name === 'mobile-chrome' ? '+48600111402' : '+48600111401';
    const requested = await page.request.post('/api/auth/otp/request', { data: { identifier: phone } });
    expect(requested.status()).toBe(200);
    const code = (await requested.json()).dev_code;
    expect(code).toMatch(/^\d{6}$/);
    const verified = await page.request.post('/api/auth/otp/verify', { data: { identifier: phone, code } });
    expect(verified.status()).toBe(200);
    const { token, user } = await verified.json();
    const currentHeaders = { Authorization: `Bearer ${token}` };
    const second = await page.request.post(`/api/auth/switch-user?user_id=${encodeURIComponent(user.id)}`);
    expect(second.status()).toBe(200);
    const otherToken = (await second.json()).token;
    try {
      await page.goto('/');
      await page.evaluate(({ token, userId }) => {
        localStorage.setItem('cartmate_token', token);
        localStorage.setItem('cartmate_user_id', userId);
      }, { token, userId: user.id });
      await page.reload();
      await page.getByRole('navigation').getByRole('button', { name: /Profil|Profile/ }).click();
      const revokeButton = page.getByRole('button', { name: /Wyloguj ze wszystkich pozostałych urządzeń|Revoke all other sessions/ });
      await expect(revokeButton).toBeEnabled();
      await revokeButton.click();
      await expect(revokeButton).toBeDisabled();
      expect((await page.request.get('/api/users/me', { headers: currentHeaders })).status()).toBe(200);
      expect((await page.request.get('/api/users/me', {
        headers: { Authorization: `Bearer ${otherToken}` },
      })).status()).toBe(401);
    } finally {
      await page.request.post('/api/auth/logout', { headers: currentHeaders });
    }
  });
});
