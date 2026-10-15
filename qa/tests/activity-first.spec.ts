import { test, expect } from '@playwright/test';

test('a person can post a study outing and another person can discover it', async ({ browser }) => {
  const host = await browser.newPage();
  const companion = await browser.newPage();
  const destination = `Public library entrance ${Date.now()}`;
  try {
    await host.goto('/');
    await host.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await host.reload();
    await expect(host.getByRole('navigation')).toBeVisible();
    await host.getByRole('navigation').getByRole('button', { name: 'Dodaj Wyjście' }).click();

    const dialog = host.locator('#create-ping-dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText(/siłownia może wymagać karnetu/i)).toBeVisible();
    await dialog.locator('#create-ping-category').selectOption('study');
    await dialog.locator('#create-ping-destination').fill(destination);
    await dialog.locator('#create-ping-address').fill('Katowice, public library main entrance');
    await host.route('**/api/ai/classify-intent', async (route) => {
      await route.fulfill({
        json: {
          category: 'grocery', intent_tags: ['#WspólnaNauka'], confidence_score: 1,
          suggested_duration_minutes: 45, recommended_group_size: 2,
          social_context_summary: 'Advisory classification only', is_safe: true,
        },
      });
    });
    await dialog.getByRole('button', { name: /Jev AI: Dopasuj tagi i punkty/ }).click();
    await expect(dialog.getByRole('button', { name: '#WspólnaNauka' })).toHaveClass(/border-teal-500/);
    await expect(dialog.locator('#create-ping-category')).toHaveValue('study');
    await dialog.getByRole('button', { name: /Opublikuj na Radarze/i }).click();
    await expect(dialog).not.toBeVisible();

    await companion.goto('/');
    await companion.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_zuzanna');
      localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
    });
    await companion.reload();
    await companion.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).click();
    // This seeded account opens with the women-only filter enabled; the ordinary outing is not women-only.
    await companion.getByRole('button', { name: /Strefa Kobiet/ }).click();
    await expect(companion.getByRole('button', { name: /Wspólna nauka/ }).first()).toBeVisible();
    await companion.getByRole('button', { name: /Wspólna nauka/ }).first().click();
    await expect(companion.getByText(destination).first()).toBeVisible();
    await expect(companion.getByText(/Wspólna nauka/).last()).toBeVisible();
  } finally {
    await host.close();
    await companion.close();
  }
});
