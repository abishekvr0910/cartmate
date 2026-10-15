import { test, expect } from '@playwright/test';

test.describe('Staging No-Demo Outing Publishing, Discovery & PII Shielding Journey', () => {
  test.setTimeout(90_000);
  test.beforeEach(async ({ request }) => {
    // Reset database and clear OTP inbox before every test
    const resetRes = await request.post('/_qa/reset-state');
    expect(resetRes.status()).toBe(200);
  });

  test('no-demo SMS OTP registration, ordinary outing publishing, PII shielding, and women-only ID denial', async ({
    browser,
    request,
  }) => {
    // -------------------------------------------------------------------------
    // 1. Unlisted Phone Numbers Cannot Request OTP (Fail-Closed Staging Gate)
    // -------------------------------------------------------------------------
    const unlistedPhone = '+48600999999';
    const unlistedDirectReq = await request.post('/api/auth/otp/request', {
      data: { identifier: unlistedPhone },
    });
    expect(unlistedDirectReq.status()).toBe(403);
    const unlistedErr = await unlistedDirectReq.json();
    expect(unlistedErr.detail).toBe('Ten numer nie jest dopuszczony do zamkniętych testów CartMate.');

    // Verify unlisted phone has no captured OTP in harness
    const unlistedOtpRes = await request.get(`/_qa/latest-otp?phone=${encodeURIComponent(unlistedPhone)}`);
    expect(unlistedOtpRes.status()).toBe(404);

    // -------------------------------------------------------------------------
    // 2. Allowlisted Account 1 (+48600111001) Completes Real SMS OTP Flow
    // -------------------------------------------------------------------------
    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();

    await hostPage.goto('/');

    // Auth modal is automatically presented for unauthenticated visitor
    const authModal = hostPage.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await expect(authModal).toBeVisible({ timeout: 8000 });
    await expect(authModal.getByText('Błyskawiczne logowanie profilem demo:')).toHaveCount(0);

    // Verify UI also denies unlisted phone numbers
    const loginIdentInput = authModal.getByPlaceholder('np. +48 601 234 567');
    await loginIdentInput.fill(unlistedPhone);
    await authModal.getByRole('button', { name: /Wyślij kod SMS/i }).click();
    await expect(
      authModal.getByText(/Ten numer nie jest dopuszczony do zamkniętych testów CartMate/i).first()
    ).toBeVisible({ timeout: 5000 });

    // Switch to Register tab to establish female gender for women-only UI evaluation
    await authModal.getByRole('button', { name: /Zarejestruj się|Register/i }).click();

    await authModal.locator('input[placeholder="np. Piotr Wiśniewski"]').fill('Kasia Katowice');
    await authModal.locator('input[type="email"]').fill('kasia@cartmate.invalid');
    await authModal.getByPlaceholder('+48 600 000 000').fill('+48600111001');

    // Select female gender (default in form is female)
    const genderSelect = authModal.locator('select').nth(1);
    await genderSelect.selectOption('female');

    // Request SMS OTP via UI
    const getRegOtpBtn = authModal.getByRole('button', { name: /Pobierz kod SMS|Wyślij ponownie/i });
    await expect(getRegOtpBtn).toBeEnabled();
    await getRegOtpBtn.click();

    // Retrieve captured OTP from local test harness
    const hostOtpResponse = await request.get('/_qa/latest-otp?phone=%2B48600111001');
    expect(hostOtpResponse.status()).toBe(200);
    const { code: hostOtpCode } = await hostOtpResponse.json();
    expect(hostOtpCode).toMatch(/^\d{6}$/);

    // Enter genuine OTP code and register
    const regOtpInput = authModal.locator('input[placeholder="Kod SMS (6 cyfr)"]');
    await regOtpInput.fill(hostOtpCode);

    const submitRegBtn = authModal.getByRole('button', { name: /Utwórz nowe konto|Create New Account/i });
    await submitRegBtn.click();

    // Verify successful registration and modal dismissal
    await expect(authModal).not.toBeVisible({ timeout: 10000 });

    // Verify session token is a real server-issued token, never a hardcoded demo token
    const hostToken = await hostPage.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(hostToken).toMatch(/^cmt_[a-f0-9]{40}$/);
    expect(hostToken).not.toContain('demo');
    const hostProfile = await request.get('/api/users/me', {
      headers: { Authorization: `Bearer ${hostToken}` },
    });
    expect(hostProfile.status()).toBe(200);
    expect((await hostProfile.json()).avatar).toBe('');

    // Phone control is not age assurance. Live participation remains closed
    // until the isolated harness simulates a verified provider callback.
    await expect(hostPage.getByText(/Pilot jest wyłącznie dla osób 18\+/i)).toBeVisible();
    const beforeAgeProof = await request.get('/api/pings', {
      headers: { Authorization: `Bearer ${hostToken}` },
    });
    expect(beforeAgeProof.status()).toBe(403);
    const hostAgeProof = await request.post('/_qa/grant-age-proof?phone=%2B48600111001');
    expect(hostAgeProof.status()).toBe(200);
    await hostPage.reload();
    const createdSpot = await request.post('/api/hotspots', {
      headers: { Authorization: `Bearer ${hostToken}` },
      data: {
        city: 'Katowice',
        name: 'Shared Avatar Vote Regression',
        category: 'cafe',
        address: 'Rynek 1, Katowice',
        description: 'Two new accounts share an empty avatar',
      },
    });
    expect(createdSpot.status()).toBe(200);
    expect((await createdSpot.json()).voter_avatars).toContain('');

    // -------------------------------------------------------------------------
    // 3. Verify Ordinary Outing Form Access & Women-Only Disabled Switch
    // -------------------------------------------------------------------------
    // Open Create Outing modal
    const postTabBtn = hostPage.locator('button[title="Dodaj Wyjście"]');
    await expect(postTabBtn).toBeVisible({ timeout: 5000 });
    await postTabBtn.click();

    const createModal = hostPage.locator('div[role="dialog"][aria-labelledby="create-ping-title"]');
    await expect(createModal).toBeVisible({ timeout: 5000 });

    // Assert ordinary outing disclosure is displayed (proves no Bronze verification wall)
    await expect(
      createModal.getByText(/Prywatny pilotaż: tylko zaproszone osoby 18\+|Private pilot: invited adults/i)
    ).toBeVisible();

    // Women-only switch must be visible for female account, but visibly disabled without genuine ID
    const womenOnlyCheckbox = createModal.locator('input[type="checkbox"][aria-label*="Strefę Kobiet"]');
    await expect(womenOnlyCheckbox).toBeVisible();
    await expect(womenOnlyCheckbox).toBeDisabled();

    // Accompanying description explains ID verification requirement
    await expect(
      createModal.getByText(/Wyjścia tylko dla kobiet wymagają weryfikacji tożsamości\. Ta funkcja nie jest jeszcze dostępna\.|Women-only outings require genuine identity verification/i)
    ).toBeVisible();

    // Direct API request with women_only: true must fail closed with HTTP 403
    const directWomenOnlyAttempt = await request.post('/api/pings', {
      headers: { Authorization: `Bearer ${hostToken}` },
      data: {
        category: 'grocery',
        destination_name: 'Silesia City Center & Zara',
        destination_lat: 50.2707,
        destination_lng: 19.0041,
        address: 'ul. Chorzowska 107, Katowice',
        intent_tags: ['#PromocjaWielosztuki'],
        ttl_minutes: 45,
        notes: 'Test women-only denial',
        women_only: true,
      },
    });
    expect(directWomenOnlyAttempt.status()).toBe(403);
    const directWomenOnlyErr = await directWomenOnlyAttempt.json();
    expect(directWomenOnlyErr.detail).toMatch(/Wyjścia tylko dla kobiet wymagają zweryfikowanej tożsamości/i);

    // -------------------------------------------------------------------------
    // 4. Publish Ordinary Outing at a Silesian Public Venue
    // -------------------------------------------------------------------------
    // Use the actual Silesia City Center preset.
    const silesiaPresetBtn = createModal.getByRole('button', { name: 'Silesia City Center & Zara' });
    await silesiaPresetBtn.click();

    await expect(createModal.locator('#create-ping-destination')).toHaveValue('Silesia City Center & Zara');
    await expect(createModal.locator('#create-ping-address')).toHaveValue('ul. Chorzowska 107, Katowice');

    // Select tag and add notes
    await createModal.getByRole('button', { name: '#PromocjaWielosztuki' }).click();
    await createModal.locator('textarea').fill('Wspólne zakupy hurtowe w Silesia City Center. Zapraszam sąsiadów z Katowic!');

    // Submit outing
    const submitPingBtn = createModal.getByRole('button', { name: /Opublikuj na Radarze|Post to Radar/i });
    await submitPingBtn.click();

    await expect(createModal).not.toBeVisible({ timeout: 10000 });

    // Host sees their published outing on the radar
    await expect(hostPage.getByText('Silesia City Center & Zara').first()).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // 5. Account 2 (+48600111002) Discovers Outing with Strict PII Shielding
    // -------------------------------------------------------------------------
    const compContext = await browser.newContext();
    const compPage = await compContext.newPage();

    await compPage.goto('/');

    const compAuthModal = compPage.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await expect(compAuthModal).toBeVisible({ timeout: 8000 });

    // Log in via SMS OTP on "Logowanie" tab
    const compIdentInput = compAuthModal.getByPlaceholder('np. +48 601 234 567');
    await compIdentInput.fill('+48600111002');
    await compAuthModal.getByRole('button', { name: /Wyślij kod SMS/i }).click();

    // Fetch captured OTP for Companion
    const compOtpResponse = await request.get('/_qa/latest-otp?phone=%2B48600111002');
    expect(compOtpResponse.status()).toBe(200);
    const { code: compOtpCode } = await compOtpResponse.json();
    expect(compOtpCode).toMatch(/^\d{6}$/);

    // Verify invalid OTP rejection first (brute-force defense)
    const compOtpInput = compAuthModal.locator('#auth-login-code');
    await compOtpInput.fill('000000');
    await compAuthModal.getByRole('button', { name: /Zweryfikuj i zaloguj/i }).click();
    await expect(
      compAuthModal.getByText(/Nieprawidłowy kod weryfikacyjny|Nieprawidłowy lub wygasły kod/i).first()
    ).toBeVisible({ timeout: 5000 });

    // Enter correct OTP and log in
    await compOtpInput.fill(compOtpCode);
    await compAuthModal.getByRole('button', { name: /Zweryfikuj i zaloguj/i }).click();

    await expect(compAuthModal).not.toBeVisible({ timeout: 10000 });

    const compToken = await compPage.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(compToken).toMatch(/^cmt_[a-f0-9]{40}$/);

    await expect(compPage.getByText(/Pilot jest wyłącznie dla osób 18\+/i)).toBeVisible();
    const compAgeProof = await request.post('/_qa/grant-age-proof?phone=%2B48600111002');
    expect(compAgeProof.status()).toBe(200);
    await compPage.reload();
    const unvotedSpots = await request.get('/api/hotspots?city=Katowice', {
      headers: { Authorization: `Bearer ${compToken}` },
    });
    expect(unvotedSpots.status()).toBe(200);
    const collisionSpot = (await unvotedSpots.json()).find((spot: { name: string }) => spot.name === 'Shared Avatar Vote Regression');
    expect(collisionSpot.user_voted).toBe(false);
    expect(collisionSpot.voter_avatars).toContain('');
    const voteButton = compPage.getByRole('button', { name: 'Głosuj (+1)' }).first();
    await expect(voteButton).toBeVisible();
    await voteButton.click();
    const votedSpots = await request.get('/api/hotspots?city=Katowice', {
      headers: { Authorization: `Bearer ${compToken}` },
    });
    const votedSpot = (await votedSpots.json()).find((spot: { name: string }) => spot.name === 'Shared Avatar Vote Regression');
    expect(votedSpot.user_voted).toBe(true);
    expect(votedSpot.votes_count).toBe(2);

    const immediatePings = await request.get('/api/pings', {
      headers: { Authorization: `Bearer ${compToken}` },
    });
    expect(immediatePings.status()).toBe(200);
    expect((await immediatePings.json()).map((ping: { destination_name: string }) => ping.destination_name))
      .toContain('Silesia City Center & Zara');

    // Companion discovers Host's outing in Katowice
    await expect(compPage.getByText('Silesia City Center & Zara').first()).toBeVisible({ timeout: 10000 });
    await expect(compPage.getByText('#PromocjaWielosztuki').first()).toBeVisible();
    await expect(compPage.getByText('Bez ocen po spotkaniu').first()).toBeVisible();
    await expect(compPage.getByRole('button', { name: /Polub wyjście/i })).toHaveCount(0);

    // --- Strict PII Shielding in Browser 2 DOM ---
    const compPageContent = await compPage.content();
    expect(compPageContent).not.toContain('+48600111001');
    expect(compPageContent).not.toContain('600111001');
    expect(compPageContent).not.toContain('kasia@cartmate.invalid');
    expect(compPageContent).not.toContain('phone_verified_at');
    expect(compPageContent).not.toContain('emergency_contact');

    // --- Strict PII Shielding in Public API Payloads ---
    const pingsApiRes = await request.get('/api/pings', {
      headers: { Authorization: `Bearer ${compToken}` },
    });
    expect(pingsApiRes.status()).toBe(200);
    const pingsList = await pingsApiRes.json();
    const discoveredPing = pingsList.find((p: any) => p.destination_name === 'Silesia City Center & Zara');
    expect(discoveredPing).toBeDefined();

    // Verify Host public profile object in ping payload
    expect(discoveredPing.host).not.toHaveProperty('phone');
    expect(discoveredPing.host).not.toHaveProperty('phone_verified_at');
    expect(discoveredPing.host).not.toHaveProperty('emergency_contact');
    expect(discoveredPing.host).not.toHaveProperty('emergency_contact_phone');
    expect(discoveredPing.host).not.toHaveProperty('email');

    // Verify public directory API does not leak phone_verified_at or phones
    const allUsersRes = await request.get('/api/users/all', {
      headers: { Authorization: `Bearer ${compToken}` },
    });
    expect(allUsersRes.status()).toBe(200);
    const allUsers = await allUsersRes.json();
    for (const u of allUsers) {
      expect(u).not.toHaveProperty('phone');
      expect(u).not.toHaveProperty('phone_verified_at');
      expect(u).not.toHaveProperty('emergency_contact');
    }

    // -------------------------------------------------------------------------
    // 6. Controlled Session Lacking Phone OTP Provenance Cannot Publish (Fail-Closed)
    // -------------------------------------------------------------------------
    // Strip phone_verified_at from Host account to simulate session without OTP provenance
    const stripRes = await request.post('/_qa/strip-phone-verification?phone=%2B48600111001');
    expect(stripRes.status()).toBe(200);

    // Host attempts to publish outing with their existing session
    const unprovenPublishRes = await request.post('/api/pings', {
      headers: { Authorization: `Bearer ${hostToken}` },
      data: {
        category: 'grocery',
        destination_name: 'Biedronka Katowice',
        destination_lat: 50.2649,
        destination_lng: 19.0238,
        address: 'ul. Mariacka 2, Katowice',
        intent_tags: ['#SpokojneZakupy'],
        ttl_minutes: 45,
        notes: 'Unproven account cannot publish',
        women_only: false,
      },
    });

    expect(unprovenPublishRes.status()).toBe(403);
    const unprovenErr = await unprovenPublishRes.json();
    expect(unprovenErr.detail).toBe('Potwierdź numer telefonu kodem SMS lub aktywacją operatora, zanim opublikujesz wyjście.');

    // Clean up browser contexts
    await hostContext.close();
    await compContext.close();
  });

  test('closed pilot requires a one-use invite in the browser and on the server', async ({ page, request }) => {
    const issued = await request.post('/_qa/pilot-invites/enable-and-issue');
    expect(issued.status()).toBe(200);
    const { invite_code: inviteCode } = await issued.json();
    expect(inviteCode).toMatch(/^CM-[A-F0-9]{24}$/);

    const policy = await request.get('/api/config/environment');
    expect(policy.status()).toBe(200);
    expect((await policy.json()).pilot_invite_required).toBe(true);

    const withoutInvite = await request.post('/api/auth/otp/request', {
      data: { identifier: '+48600111001' },
    });
    expect(withoutInvite.status()).toBe(403);

    await page.goto('/');
    const authModal = page.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await expect(authModal).toBeVisible();
    await authModal.getByRole('button', { name: /Zarejestruj się|Register/i }).click();
    const inviteInput = authModal.getByLabel('Kod zaproszenia do pilotażu *');
    await expect(inviteInput).toBeVisible();

    await authModal.locator('input[placeholder="np. Piotr Wiśniewski"]').fill('Pilot Katowice');
    await authModal.locator('input[type="email"]').fill('pilot@cartmate.invalid');
    await authModal.getByPlaceholder('+48 600 000 000').fill('+48600111001');
    await inviteInput.fill(inviteCode);

    await authModal.getByRole('button', { name: /Pobierz kod SMS|Wyślij ponownie/i }).click();
    const otpResponse = await request.get('/_qa/latest-otp?phone=%2B48600111001');
    expect(otpResponse.status()).toBe(200);
    const { code: otpCode } = await otpResponse.json();
    expect(otpCode).toMatch(/^\d{6}$/);
    await authModal.locator('input[placeholder="Kod SMS (6 cyfr)"]').fill(otpCode);
    await authModal.getByRole('button', { name: /Utwórz nowe konto|Create New Account/i }).click();
    await expect(authModal).not.toBeVisible({ timeout: 10000 });

    const token = await page.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(token).toMatch(/^cmt_[a-f0-9]{40}$/);
    const me = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${token}` } });
    expect(me.status()).toBe(200);

    const replay = await request.post('/api/auth/otp/request', {
      data: { identifier: '+48600111002', invite_code: inviteCode },
    });
    expect(replay.status()).toBe(403);
  });
});
