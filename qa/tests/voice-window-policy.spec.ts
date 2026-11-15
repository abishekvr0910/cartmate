import { test, expect, type Page } from '@playwright/test';

// The voice lobby must show the voice-hours policy the server reports, in every language,
// and must never promise that a moderator is watching.

type WindowOverride = Record<string, unknown>;

const LANGUAGES = [
  { code: 'pl', menu: /Polski/i },
  { code: 'en', menu: /English/i },
  { code: 'uk', menu: /Українська/i },
  { code: 'ru', menu: /Русский/i },
] as const;

type LanguageCode = (typeof LANGUAGES)[number]['code'];

const SERVER_HOURS = { start: '19:00', end: '22:00', timezone: 'Europe/Warsaw' };
const HOURS_TEXT = '19:00 - 22:00';

const COPY: Record<
  LanguageCode,
  {
    unrestricted: string;
    open: string;
    closed: string;
    unavailable: string;
    closedButton: string;
    unavailableButton: string;
    note: RegExp;
  }
> = {
  pl: {
    unrestricted: 'Otwarte całą dobę',
    open: `Otwarte (${HOURS_TEXT})`,
    closed: `Zamknięte (${HOURS_TEXT})`,
    unavailable: 'Chwilowo niedostępne',
    closedButton: `Okno rozmów zamknięte (${HOURS_TEXT})`,
    unavailableButton: 'Rozmowy chwilowo niedostępne',
    note: /Nikt nie słucha rozmów na żywo.*112/,
  },
  en: {
    unrestricted: 'Open all day',
    open: `Open (${HOURS_TEXT})`,
    closed: `Closed (${HOURS_TEXT})`,
    unavailable: 'Temporarily unavailable',
    closedButton: `Call window closed (${HOURS_TEXT})`,
    unavailableButton: 'Calls temporarily unavailable',
    note: /Nobody listens to calls live.*112/,
  },
  uk: {
    unrestricted: 'Відкрито цілодобово',
    open: `Відкрито (${HOURS_TEXT})`,
    closed: `Закрито (${HOURS_TEXT})`,
    unavailable: 'Тимчасово недоступно',
    closedButton: `Вікно розмов зачинено (${HOURS_TEXT})`,
    unavailableButton: 'Розмови тимчасово недоступні',
    note: /Ніхто не слухає розмови наживо.*112/,
  },
  ru: {
    unrestricted: 'Открыто круглосуточно',
    open: `Открыто (${HOURS_TEXT})`,
    closed: `Закрыто (${HOURS_TEXT})`,
    unavailable: 'Временно недоступно',
    closedButton: `Окно звонков закрыто (${HOURS_TEXT})`,
    unavailableButton: 'Звонки временно недоступны',
    note: /Никто не слушает разговоры в реальном времени.*112/,
  },
};

async function signInAndOpenVoiceLobby(page: Page): Promise<void> {
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('cartmate_token', 'token_ola');
    localStorage.setItem('cartmate_user_id', 'usr_ola');
  });
  await page.reload();
  await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });
  await page.getByRole('navigation').getByRole('button', { name: /W pobliżu|Radar|Nearby/i }).first().click();
  await page.getByRole('button', { name: /Głos 10'|Voice 10'/i }).click();
  await expect(page.getByRole('heading', { name: '10-Minutowe Rozmowy' })).toBeVisible({ timeout: 5000 });
}

async function selectLanguage(page: Page, code: LanguageCode, menu: RegExp): Promise<void> {
  await page.locator('header').locator('button[title*="Wybierz język"], button[title*="Select language"]').first().click();
  await page.locator('header').getByRole('button', { name: menu }).first().click();
  await expect(page.locator('html')).toHaveAttribute('lang', code);
}

/** Serves the real status response with only the voice-hours fields replaced. */
async function overrideWindow(page: Page, override: WindowOverride): Promise<void> {
  await page.route('**/api/voice/status', async (route) => {
    const response = await route.fetch();
    const body = await response.json();
    await route.fulfill({
      response,
      json: { ...body, cooldown_remaining_seconds: 0, daily_calls_used: 0, ...override },
    });
  });
}

