import { test, expect } from '@playwright/test';

test.describe('Plan visibility and cancellation-modal smoke checks', () => {
  test.beforeEach(async ({ page }) => {
    // Authenticate as Jakub (host of active trip_makro_01)
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await page.reload();
  });

  test('user sees live radar pings and can inspect specific destination and intent tags', async ({ page }) => {
    await page.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).click();
    // Radar container is strictly expected to be visible
    const radarMain = page.locator('main').first();
    await expect(radarMain).toBeVisible({ timeout: 10000 });

    // Verify presence of live pings
    const pingDestination = page.locator('text=/Makro|Biedronka|Silesia/i').first();
    await expect(pingDestination).toBeVisible();

    // Verify intent tags are rendered (e.g. #...)
    const intentTag = page.locator('text=/#/').first();
    await expect(intentTag).toBeVisible();
  });

  test('active trip HUD displays concrete plan terms (what, when, duration, cost policy)', async ({ page }) => {
    // Wait for bottom navigation to be visible
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });

    // Navigate strictly to the Active Trip tab
    const tripNavBtn = page.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i });
    await expect(tripNavBtn).toBeVisible({ timeout: 5000 });
    await tripNavBtn.click();

    // Verify Active Trip HUD destination
    await expect(page.getByText(/Makro Cash & Carry/i).first()).toBeVisible({ timeout: 8000 });

    // Verify concrete plan duration (~45m)
    await expect(page.getByText(/~?45\s*m/i).first()).toBeVisible();

    // Verify 50/50 cost sharing policy is explicitly stated
    await expect(page.getByText(/50\/50/i).first()).toBeVisible();

    // Verify rendezvous spot location is clearly stated
    await expect(page.getByText(/Roździeńskiego/i).first()).toBeVisible();
  });

  test('cancellation modal provides respectful low-guilt reason tags and dismisses cleanly', async ({ page }) => {
    // Wait for bottom navigation to be visible
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });

    // Navigate strictly to the Active Trip tab
    const tripNavBtn = page.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i });
    await expect(tripNavBtn).toBeVisible({ timeout: 5000 });
    await tripNavBtn.click();

    // Click low-guilt cancellation button (fail-closed, no if)
    const cancelTrigger = page.getByRole('button', { name: /Zrezygnuj z wyjścia|Cancel outing/i });
    await expect(cancelTrigger).toBeVisible({ timeout: 5000 });
    await cancelTrigger.click();

    // Verify cancellation modal is displayed with title
    const cancelModal = page.locator('div.fixed.inset-0').filter({ hasText: /Zrezygnuj z wyjścia|Cancel Outing/i });
    await expect(cancelModal).toBeVisible();

    // Verify radio reasons exist (at least 3 reasons)
    const reasonRadios = cancelModal.locator('input[type="radio"], input[name="cancel_reason"]');
    await expect(reasonRadios).toHaveCount(6);
    for (const reason of [
      'Zmieniły mi się plany',
      'Kolidujący termin / pilna sprawa',
      'Pogoda lub trudności z dojazdem',
      'Nagła sytuacja',
      'To wyjście nie jest już potrzebne',
      'Inny powód',
    ]) {
      await expect(cancelModal.getByRole('radio', { name: reason })).toBeVisible();
    }

    // Verify dismiss button works cleanly
    const dismissBtn = cancelModal.getByRole('button', { name: /Anuluj|Cancel/i }).first();
    await expect(dismissBtn).toBeVisible();
    await dismissBtn.click();

    // Modal must close
    await expect(cancelModal).not.toBeVisible();
  });
});
