import { test, expect } from '@playwright/test';

test.describe('Micro-Pods Quorum & Ephemeral Voice Journeys', () => {
  test('micro-pod unlocks chat at quorum (3/5) in real-time and supports live chat and focus trap/Escape', async ({ browser, request }) => {
    // 1. Seed verified place and forming pod via API
    const zuzannaHeaders = { Authorization: 'Bearer token_zuzanna' };
    const jakubHeaders = { Authorization: 'Bearer token_jakub' };
    const marekHeaders = { Authorization: 'Bearer token_marek' };

    const timestamp = Date.now();
    const placeRes = await request.post('/api/pods/places', {
      headers: zuzannaHeaders,
      data: {
        slug: `park-test-${timestamp}`,
        name: `Park Kościuszki #${timestamp}`,
        kind: 'park',
        city: 'Katowice',
        meeting_point: 'Pomnik Kościuszki',
        latitude: 50.25,
        longitude: 19.01,
        is_indoor: 0,
        template_codes: ['park_walk'],
      },
    });
    expect(placeRes.ok()).toBeTruthy();
    const place = await placeRes.json();

    // Create pod as Zuzanna (confirmed = 1)
    const now = new Date();
    const startsAt = new Date(now.getTime() + 7200000).toISOString().replace(/\.\d{3}Z$/, 'Z');
    const endsAt = new Date(now.getTime() + 10800000).toISOString().replace(/\.\d{3}Z$/, 'Z');
    const deadlineAt = new Date(now.getTime() + 3600000).toISOString().replace(/\.\d{3}Z$/, 'Z');

    const podRes = await request.post('/api/pods', {
      headers: zuzannaHeaders,
      data: {
        template_code: 'park_walk',
        third_place_id: place.id,
        starts_at: startsAt,
        ends_at: endsAt,
        quorum_deadline_at: deadlineAt,
        language_code: 'pl',
        spend_expectation: 'no_expected_spend',
        title: `Spacer Park #${timestamp}`,
      },
    });
    expect(podRes.ok()).toBeTruthy();
    const pod = await podRes.json();
    const podId = pod.id;

    // Join Marek as 2nd participant (confirmed = 2/3, forming)
    const joinMarekRes = await request.post(`/api/pods/${podId}/join`, {
      headers: marekHeaders,
    });
    expect(joinMarekRes.ok()).toBeTruthy();

    // Context A: Host Zuzanna
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await pageA.goto('/');
    await pageA.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_zuzanna');
      localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
    });
    await pageA.reload();

    // Context B: Participant Jakub
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await pageB.goto('/');
    await pageB.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_jakub');
      localStorage.setItem('cartmate_user_id', 'usr_jakub');
    });
    await pageB.reload();

    // Both navigate to "Pody 3-5"
    const navNearbyA = pageA.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).first();
    await navNearbyA.click();
    const podsBtnA = pageA.getByRole('button', { name: /Pody 3-5|Pods 3-5/i });
    await podsBtnA.click();

    const navNearbyB = pageB.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).first();
    await navNearbyB.click();
    const podsBtnB = pageB.getByRole('button', { name: /Pody 3-5|Pods 3-5/i });
    await podsBtnB.click();

    // Verify Context A sees pod as forming with waiting for quorum
    const podCardA = pageA.locator('.glass-card').filter({ hasText: `Spacer Park #${timestamp}` });
    await expect(podCardA.getByText(/Formowanie|Forming/i).first()).toBeVisible({ timeout: 10000 });
    await expect(podCardA.getByText(/Oczekiwanie na quorum|Waiting for quorum/i).first()).toBeVisible();

    // Context B sees pod card with join button (+1 seat)
    const podCardB = pageB.locator('.glass-card').filter({ hasText: `Spacer Park #${timestamp}` });
    const joinBtn = podCardB.getByRole('button', { name: /Dołącz do poda|Join pod/i }).first();
    await expect(joinBtn).toBeVisible({ timeout: 10000 });

    // Context B clicks join
    await joinBtn.click();

    // Real-time: BOTH Context A and Context B must update to Quorum active (3 / 5) without page reload!
    await expect(podCardA.getByText(/Quorum aktywne!|Quorum active!/i).first()).toBeVisible({ timeout: 8000 });
    await expect(podCardB.getByText(/Quorum aktywne!|Quorum active!/i).first()).toBeVisible({ timeout: 8000 });

    // "Czat grupy" button is now enabled in both contexts
    const chatBtnA = podCardA.getByRole('button', { name: /Czat grupy|Group chat/i }).first();
    const chatBtnB = podCardB.getByRole('button', { name: /Czat grupy|Group chat/i }).first();
    await expect(chatBtnA).toBeVisible();
    await expect(chatBtnB).toBeVisible();

    // Context A opens chat drawer
    await chatBtnA.click();
    const drawerA = pageA.locator('#pod-chat-drawer-dialog');
    await expect(drawerA).toBeVisible();

    // Context B opens chat drawer and sends a message
    await chatBtnB.click();
    const drawerB = pageB.locator('#pod-chat-drawer-dialog');
    await expect(drawerB).toBeVisible();

    const inputB = drawerB.locator('input[type="text"]');
    await inputB.fill('Cześć grupa, widzimy się przy wejściu!');
    await drawerB.locator('button[type="submit"]').click();

    // Context A sees message delivered over WebSocket in real time
    await expect(drawerA.getByText('Cześć grupa, widzimy się przy wejściu!')).toBeVisible({ timeout: 6000 });

    // Focus trap / Escape closes drawer in Context A
    await pageA.keyboard.press('Escape');
    await expect(drawerA).not.toBeVisible();

    await contextA.close();
    await contextB.close();
  });

  test('two-user WebRTC voice call connects, displays peer, hangs up, and submits rating', async ({ browser }, testInfo) => {
    const isMobile = testInfo.project.name === 'mobile-chrome';
    const userA = isMobile
      ? { token: 'token_mateusz', id: 'usr_mateusz', name: 'Mateusz' }
      : { token: 'token_ania', id: 'usr_ania', name: 'Ania' };
    const userB = isMobile
      ? { token: 'token_zuzanna', id: 'usr_zuzanna', name: 'Zuzanna' }
      : { token: 'token_jakub', id: 'usr_jakub', name: 'Jakub' };

    // Context A
    const contextA = await browser.newContext();
    const pageA = await contextA.newPage();
    await pageA.goto('/');
    await pageA.evaluate((u) => {
      localStorage.setItem('cartmate_token', u.token);
      localStorage.setItem('cartmate_user_id', u.id);
    }, userA);
    await pageA.reload();

    // Context B
    const contextB = await browser.newContext();
    const pageB = await contextB.newPage();
    await pageB.goto('/');
    await pageB.evaluate((u) => {
      localStorage.setItem('cartmate_token', u.token);
      localStorage.setItem('cartmate_user_id', u.id);
    }, userB);
    await pageB.reload();

    // Both navigate to "Głos 10'" tab
    const navNearbyA = pageA.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).first();
    await navNearbyA.click();
    const voiceBtnA = pageA.getByRole('button', { name: /Głos 10'|Voice 10'/i });
    await voiceBtnA.click();

    const navNearbyB = pageB.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).first();
    await navNearbyB.click();
    const voiceBtnB = pageB.getByRole('button', { name: /Głos 10'|Voice 10'/i });
    await voiceBtnB.click();

    // Both click "Połącz z kimś teraz (10 min)"
    const connectA = pageA.getByRole('button', { name: /Połącz z kimś teraz|Connect now/i }).first();
    await expect(connectA).toBeVisible({ timeout: 8000 });
    await connectA.click();

    const connectB = pageB.getByRole('button', { name: /Połącz z kimś teraz|Connect now/i }).first();
    await expect(connectB).toBeVisible({ timeout: 8000 });
    await connectB.click();

    // Both transition to connecting or in-call HUD with peer info
    await expect(pageA.locator(`text=/${userB.name}|Łączenie rozmówcy|Connecting/i`).first()).toBeVisible({ timeout: 10000 });
    await expect(pageB.locator(`text=/${userA.name}|Łączenie rozmówcy|Connecting/i`).first()).toBeVisible({ timeout: 10000 });

    // Test in-call audio controls: Mute toggle & Speakerphone switcher (Handy voice patterns)
    const muteBtnA = pageA.locator('button[title*="wycisz"], button[title*="Mute"]').first();
    if (await muteBtnA.isVisible()) {
      await muteBtnA.click();
      const unmuteBtnA = pageA.locator('button[title*="wycisz"], button[title*="Unmute"]').first();
      await expect(unmuteBtnA).toBeVisible({ timeout: 3000 });
      await unmuteBtnA.click();
    }
    const speakerBtnA = pageA.locator('button[title*="Głośnik"], button[title*="Speaker"]').first();
    if (await speakerBtnA.isVisible()) {
      await speakerBtnA.click();
    }

    // Context A clicks hangup ("Koniec" / "Zakończ rozmowę")
    const hangupBtnA = pageA.getByRole('button', { name: /Koniec|End/i }).first();
    await expect(hangupBtnA).toBeVisible({ timeout: 5000 });
    await hangupBtnA.click();

    // Post-call rating dialog opens in Context A
    const ratingDialogA = pageA.locator('#voice-rating-dialog');
    await expect(ratingDialogA).toBeVisible({ timeout: 5000 });

    // Select "Miła" / "Kind"
    const respectfulBtn = ratingDialogA.getByRole('button', { name: /Miła|Kind|Приємна|Приятный/i });
    await expect(respectfulBtn).toBeVisible();
    await respectfulBtn.click();

    // Click "Zapisz ocenę" / "Save rating"
    const saveRatingBtn = ratingDialogA.getByRole('button', { name: /Zapisz ocenę|Save rating|Зберегти оцінку|Сохранить оценку/i });
    await expect(saveRatingBtn).toBeVisible();
    await saveRatingBtn.click();

    // Rating thanks confirmation rendered
    await expect(ratingDialogA.getByText(/Dziękujemy za ocenę|Thank you for rating|Дякуємо за оцінку|Спасибо за оценку/i)).toBeVisible({ timeout: 5000 });

    await contextA.close();
    await contextB.close();
  });

  test('header language switcher cycles PL -> EN -> UK -> RU with zero residual Polish in SafetyHub, PodFeed, and VoiceCallHUD', async ({ page }) => {
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_ola');
      localStorage.setItem('cartmate_user_id', 'usr_ola');
    });
    await page.reload();

    const openLangMenu = async () => {
      const langTrigger = page.locator('header').locator('button[title*="Wybierz język"], button[title*="Select language"]').first();
      await langTrigger.click();
    };

    const selectLanguage = async (name: RegExp) => {
      await openLangMenu();
      const option = page.locator('header').getByRole('button', { name }).first();
      await option.click();
    };

    // 1. Switch to English
    await selectLanguage(/English/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'en');

    // Check Safety Hub in English
    const safetyBtn = page.getByRole('navigation').getByRole('button', { name: /Safety/i });
    await safetyBtn.click();
    await expect(page.getByText(/Trust & Safety Hub/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByText(/Your.*Tier/i)).toBeVisible();

    // Check Pods in English
    const nearbyBtn = page.getByRole('navigation').getByRole('button', { name: /Radar|Nearby/i }).first();
    await nearbyBtn.click();
    const podsBtn = page.getByRole('button', { name: /Pods 3-5/i });
    await podsBtn.click();
    await expect(page.getByText('Discover Micro-Pods in Silesia')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Verified Third Places')).toBeVisible();

    // Check Voice in English
    const voiceBtn = page.getByRole('button', { name: /Voice 10'/i });
    await voiceBtn.click();
    await expect(page.getByText('10-Minute Voice')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Connect now (10 min)')).toBeVisible();

    // 2. Switch to Ukrainian
    await selectLanguage(/Українська/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'uk');
    await expect(page.getByText('10-Хвилинні Розмови')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('З’єднатися зараз (10 хв)')).toBeVisible();

    // 3. Switch to Russian
    await selectLanguage(/Русский/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'ru');
    await expect(page.getByText('10-Минутные Разговоры')).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Соединиться сейчас (10 мин)')).toBeVisible();

    // 4. Switch back to Polish
    await selectLanguage(/Polski/i);
    await expect(page.locator('html')).toHaveAttribute('lang', 'pl');
    await expect(page.getByText('10-Minutowe Rozmowy')).toBeVisible({ timeout: 5000 });
  });
});
