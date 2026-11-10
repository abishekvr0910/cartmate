import { test, expect } from '@playwright/test';

test.describe('Truthful Safety & SOS Disclosures Journey', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as Jakub (active trip participant)
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await page.reload();
  });

  test('safety hub displays truthful emergency contact consent status and 112 guidance', async ({ page }) => {
    // Wait for bottom nav
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });

    // Navigate strictly to the Safety Hub tab
    const safetyNavBtn = page.getByRole('navigation').getByRole('button', { name: /Bezpieczeństwo|Safety/i });
    await expect(safetyNavBtn).toBeVisible({ timeout: 5000 });
    await safetyNavBtn.click();

    // Verify 3-tier trust status card is rendered
    await expect(page.locator('text=/Poziom zaufania|Twój Poziom|Your Tier/i').first()).toBeVisible({ timeout: 5000 });

    // Verify truthfulness statement: emergency contact requires consent, fallback to 112
    const disclaimer = page.locator('text=/112|zgoda odbiorcy/i').first();
    await expect(disclaimer).toBeVisible();
    await expect(page.locator('text=/nie zastępuje służb ratunkowych|112/i').first()).toBeVisible();
  });

  test('active trip SOS modal shows 112 and requires explicit confirmation', async ({ page }) => {
    // Wait for bottom nav
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });

    // Navigate strictly to the Active Trip tab
    const tripNavBtn = page.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i });
    await expect(tripNavBtn).toBeVisible({ timeout: 5000 });
    await tripNavBtn.click();

    // Click SOS button (fail-closed, no conditional if)
    const sosTrigger = page.getByRole('button', { name: /SOS/i }).first();
    await expect(sosTrigger).toBeVisible({ timeout: 5000 });
    await sosTrigger.click();

    // SOS modal must be visible
    const sosModal = page.getByRole('dialog', { name: /Otworzyć opcje pomocy|Open emergency options/i });
    await expect(sosModal).toBeVisible({ timeout: 5000 });

    // The pilot is direct-112-only: no SMS or emergency call is sent by CartMate.
    await expect(sosModal.getByText(/nie dzwoni pod 112|does not call 112/i)).toBeVisible();
    await expect(sosModal.locator('text=/112|zgoda nie jest potwierdzona/i').first()).toBeVisible();

    // Assert explicit user consent checkbox exists
    const consentCheckbox = sosModal.locator('input[type="checkbox"]');
    await expect(consentCheckbox).toBeVisible();
    await expect(consentCheckbox).not.toBeChecked();
    const confirmButton = sosModal.getByRole('button', { name: /Pokaż opcje pomocy|Show help options/i });
    await expect(confirmButton).toBeDisabled();
    await consentCheckbox.check();
    await expect(confirmButton).toBeEnabled();

    // Dismiss modal cleanly
    const dismissBtn = sosModal.getByRole('button', { name: /Anuluj|Cancel/i }).first();
    await expect(dismissBtn).toBeVisible();
    await dismissBtn.click();
    await expect(sosModal).not.toBeVisible();
  });

  test('discovery segmented switcher navigates between 1:1 outings, micro-pods 3-5, and 10m voice while preserving Safety tab', async ({ page }) => {
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });
    const safetyNavBtn = page.getByRole('navigation').getByRole('button', { name: /Bezpieczeństwo|Safety/i });
    await expect(safetyNavBtn).toBeVisible();

    const nearbyNavBtn = page.getByRole('navigation').getByRole('button', { name: /W pobliżu|Radar|Nearby/i }).first();
    await nearbyNavBtn.click();

    const podsBtn = page.getByRole('button', { name: /Pody 3-5|Pods 3-5/i });
    await expect(podsBtn).toBeVisible({ timeout: 5000 });
    await podsBtn.click();
    await expect(page.locator('text=/Pody 3–5 osób|Pody 3-5/i').first()).toBeVisible({ timeout: 5000 });

    const voiceBtn = page.getByRole('button', { name: /Głos 10'|Voice 10'/i });
    await expect(voiceBtn).toBeVisible();
    await voiceBtn.click();
    await expect(page.locator('text=/Rozmowy Głosowe|Połącz z kimś teraz/i').first()).toBeVisible({ timeout: 5000 });
    await expect(safetyNavBtn).toBeVisible();
  });
});
