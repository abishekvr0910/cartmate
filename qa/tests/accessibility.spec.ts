import { test, expect } from '@playwright/test';

test.describe('Keyboard & Screen-Reader Accessibility Checks', () => {
  test('auth modal has proper ARIA attributes, keyboard focus, and accessible close button', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => localStorage.clear());
    await page.reload();

    const modal = page.locator('[role="dialog"][aria-modal="true"]');
    await expect(modal).toBeVisible({ timeout: 10000 });

    // Verify accessible role and modal declaration
    await expect(modal).toHaveAttribute('role', 'dialog');
    await expect(modal).toHaveAttribute('aria-modal', 'true');

    // Test keyboard focus can reach the input
    const input = modal.locator('input').first();
    await input.focus();
    await expect(input).toBeFocused();
    await expect(modal.getByRole('textbox', { name: 'Numer telefonu' })).toBeVisible();
    await modal.getByRole('button', { name: 'Zarejestruj się' }).click();
    await expect(modal.getByRole('textbox', { name: /Imię i Nazwisko/ })).toBeVisible();
    await expect(modal.getByRole('textbox', { name: /Weryfikacja numeru telefonu/ })).toBeVisible();

    // Verify accessible dismiss control is strictly present
    const closeBtn = modal.locator('button[aria-label*="Zamknij"], button[aria-label*="Close"]');
    await expect(closeBtn).toBeVisible();
    await expect(closeBtn).toHaveAttribute('aria-label');

    await closeBtn.click();
    const authTrigger = page.getByRole('button', { name: /Zaloguj się lub utwórz konto|Sign in or create an account/i });
    await authTrigger.click();
    await expect(modal.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Shift+Tab');
    await expect(modal.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Escape');
    await expect(modal).not.toBeVisible();
    await expect(authTrigger).toBeFocused();
  });

  test('navigation buttons have accessible labels', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await page.reload();

    // Wait for the app shell and nav/header to mount
    const nav = page.locator('nav').first();
    await expect(nav).toBeVisible({ timeout: 10000 });

    // Verify main navigation buttons have accessible labels (either visible text or aria-label)
    const buttons = nav.locator('button');
    const buttonCount = await buttons.count();
    expect(buttonCount).toBeGreaterThan(0);

    for (let i = 0; i < buttonCount; i++) {
      const btn = buttons.nth(i);
      const text = await btn.innerText();
      const ariaLabel = await btn.getAttribute('aria-label');
      expect(Boolean(text.trim() || ariaLabel), `Button index ${i} must have text or aria-label`).toBe(true);
    }

    await nav.getByRole('button', { name: 'Dodaj Wyjście' }).click();
    const createDialog = page.locator('[role="dialog"][aria-labelledby="create-ping-title"]');
    await expect(createDialog.getByRole('textbox', { name: 'Publiczne miejsce spotkania' })).toBeVisible();
    await expect(createDialog.getByRole('textbox', { name: 'Adres / Ulica' })).toBeVisible();
    await expect(createDialog.getByRole('combobox', { name: 'Kategoria Wyjścia' })).toBeVisible();
    await expect(createDialog.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Shift+Tab');
    await expect(createDialog.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Escape');
    await expect(createDialog).not.toBeVisible();
    await expect(nav.getByRole('button', { name: 'Dodaj Wyjście' })).toBeFocused();
  });

  test('320px viewport keeps the first outing reachable without horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 640 });
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await page.reload();
    await page.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).click();

    const nav = page.locator('nav').first();
    const outing = page.locator('[id^="ping-"]').first();
    await expect(nav).toBeVisible();
    await expect(outing).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);

    const navBox = await nav.boundingBox();
    const outingBox = await outing.boundingBox();
    expect(navBox).not.toBeNull();
    expect(outingBox).not.toBeNull();
    expect(outingBox!.y).toBeLessThan(navBox!.y);
    for (const button of await nav.locator('button').all()) {
      expect((await button.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    }
  });

  test('trip dialogs name their controls, trap focus, and return focus on Escape', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await page.reload();
    await page.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i }).click();

    const cancelTrigger = page.getByRole('button', { name: /Zrezygnuj z wyjścia|Cancel outing/i });
    await cancelTrigger.click();
    const cancelDialog = page.getByRole('dialog', { name: /Zrezygnuj z wyjścia|Cancel Outing/i });
    await expect(cancelDialog).toBeVisible();
    await expect(cancelDialog.getByRole('textbox', { name: /Dodatkowa wiadomość|Optional note/i })).toBeVisible();
    await expect(cancelDialog.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Shift+Tab');
    await expect(cancelDialog.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Escape');
    await expect(cancelDialog).not.toBeVisible();
    await expect(cancelTrigger).toBeFocused();

    const sosTrigger = page.getByRole('button', { name: /SOS/i }).first();
    await sosTrigger.click();
    const sosDialog = page.getByRole('dialog', { name: /Otworzyć opcje pomocy|Open emergency options/i });
    await expect(sosDialog).toBeVisible();
    await expect(sosDialog.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Escape');
    await expect(sosDialog).not.toBeVisible();
    await expect(sosTrigger).toBeFocused();

    const finishTrigger = page.getByRole('button', { name: /Zakończ wyjście|Finish outing/i });
    await finishTrigger.click();
    const finishDialog = page.getByRole('dialog', { name: /Zakończ wyjście|Finish outing/i });
    await expect(finishDialog).toBeVisible();
    await expect(finishDialog.getByRole('button', { name: /Zakończ bez oceny|Finish without a review/i })).toBeEnabled();
    await expect(finishDialog.getByRole('button', { name: /Tak, chętnie|Yes, buddy/i })).toHaveAttribute('aria-pressed', 'false');
    await expect(finishDialog.getByRole('button', { name: /Tylko jednorazowo|One-time only/i })).toHaveAttribute('aria-pressed', 'false');
    await page.keyboard.press('Escape');
    await expect(finishDialog).not.toBeVisible();
    await expect(finishTrigger).toBeFocused();
  });

  test('spot and group dialogs stay named, keyboard-contained and reflow at narrow width', async ({ page }) => {
    await page.setViewportSize({ width: 320, height: 568 });
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_zuzanna');
      localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
    });
    await page.reload();
    await page.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).click();

    const suggest = page.getByRole('button', { name: /Zaproponuj miejscówkę|Suggest a spot/i }).first();
    await expect(suggest).toBeVisible();
    await suggest.click();
    const spotDialog = page.getByRole('dialog', { name: /Zaproponuj|Suggest/i });
    await expect(spotDialog).toBeVisible();
    await expect(spotDialog.getByRole('textbox', { name: /Nazwa miejsca|Place name/i })).toBeVisible();
    await expect(spotDialog.getByRole('textbox', { name: /Ulica lub okolica|Street or area/i })).toBeVisible();
    await expect(spotDialog.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Shift+Tab');
    await expect(spotDialog.locator(':focus')).toHaveCount(1);
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
    await page.keyboard.press('Escape');
    await expect(spotDialog).not.toBeVisible();
    await expect(suggest).toBeFocused();

    const groupTrigger = page.getByRole('button', { name: /Dołącz do ekipy|Join the crew/i }).first();
    await expect(groupTrigger).toBeVisible();
    await groupTrigger.click();
    const groupDialog = page.getByRole('dialog', { name: /Kafej|Strefa Kultury/i });
    await expect(groupDialog).toBeVisible();
    await expect(groupDialog.getByRole('button', { name: /Otwórz czat ekipy|Open group chat/i })).toBeVisible();
    await expect(groupDialog.locator(':focus')).toHaveCount(1);
    await page.keyboard.press('Escape');
    await expect(groupDialog).not.toBeVisible();
    await expect(groupTrigger).toBeFocused();
  });
});
