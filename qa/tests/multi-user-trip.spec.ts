import { test, expect, type Page } from '@playwright/test';

type TripWsFrame = {
  type?: string;
  scope?: string;
  payload?: { sender_id?: string; id?: string; status?: string; sos_triggered?: boolean; trip_id?: string; companion_checked_in?: boolean; rendezvous_verified?: boolean; total_split_pln?: number };
};

function captureRealtimeFrames(page: Page): TripWsFrame[] {
  const frames: TripWsFrame[] = [];
  page.on('websocket', (socket) => {
    if (new URL(socket.url()).pathname !== '/ws') return;
    socket.on('framereceived', ({ payload }) => {
      try { frames.push(JSON.parse(String(payload))); } catch { /* Ignore non-JSON frames. */ }
    });
  });
  return frames;
}

test.describe('Multi-User Trip Coordination & Rendezvous Journey', () => {
  test.beforeEach(async ({ request }) => {
    // Uses configured Playwright baseURL without hardcoding port 8000
    const reset = await request.post('/api/testing/reset-seeded-trip');
    expect(reset.status()).toBe(200);
  });

  test('host and companion coordinate plan, chat live, verify PIN handshake, and calculate 50/50 balance', async ({ browser }) => {
    // Context 1: Host Jakub
    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const hostFrames = captureRealtimeFrames(hostPage);
    await hostPage.goto('/');
    await hostPage.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await hostPage.reload();

    // Context 2: Companion Zuzanna
    const companionContext = await browser.newContext({
      permissions: ['clipboard-read', 'clipboard-write'],
    });
    const companionPage = await companionContext.newPage();
    const companionFrames = captureRealtimeFrames(companionPage);
    companionPage.on('dialog', (dialog) => dialog.accept());
    await companionPage.goto('/');
    await companionPage.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_zuzanna');
      localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
    });
    await companionPage.reload();

    // 1. Host navigates to Active Trip HUD
    const hostTripNav = hostPage.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i });
    await expect(hostTripNav).toBeVisible({ timeout: 10000 });
    await hostTripNav.click();

    // Host sees destination and 50/50 terms
    await expect(hostPage.getByText(/Makro Cash & Carry/i).first()).toBeVisible({ timeout: 8000 });
    await expect(hostPage.getByText(/50\/50/i).first()).toBeVisible();

    // Host sees waiting for companion acceptance notice
    await expect(hostPage.getByText(/Oczekiwanie na akceptację|Waiting for the companion to accept/i).first()).toBeVisible({ timeout: 5000 });
    await expect.poll(() => hostFrames.some((frame) => frame.type === 'subscription.confirmed' && frame.scope?.startsWith('trip:')), { timeout: 10000 }).toBe(true);

    // 2. Companion navigates to Active Trip HUD
    const compTripNav = companionPage.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i });
    await expect(compTripNav).toBeVisible({ timeout: 10000 });
    await compTripNav.click();
    await expect(companionPage.getByText(/Makro Cash & Carry/i).first()).toBeVisible({ timeout: 8000 });
    await expect.poll(() => companionFrames.some((frame) => frame.type === 'subscription.confirmed' && frame.scope?.startsWith('chat:')), { timeout: 10000 }).toBe(true);

    // Companion accepts the plan terms
    const acceptPlanBtn = companionPage.getByRole('button', { name: /Akceptuję warunki spotkania|Accept Plan Terms/i });
    await expect(acceptPlanBtn).toBeVisible({ timeout: 5000 });
    await acceptPlanBtn.click();
    await expect(companionPage.getByText(/Plan zaakceptowany|Plan accepted/i).first()).toBeVisible({ timeout: 5000 });

    // Host sees mutual acceptance from the WebSocket, without a page reload.
    await expect.poll(() => hostFrames.some((frame) => frame.type === 'trip.plan_accepted' && frame.scope?.startsWith('trip:')), { timeout: 10000 }).toBe(true);
    await expect(hostPage.getByText(/Plan zaakceptowany|Plan accepted/i).first()).toBeVisible({ timeout: 5000 });

    const hostCheckInBtn = hostPage.getByRole('button', { name: /Jestem na miejscu|Check in|Arrived/i });
    await expect(hostCheckInBtn).toBeVisible({ timeout: 5000 });
    await hostCheckInBtn.click();
    const hostPinDisplay = hostPage.locator('span.font-mono.text-xl.font-black.text-amber-400');
    await expect(hostPinDisplay).toBeVisible({ timeout: 5000 });
    const sharedPin = (await hostPinDisplay.innerText()).trim();
    expect(sharedPin).toMatch(/^\d{4}$/);

    await companionPage.getByRole('button', { name: /Jestem na miejscu|Check in|Arrived/i }).click();
    await expect.poll(() => hostFrames.some((frame) => frame.type === 'trip.status_updated' && frame.payload?.id === 'trip_makro_01' && frame.payload?.companion_checked_in === true), { timeout: 10000 }).toBe(true);
    await expect(hostPinDisplay).toHaveText(sharedPin);

    // 3. Live In-App Coordination Chat
    const hostChatInput = hostPage.getByPlaceholder(/Napisz|Standing outside/i);
    await expect(hostChatInput).toBeEnabled({ timeout: 5000 });
    await hostChatInput.fill('Cześć Zuzanna! Stoję przy wejściu głównym.');
    await hostPage.locator('form:has(input[aria-label]) button[type="submit"]').click();
    await expect(hostPage.getByText('Cześć Zuzanna! Stoję przy wejściu głównym.')).toBeVisible({ timeout: 5000 });

    // Companion receives the live chat frame and sees it without reloading.
    await expect.poll(() => companionFrames.some((frame) => frame.type === 'chat.message' && frame.scope?.startsWith('chat:') && frame.payload?.sender_id === 'usr_jakub'), { timeout: 10000 }).toBe(true);
    await expect(companionPage.getByText('Cześć Zuzanna! Stoję przy wejściu głównym.')).toBeVisible({ timeout: 5000 });
    const compChatInput = companionPage.getByPlaceholder(/Napisz|Standing outside/i);
    await compChatInput.fill('Super, wchodzę do hali!');
    await companionPage.locator('form:has(input[aria-label]) button[type="submit"]').click();
    await expect(companionPage.getByText('Super, wchodzę do hali!')).toBeVisible({ timeout: 5000 });

    // 4. Dual PIN Rendezvous
    // Companion enters wrong PIN first to verify fail-closed security
    const pinInput = companionPage.locator('input[placeholder="0000"]');
    await pinInput.fill('0000');
    const verifyBtn = companionPage.getByRole('button', { name: /Potwierd[zź] Spotkanie|Confirm Handshake/i });
    await verifyBtn.click();
    await expect(companionPage.locator('text=/Nieprawidłowy kod PIN|Invalid PIN|Incorrect PIN/i').first()).toBeVisible({ timeout: 5000 });

    // Companion enters the real PIN shared by host
    await pinInput.fill(sharedPin);
    await verifyBtn.click();
    await expect(companionPage.locator('text=/Wpisano zgodny PIN|Matching PIN entered|Organizator zameldowa/i').first()).toBeVisible({ timeout: 8000 });
    await expect.poll(() => hostFrames.some((frame) => frame.type === 'trip.handshake_verified' && frame.payload?.id === 'trip_makro_01' && frame.payload?.rendezvous_verified === true), { timeout: 10000 }).toBe(true);
    await expect(hostPage.locator('text=/Wpisano zgodny PIN|Matching PIN entered|Organizator zameldowa/i').first()).toBeVisible({ timeout: 8000 });

    // 5. Wholesale 50/50 Balance Settlement & Item Recording
    // Host records a new grocery item to split
    const addSplitBtn = hostPage.getByRole('button', { name: /Dodaj pozycję|Record item/i });
    await expect(addSplitBtn).toBeVisible({ timeout: 5000 });
    await addSplitBtn.click();

    await hostPage.locator('input[placeholder*="Zgrzewka"]').fill('Kawa ziarnista Lavazza 1kg');
    await hostPage.locator('input[placeholder="34.90"]').fill('50.00');
    await hostPage.getByRole('button', { name: /Zapisz pozycję|Record item/i }).click();

    // Host sees the newly added item and updated total split
    await expect(hostPage.getByText('Kawa ziarnista Lavazza 1kg')).toBeVisible({ timeout: 5000 });
    await expect(hostPage.getByText('189.90 zł').first()).toBeVisible({ timeout: 5000 });

    // Companion sees the updated calculated balance without reloading.
    await expect.poll(() => companionFrames.some((frame) => frame.type === 'trip.status_updated' && frame.payload?.id === 'trip_makro_01' && frame.payload?.total_split_pln === 189.9), { timeout: 10000 }).toBe(true);
    await expect(companionPage.getByText('Kawa ziarnista Lavazza 1kg')).toBeVisible({ timeout: 5000 });
    await expect(companionPage.getByText('189.90 zł').first()).toBeVisible({ timeout: 5000 });
    await expect(companionPage.getByText(/94\.95 zł/).first()).toBeVisible({ timeout: 5000 });

    // Companion copies contact number for manual BLIK transfer
    const blikBtn = companionPage.getByRole('button', { name: /Skopiuj numer kontaktowy|Copy contact number/i });
    await expect(blikBtn).toBeVisible({ timeout: 5000 });
    await blikBtn.click();
    await expect(companionPage.getByText(/Skopiowano|Contact number copied|Copied/i).first()).toBeVisible({ timeout: 5000 });

    await hostContext.close();
    await companionContext.close();
  });

  test('cancellation reaches the other participant across tabs without a reload', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const hostFrames = captureRealtimeFrames(hostPage);
    await hostPage.goto('/');
    await hostPage.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await hostPage.reload();
    await expect.poll(() => hostFrames.some((frame) => frame.type === 'subscription.confirmed' && frame.scope?.startsWith('trip:')), { timeout: 10000 }).toBe(true);

    const companionContext = await browser.newContext();
    const companionPage = await companionContext.newPage();
    await companionPage.goto('/');
    await companionPage.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_zuzanna');
      localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
    });
    await companionPage.reload();
    await companionPage.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i }).click();
    await companionPage.getByRole('button', { name: /Zrezygnuj z wyjścia|Cancel outing/i }).click();
    const cancellation = companionPage.getByRole('dialog', { name: /Zrezygnuj z wyjścia|Cancel Outing/i });
    await expect(cancellation).toBeVisible();
    await cancellation.getByRole('button', { name: /Potwierdź rezygnację|Confirm Cancel/i }).click();

    await expect.poll(() => hostFrames.some((frame) => frame.type === 'trip.cancelled' && frame.payload?.trip_id === 'trip_makro_01'), { timeout: 10000 }).toBe(true);
    await expect(hostPage.getByRole('status').getByText(/Wyjście zostało anulowane|The outing was cancelled/i)).toBeVisible({ timeout: 5000 });
    await hostPage.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i }).click();
    await expect(hostPage.getByText(/Brak Aktywnego Wyjścia|No Outing Currently Active/i)).toBeVisible();

    await hostContext.close();
    await companionContext.close();
  });

  test('SOS reaches the other participant as a valid trip update without a reload', async ({ browser }) => {
    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const hostFrames = captureRealtimeFrames(hostPage);
    await hostPage.goto('/');
    await hostPage.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await hostPage.reload();
    await expect.poll(() => hostFrames.some((frame) => frame.type === 'subscription.confirmed' && frame.scope?.startsWith('trip:')), { timeout: 10000 }).toBe(true);

    const companionContext = await browser.newContext();
    const companionPage = await companionContext.newPage();
    await companionPage.goto('/');
    await companionPage.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_zuzanna');
      localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
    });
    await companionPage.reload();
    await companionPage.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i }).click();
    await companionPage.getByRole('button', { name: /SOS/i }).first().click();
    const sosModal = companionPage.getByRole('dialog', { name: /Otworzyć opcje pomocy|Open emergency options/i });
    await sosModal.locator('input[type="checkbox"]').check();
    await sosModal.getByRole('button', { name: /Pokaż opcje pomocy|Show help options/i }).click();

    await expect.poll(() => hostFrames.some((frame) => frame.type === 'trip.sos_triggered' && frame.payload?.id === 'trip_makro_01' && frame.payload?.status === 'emergency_sos'), { timeout: 10000 }).toBe(true);
    await hostPage.getByRole('navigation').getByRole('button', { name: /^Aktywne Wyjście$|^Active Trip$/i }).click();
    await expect(hostPage.getByText(/OPCJE POMOCY OTWARTE|HELP OPTIONS OPEN/i).first()).toBeVisible({ timeout: 5000 });
    await expect(hostPage.getByRole('link', { name: /Zadzwoń 112|Call 112/i }).first()).toHaveAttribute('href', 'tel:112');

    await hostContext.close();
    await companionContext.close();
  });
});