test.describe('Truthful voice-hours policy', () => {
  // Switching language refetches the status, so a request can still be in flight when a test
  // ends. Drop the route handlers quietly instead of failing on a response that no longer exists.
  test.afterEach(async ({ page }) => {
    await page.unrouteAll({ behavior: 'ignoreErrors' });
  });

  test('a server without an enforced window shows calls as open all day, with no evening hours', async ({ page }) => {
    // No mocking: the development test server enforces no window, exactly like staging.
    await signInAndOpenVoiceLobby(page);

    const badge = page.getByTestId('voice-window-state');
    await expect(badge).toHaveAttribute('data-state', 'unrestricted');
    await expect(badge).toHaveText(COPY.pl.unrestricted);
    await expect(page.getByText(/18:00/)).toHaveCount(0);
    await expect(page.getByTestId('voice-moderation-note')).toHaveText(COPY.pl.note);
  });

  test('unrestricted state is labelled in all four languages without implying moderator cover', async ({ page }) => {
    await overrideWindow(page, {
      window_state: 'unrestricted',
      window_open: true,
      window_enforced: false,
      window_hours: null,
      window_schedule: null,
    });
    await signInAndOpenVoiceLobby(page);

    for (const { code, menu } of LANGUAGES) {
      await selectLanguage(page, code, menu);
      await expect(page.getByTestId('voice-window-state')).toHaveText(COPY[code].unrestricted);
      await expect(page.getByTestId('voice-moderation-note')).toHaveText(COPY[code].note);
      await expect(page.getByText(/\d\d:00 - \d\d:00/)).toHaveCount(0);
    }
  });

  test('enforced open window shows the hours the server sent, in all four languages', async ({ page }) => {
    await overrideWindow(page, {
      window_state: 'open',
      window_open: true,
      window_enforced: true,
      window_hours: SERVER_HOURS,
    });
    await signInAndOpenVoiceLobby(page);

    for (const { code, menu } of LANGUAGES) {
      await selectLanguage(page, code, menu);
      const badge = page.getByTestId('voice-window-state');
      await expect(badge).toHaveAttribute('data-state', 'open');
      await expect(badge).toHaveText(COPY[code].open);
      await expect(page.getByTestId('voice-moderation-note')).toHaveText(COPY[code].note);
    }
  });

  test('enforced closed window disables calling and names the hours, in all four languages', async ({ page }) => {
    await overrideWindow(page, {
      window_state: 'closed',
      window_open: false,
      window_enforced: true,
      window_hours: SERVER_HOURS,
    });
    await signInAndOpenVoiceLobby(page);

    for (const { code, menu } of LANGUAGES) {
      await selectLanguage(page, code, menu);
      const badge = page.getByTestId('voice-window-state');
      await expect(badge).toHaveAttribute('data-state', 'closed');
      await expect(badge).toHaveText(COPY[code].closed);
      await expect(page.getByRole('button', { name: COPY[code].closedButton })).toBeDisabled();
    }
  });

  test('timezone failure shows calls as unavailable, not as an evening schedule, in all four languages', async ({ page }) => {
    await overrideWindow(page, {
      window_state: 'unavailable',
      window_open: false,
      window_enforced: true,
      window_hours: SERVER_HOURS,
    });
    await signInAndOpenVoiceLobby(page);

    for (const { code, menu } of LANGUAGES) {
      await selectLanguage(page, code, menu);
      const badge = page.getByTestId('voice-window-state');
      await expect(badge).toHaveAttribute('data-state', 'unavailable');
      await expect(badge).toHaveText(COPY[code].unavailable);
      await expect(page.getByRole('button', { name: COPY[code].unavailableButton })).toBeDisabled();
      await expect(page.getByText(/\d\d:00 - \d\d:00/)).toHaveCount(0);
    }
  });

  test('the call button stays disabled until the server has reported its policy', async ({ page }) => {
    let release: () => void = () => {};
    const held = new Promise<void>((resolve) => {
      release = resolve;
    });
    await page.route('**/api/voice/status', async (route) => {
      await held;
      const response = await route.fetch();
      const body = await response.json();
      await route.fulfill({ response, json: { ...body, cooldown_remaining_seconds: 0, daily_calls_used: 0 } });
    });
    await signInAndOpenVoiceLobby(page);

    const badge = page.getByTestId('voice-window-state');
    await expect(badge).toHaveAttribute('data-state', 'checking');
    await expect(page.getByRole('button', { name: 'Sprawdzanie…' })).toBeDisabled();

    release();
    await expect(badge).toHaveAttribute('data-state', 'unrestricted');
    await expect(page.getByRole('button', { name: /Połącz z kimś teraz/ })).toBeEnabled();
  });

  test('a failed status request shows calls as unavailable and blocks calling', async ({ page }) => {
    await page.route('**/api/voice/status', (route) =>
      route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: 'unavailable' }) }),
    );
    await signInAndOpenVoiceLobby(page);

    await expect(page.getByTestId('voice-window-state')).toHaveAttribute('data-state', 'unavailable');
    await expect(page.getByRole('button', { name: COPY.pl.unavailableButton })).toBeDisabled();
    await expect(page.getByText(/\d\d:00 - \d\d:00/)).toHaveCount(0);
  });

  test('cooldown still takes over the call button while the window is open', async ({ page }) => {
    await overrideWindow(page, {
      window_state: 'unrestricted',
      window_open: true,
      window_enforced: false,
      window_hours: null,
      cooldown_remaining_seconds: 420,
    });
    await signInAndOpenVoiceLobby(page);

    await expect(page.getByTestId('voice-window-state')).toHaveText(COPY.pl.unrestricted);
    await expect(page.getByRole('button', { name: 'Przerwa: 420s' })).toBeDisabled();
  });

  test('daily limit still takes over the call button while the window is open', async ({ page }) => {
    await overrideWindow(page, {
      window_state: 'open',
      window_open: true,
      window_enforced: true,
      window_hours: SERVER_HOURS,
      daily_calls_used: 3,
    });
    await signInAndOpenVoiceLobby(page);

    await expect(page.getByTestId('voice-window-state')).toHaveText(COPY.pl.open);
    await expect(page.getByRole('button', { name: 'Osiągnięto limit dzienny (3/3)' })).toBeDisabled();
  });
});
