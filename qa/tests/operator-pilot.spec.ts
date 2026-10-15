import { test, expect, Page } from '@playwright/test';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as fs from 'fs';
import * as os from 'os';

interface WsFrame {
  type?: string;
  action?: string;
  payload?: any;
  [key: string]: any;
}

function captureRealtimeFrames(page: Page): WsFrame[] {
  const frames: WsFrame[] = [];
  page.on('websocket', (ws) => {
    ws.on('framereceived', (event) => {
      try {
        const data = JSON.parse(event.payload.toString());
        frames.push(data);
      } catch {}
    });
  });
  return frames;
}

const startHarness = (dbPath: string, port = 8018): ChildProcess => {
  const pythonBin = process.platform === 'win32' ? 'python' : 'python3';
  return spawn(pythonBin, [path.resolve(__dirname, '..', 'operator_pilot_harness.py')], {
    cwd: path.resolve(__dirname, '..'),
    env: {
      ...process.env,
      CARTMATE_OPERATOR_PILOT_PORT: port.toString(),
      CARTMATE_DATABASE_PATH: dbPath,
    },
    stdio: 'ignore',
  });
};

const stopHarness = async (proc: ChildProcess) => {
  if (!proc || proc.exitCode !== null || proc.signalCode !== null) return;
  const exited = new Promise((resolve) => proc.once('exit', resolve));
  if (process.platform === 'win32') {
    try {
      const killer = spawn('taskkill', ['/pid', proc.pid!.toString(), '/f', '/t'], { windowsHide: true, stdio: 'ignore' });
      await new Promise((resolve) => killer.once('exit', resolve));
    } catch {}
  } else {
    try {
      proc.kill('SIGTERM');
    } catch {}
  }
  let timer: NodeJS.Timeout | undefined;
  try {
    await Promise.race([
      exited,
      new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Harness did not exit within timeout')), 8000); }),
    ]);
  } finally {
    if (timer) clearTimeout(timer);
  }
};

const waitForHarness = async (port = 8018, maxMs = 15000) => {
  const start = Date.now();
  while (Date.now() - start < maxMs) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/api/health`);
      if (res.ok) return;
    } catch {}
    await new Promise((r) => setTimeout(r, 200));
  }
  throw new Error(`Harness on port ${port} did not become ready`);
};

test.describe('Staging Operator-Admitted Friend Pilot Journey', () => {
  test.setTimeout(120_000);

  test('two-person operator admission, witnessed 18+ attestation, outing creation, join, mutual trip, live chat, ledger, and cancellation', async ({
    browser,
    request,
  }) => {
    // Reset rate limits for isolated test run
    await request.post('/_op_qa/reset-rate-limits');

    // -------------------------------------------------------------------------
    // 1. Fetch Operator credentials from harness
    // -------------------------------------------------------------------------
    const opCredsRes = await request.get('/_op_qa/operator-credentials');
    expect(opCredsRes.status()).toBe(200);
    const { token: opToken } = await opCredsRes.json();
    const opHeaders = { Authorization: `Bearer ${opToken}` };

    // -------------------------------------------------------------------------
    // 2. Issue fresh single-use CMACT- tokens for Host H and Companion C
    // -------------------------------------------------------------------------
    const hTokRes = await request.post('/_op_qa/issue-token?intended_for=Hubert+Host');
    expect(hTokRes.status()).toBe(200);
    const { token: hActivationToken } = await hTokRes.json();
    expect(hActivationToken).toMatch(/^CMACT-[A-F0-9]{24}$/);

    const cTokRes = await request.post('/_op_qa/issue-token?intended_for=Cezary+Companion');
    expect(cTokRes.status()).toBe(200);
    const { token: cActivationToken } = await cTokRes.json();
    expect(cActivationToken).toMatch(/^CMACT-[A-F0-9]{24}$/);

    // -------------------------------------------------------------------------
    // 3. Setup host and companion browser contexts with frame capture
    // -------------------------------------------------------------------------
    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const hostFrames = captureRealtimeFrames(hostPage);

    const companionContext = await browser.newContext();
    const companionPage = await companionContext.newPage();
    const compFrames = captureRealtimeFrames(companionPage);

    // Record runtime viewport settings
    const hVp = hostPage.viewportSize();
    const cVp = companionPage.viewportSize();
    expect(hVp).toBeTruthy();
    expect(cVp).toBeTruthy();

    // -------------------------------------------------------------------------
    // 4. Host H redeems CMACT- token via AuthModal UI
    // -------------------------------------------------------------------------
    await hostPage.goto('/');
    const hostAuthModal = hostPage.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await expect(hostAuthModal).toBeVisible({ timeout: 10000 });

    const hostActivateTab = hostAuthModal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i });
    await expect(hostActivateTab).toBeVisible();
    await hostActivateTab.click();

    await hostAuthModal.locator('#auth-act-token').fill(hActivationToken);
    await hostAuthModal.locator('#auth-act-name').fill('Hubert Host');
    await hostAuthModal.locator('#auth-act-city').selectOption('Katowice');
    await hostAuthModal.locator('#auth-act-gender').selectOption('male');
    await hostAuthModal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();

    await expect(hostAuthModal).not.toBeVisible({ timeout: 10000 });
    await expect(hostPage.getByRole('heading', { name: /CartMate · 18\+/i })).toBeVisible({ timeout: 10000 });

    const hToken = await hostPage.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(hToken).toMatch(/^cmt_[a-f0-9]{40}$/);
    const hProfile = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${hToken}` } });
    const hUser = await hProfile.json();
    expect(hUser.assurance_marker).toBe('operator_in_person');
    expect(hUser.phone_verified_at).toBeNull();
    expect(hUser.adult_verified_at).toBeNull();

    await hostPage.getByRole('button', { name: /Wygeneruj kod do sprawdzenia 18\+/i }).click();
    const hostChallengeCodeEl = hostPage.locator('p[role="status"] code').last();
    await expect(hostChallengeCodeEl).toBeVisible({ timeout: 5000 });
    const hostChallengeCode = (await hostChallengeCodeEl.textContent())?.trim();
    expect(hostChallengeCode).toBeTruthy();

    // -------------------------------------------------------------------------
    // 5. Companion C redeems CMACT- token via AuthModal UI
    // -------------------------------------------------------------------------
    await companionPage.goto('/');
    const compAuthModal = companionPage.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await expect(compAuthModal).toBeVisible({ timeout: 10000 });

    await compAuthModal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();
    await compAuthModal.locator('#auth-act-token').fill(cActivationToken);
    await compAuthModal.locator('#auth-act-name').fill('Cezary Companion');
    await compAuthModal.locator('#auth-act-city').selectOption('Katowice');
    await compAuthModal.locator('#auth-act-gender').selectOption('male');
    await compAuthModal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();

    await expect(compAuthModal).not.toBeVisible({ timeout: 10000 });
    await expect(companionPage.getByRole('heading', { name: /CartMate · 18\+/i })).toBeVisible({ timeout: 10000 });

    const cToken = await companionPage.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(cToken).toMatch(/^cmt_[a-f0-9]{40}$/);
    const cProfile = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${cToken}` } });
    const cUser = await cProfile.json();

    await companionPage.getByRole('button', { name: /Wygeneruj kod do sprawdzenia 18\+/i }).click();
    const compChallengeCodeEl = companionPage.locator('p[role="status"] code').last();
    await expect(compChallengeCodeEl).toBeVisible({ timeout: 5000 });
    const compChallengeCode = (await compChallengeCodeEl.textContent())?.trim();
    expect(compChallengeCode).toBeTruthy();

    // -------------------------------------------------------------------------
    // 6. Operator O records witnessed adult attestation with challenges
    // -------------------------------------------------------------------------
    const attestH = await request.post(`/api/moderation/users/${hUser.id}/adult-attestation`, {
      headers: opHeaders,
      data: {
        method: 'physical_identity_document',
        confirmed_over_18: true,
        subject_present: true,
        subject_consented: true,
        account_bound: true,
        account_challenge: hostChallengeCode,
      },
    });
    expect(attestH.status()).toBe(200);

    const attestC = await request.post(`/api/moderation/users/${cUser.id}/adult-attestation`, {
      headers: opHeaders,
      data: {
        method: 'physical_identity_document',
        confirmed_over_18: true,
        subject_present: true,
        subject_consented: true,
        account_bound: true,
        account_challenge: compChallengeCode,
      },
    });
    expect(attestC.status()).toBe(200);

    // -------------------------------------------------------------------------
    // 7. Both click "Sprawdź ponownie" and enter the app without reload
    // -------------------------------------------------------------------------
    await hostPage.getByRole('button', { name: /Sprawdź ponownie/i }).click();
    await expect(hostPage.getByRole('heading', { name: /CartMate · 18\+/i })).not.toBeVisible({ timeout: 10000 });

    await companionPage.getByRole('button', { name: /Sprawdź ponownie/i }).click();
    await expect(companionPage.getByRole('heading', { name: /CartMate · 18\+/i })).not.toBeVisible({ timeout: 10000 });

    // Wait briefly for WebSocket handshake
    await expect.poll(() => compFrames.some((f) => f.type === 'connection.ready'), { timeout: 10000 }).toBe(true);

    // -------------------------------------------------------------------------
    // 8. Host H creates an outing via UI
    // -------------------------------------------------------------------------
    const newPingNavBtn = hostPage.locator('button[title*="Wyjście"], nav button').filter({ hasText: /Wyjście/i }).first();
    await newPingNavBtn.click();
    const createPingDialog = hostPage.locator('#create-ping-dialog');
    await expect(createPingDialog).toBeVisible({ timeout: 6000 });

    const presetBtn = createPingDialog.locator('button[type="button"]').filter({ hasText: /Makro|Biedronka|IKEA/i }).first();
    await presetBtn.click();
    const submitPingBtn = createPingDialog.locator('button[type="submit"]');
    await submitPingBtn.click();
    await expect(createPingDialog).not.toBeVisible({ timeout: 8000 });

    // -------------------------------------------------------------------------
    // 9. Companion C receives outing live via WebSocket without page reload!
    // -------------------------------------------------------------------------
    const hostPingCard = companionPage.locator(`text=${hUser.name}`).first();
    await expect(hostPingCard).toBeVisible({ timeout: 10000 });
    expect(compFrames.some((f) => f.type === 'ping.created')).toBe(true);

    // Companion clicks Join on the ping card
    const joinBtn = companionPage.locator('button').filter({ hasText: /Dołącz/i }).first();
    await joinBtn.click();
    const joinModal = companionPage.locator('div[role="dialog"][aria-labelledby="join-request-modal-title"]');
    await expect(joinModal).toBeVisible({ timeout: 5000 });
    const sendJoinBtn = joinModal.getByRole('button', { name: /Wyślij zgłoszenie|Dołącz/i });
    await sendJoinBtn.click();
    await expect(joinModal).not.toBeVisible({ timeout: 5000 });

    // -------------------------------------------------------------------------
    // 10. Host H reviews requests and accepts Companion in Host UI!
    // -------------------------------------------------------------------------
    const requestsBtn = hostPage.locator('button').filter({ hasText: /Zgłoszenia/i }).first();
    await expect(requestsBtn).toBeVisible({ timeout: 10000 });
    await requestsBtn.click();

    const hostReviewModal = hostPage.locator('div[role="dialog"][aria-labelledby="host-review-modal-title"]');
    await expect(hostReviewModal).toBeVisible({ timeout: 5000 });
    const acceptCompanionBtn = hostReviewModal.getByRole('button', { name: /Zaakceptuj/i });
    await expect(acceptCompanionBtn).toBeVisible({ timeout: 5000 });
    await acceptCompanionBtn.click();

    // -------------------------------------------------------------------------
    // 11. Both pages navigate into Active Trip HUD without reload!
    // -------------------------------------------------------------------------
    await expect(hostPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });
    await expect(companionPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // 12. Host updates plan to 50/50 split policy & both accept in UI
    // -------------------------------------------------------------------------
    const whenInput = hostPage.locator('input[placeholder*="27.09"]');
    await expect(whenInput).toBeVisible({ timeout: 5000 });
    await whenInput.fill('Dziś o 18:00 przy kasach');

    const policySelect = hostPage.locator('form label select');
    await expect(policySelect).toBeVisible({ timeout: 5000 });
    await policySelect.selectOption('split_strictly_50_50');
    await hostPage.getByRole('button', { name: /Zapisz plan i poproś o akceptację/i }).click();

    const hostAcceptPlanBtn = hostPage.getByRole('button', { name: /Akceptuję warunki spotkania/i });
    await expect(hostAcceptPlanBtn).toBeVisible({ timeout: 5000 });
    await hostAcceptPlanBtn.click();

    const compAcceptPlanBtn = companionPage.getByRole('button', { name: /Akceptuję warunki spotkania/i });
    await expect(compAcceptPlanBtn).toBeVisible({ timeout: 5000 });
    await compAcceptPlanBtn.click();

    await expect(hostPage.getByText(/Plan zaakceptowany/i)).toBeVisible({ timeout: 10000 });
    await expect(companionPage.getByText(/Plan zaakceptowany/i)).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // 13. Check-in & PIN Handshake in UI
    // -------------------------------------------------------------------------
    const hostArrivedBtn = hostPage.getByRole('button', { name: /Jestem na miejscu/i });
    await expect(hostArrivedBtn).toBeVisible({ timeout: 5000 });
    await hostArrivedBtn.click();

    // Host sees the revealed 4-digit PIN in UI
    const hostPinEl = hostPage.locator('span.font-mono.tracking-widest');
    await expect(hostPinEl).toBeVisible({ timeout: 5000 });
    const revealedPin = (await hostPinEl.textContent())?.trim();
    expect(revealedPin).toMatch(/^\d{4}$/);

    // Companion enters the PIN verbally shared by Host in UI
    const compPinInput = companionPage.locator('input[placeholder="0000"]');
    await expect(compPinInput).toBeVisible({ timeout: 5000 });
    await compPinInput.fill(revealedPin!);
    await companionPage.getByRole('button', { name: /Potwierdź Spotkanie/i }).click();

    // Verify PIN verified status appears on both pages
    await expect(hostPage.getByText(/Wpisano zgodny PIN/i).first()).toBeVisible({ timeout: 10000 });
    await expect(companionPage.getByText(/Wpisano zgodny PIN/i).first()).toBeVisible({ timeout: 10000 });

    // -------------------------------------------------------------------------
    // 14. Live In-App Coordination Chat in UI
    // -------------------------------------------------------------------------
    // The companion can browse other tabs without losing private trip-chat
    // activity; the cue is only a local in-app indicator, not a read receipt.
    await companionPage.getByRole('navigation').getByRole('button', { name: 'W pobliżu' }).click();
    const hostChatInput = hostPage.locator('input[placeholder*="czarnej kurtce"]');
    await hostChatInput.fill('Hej Cezary! Czekam przy wejściu do Makro.');
    await hostPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();

    await expect(hostPage.locator('text=Hej Cezary! Czekam przy wejściu do Makro.').first()).toBeVisible({ timeout: 5000 });
    const tripWithNewMessage = companionPage.getByRole('navigation').getByRole('button', { name: /Aktywne Wyjście, Nowa wiadomość od osoby towarzyszącej/i });
    await expect(tripWithNewMessage).toBeVisible({ timeout: 10000 });
    await tripWithNewMessage.click();
    await expect(companionPage.getByRole('navigation').getByRole('button', { name: 'Aktywne Wyjście' })).toBeVisible();
    await expect(companionPage.locator('text=Hej Cezary! Czekam przy wejściu do Makro.').first()).toBeVisible({ timeout: 10000 });

    const compChatInput = companionPage.locator('input[placeholder*="czarnej kurtce"]');
    await compChatInput.fill('Cześć Hubert! Już podchodzę.');
    await companionPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();

    await expect(hostPage.locator('text=Cześć Hubert! Już podchodzę.').first()).toBeVisible({ timeout: 10000 });
    expect(compFrames.some((f) => f.type === 'chat.message')).toBe(true);

    // -------------------------------------------------------------------------
    // 15. 50/50 Ledger Item Entry in UI
    // -------------------------------------------------------------------------
    const addSplitBtn = hostPage.getByRole('button', { name: /Dodaj pozycję/i });
    await expect(addSplitBtn).toBeVisible({ timeout: 5000 });
    await addSplitBtn.click();
    const splitDialog = hostPage.locator('#trip-split-dialog');
    await expect(splitDialog).toBeVisible({ timeout: 5000 });
    await hostPage.locator('#trip-split-item-name').fill('Kawa i herbata Makro');
    await hostPage.locator('#trip-split-item-price').fill('40.00');
    await splitDialog.locator('button[type="submit"]').click();
    await expect(splitDialog).not.toBeVisible({ timeout: 5000 });

    // Assert split item visible on BOTH Host and Companion screens
    await expect(hostPage.getByText(/Kawa i herbata Makro/i).first()).toBeVisible({ timeout: 5000 });
    await expect(companionPage.getByText(/Kawa i herbata Makro/i).first()).toBeVisible({ timeout: 5000 });

    // Assert total split 40.00 zł and net settlement 20.00 zł on BOTH screens
    await expect(hostPage.getByText(/40\.00\s*zł/).first()).toBeVisible({ timeout: 5000 });
    await expect(companionPage.getByText(/40\.00\s*zł/).first()).toBeVisible({ timeout: 5000 });
    await expect(hostPage.getByText(/20\.00\s*zł/).first()).toBeVisible({ timeout: 5000 });
    await expect(companionPage.getByText(/20\.00\s*zł/).first()).toBeVisible({ timeout: 5000 });

    // -------------------------------------------------------------------------
    // 16. Low-Guilt Cancellation in UI
    // -------------------------------------------------------------------------
    await hostPage.getByRole('button', { name: /Zrezygnuj z wyjścia/i }).click();
    const cancelModal = hostPage.locator('#trip-cancel-dialog');
    await expect(cancelModal).toBeVisible({ timeout: 5000 });
    await cancelModal.locator('button').filter({ hasText: /Potwierdź rezygnację/i }).click();

    // Verify both Host and Companion Active Trip HUD clears without reload, and status notice appears
    await expect(hostPage.getByRole('status').filter({ hasText: /Wyjście zostało anulowane/i }).first()).toBeVisible({ timeout: 10000 });
    await expect(companionPage.getByRole('status').filter({ hasText: /Wyjście zostało anulowane/i }).first()).toBeVisible({ timeout: 10000 });

    // Clean up contexts
    await hostContext.close();
    await companionContext.close();
  });

  test('operator recovery restores same account after session loss (CR-01)', async ({
    browser,
    request,
  }) => {
    await request.post('/_op_qa/reset-rate-limits');

    // 1. Issue activation token and redeem
    const tokRes = await request.post('/_op_qa/issue-token?intended_for=Ewa+Existing');
    const { token: actToken } = await tokRes.json();

    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto('/');

    const authModal = page.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await expect(authModal).toBeVisible({ timeout: 10000 });
    await authModal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();

    await authModal.locator('#auth-act-token').fill(actToken);
    await authModal.locator('#auth-act-name').fill('Ewa Existing');
    await authModal.locator('#auth-act-city').selectOption('Katowice');
    await authModal.locator('#auth-act-gender').selectOption('female');
    await authModal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();

    await expect(authModal).not.toBeVisible({ timeout: 10000 });
    const originalToken = await page.evaluate(() => localStorage.getItem('cartmate_token'));
    const originalProfile = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${originalToken}` } });
    const originalUser = await originalProfile.json();

    // 2. Clear token to simulate logout / cleared local storage
    await page.evaluate(() => localStorage.removeItem('cartmate_token'));
    await page.reload();

    await expect(authModal).toBeVisible({ timeout: 10000 });

    // 3. Issue recovery token bound to original user ID
    const recRes = await request.post(`/_op_qa/issue-recovery-token?user_id=${originalUser.id}&intended_for=Ewa+Existing`);
    expect(recRes.status()).toBe(200);
    const { token: recToken } = await recRes.json();
    expect(recToken).toMatch(/^CMREC-[A-F0-9]{24}$/);

    // 4. Redeem recovery token via AuthModal UI
    await authModal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();
    await authModal.locator('#auth-act-token').fill(recToken);
    await authModal.locator('#auth-act-name').fill('Ewa Existing');
    await authModal.locator('#auth-act-city').selectOption('Katowice');
    await authModal.locator('#auth-act-gender').selectOption('female');
    await authModal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();

    await expect(authModal).not.toBeVisible({ timeout: 10000 });

    // 5. Verify restored session is bound to the SAME user ID
    const restoredToken = await page.evaluate(() => localStorage.getItem('cartmate_token'));
    expect(restoredToken).toMatch(/^cmt_[a-f0-9]{40}$/);
    const restoredProfile = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${restoredToken}` } });
    const restoredUser = await restoredProfile.json();
    expect(restoredUser.id).toBe(originalUser.id);
    expect(restoredUser.name).toBe('Ewa Existing');

    await context.close();
  });

  test('second outing journey: discovery, mutual match, and companion cancellation (R2-03)', async ({
    browser,
    request,
  }) => {
    await request.post('/_op_qa/reset-rate-limits');

    const opCredsRes = await request.get('/_op_qa/operator-credentials');
    const { token: opToken } = await opCredsRes.json();
    const opHeaders = { Authorization: `Bearer ${opToken}` };

    const hTok = (await (await request.post('/_op_qa/issue-token?intended_for=Helena+Host')).json()).token;
    const cTok = (await (await request.post('/_op_qa/issue-token?intended_for=Celina+Companion')).json()).token;

    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const compContext = await browser.newContext();
    const compPage = await compContext.newPage();

    // Enroll Helena
    await hostPage.goto('/');
    const hModal = hostPage.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await hModal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();
    await hModal.locator('#auth-act-token').fill(hTok);
    await hModal.locator('#auth-act-name').fill('Helena Host');
    await hModal.locator('#auth-act-city').selectOption('Katowice');
    await hModal.locator('#auth-act-gender').selectOption('female');
    await hModal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();
    await expect(hModal).not.toBeVisible({ timeout: 10000 });

    const hSession = await hostPage.evaluate(() => localStorage.getItem('cartmate_token'));
    const hUser = await (await request.get('/api/users/me', { headers: { Authorization: `Bearer ${hSession}` } })).json();
    await hostPage.getByRole('button', { name: /Wygeneruj kod do sprawdzenia 18\+/i }).click();
    const hChallenge = (await hostPage.locator('p[role="status"] code').last().textContent())?.trim();

    // Enroll Celina
    await compPage.goto('/');
    const cModal = compPage.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await cModal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();
    await cModal.locator('#auth-act-token').fill(cTok);
    await cModal.locator('#auth-act-name').fill('Celina Companion');
    await cModal.locator('#auth-act-city').selectOption('Katowice');
    await cModal.locator('#auth-act-gender').selectOption('female');
    await cModal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();
    await expect(cModal).not.toBeVisible({ timeout: 10000 });

    const cSession = await compPage.evaluate(() => localStorage.getItem('cartmate_token'));
    const cUser = await (await request.get('/api/users/me', { headers: { Authorization: `Bearer ${cSession}` } })).json();
    await compPage.getByRole('button', { name: /Wygeneruj kod do sprawdzenia 18\+/i }).click();
    const cChallenge = (await compPage.locator('p[role="status"] code').last().textContent())?.trim();

    // Attest both
    await request.post(`/api/moderation/users/${hUser.id}/adult-attestation`, {
      headers: opHeaders,
      data: { method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: hChallenge },
    });
    await request.post(`/api/moderation/users/${cUser.id}/adult-attestation`, {
      headers: opHeaders,
      data: { method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: cChallenge },
    });

    await hostPage.getByRole('button', { name: /Sprawdź ponownie/i }).click();
    await compPage.getByRole('button', { name: /Sprawdź ponownie/i }).click();
    await expect(hostPage.getByRole('heading', { name: /CartMate · 18\+/i })).not.toBeVisible({ timeout: 10000 });
    await expect(compPage.getByRole('heading', { name: /CartMate · 18\+/i })).not.toBeVisible({ timeout: 10000 });

    // Host creates ping
    const newPingBtn = hostPage.locator('button[title*="Wyjście"], nav button').filter({ hasText: /Wyjście/i }).first();
    await newPingBtn.click();
    const createPingDialog = hostPage.locator('#create-ping-dialog');
    await expect(createPingDialog).toBeVisible({ timeout: 6000 });
    await createPingDialog.locator('button[type="button"]').filter({ hasText: /IKEA|Biedronka|Makro/i }).first().click();
    await createPingDialog.locator('button[type="submit"]').click();
    await expect(createPingDialog).not.toBeVisible({ timeout: 8000 });

    // Celina joins
    const card = compPage.locator(`text=${hUser.name}`).first();
    await expect(card).toBeVisible({ timeout: 10000 });
    await compPage.locator('button').filter({ hasText: /Dołącz/i }).first().click();
    const joinModal = compPage.locator('div[role="dialog"][aria-labelledby="join-request-modal-title"]');
    await expect(joinModal).toBeVisible({ timeout: 5000 });
    await joinModal.getByRole('button', { name: /Wyślij zgłoszenie|Dołącz/i }).click();
    await expect(joinModal).not.toBeVisible({ timeout: 5000 });

    // Helena accepts
    const reqBtn = hostPage.locator('button').filter({ hasText: /Zgłoszenia/i }).first();
    await expect(reqBtn).toBeVisible({ timeout: 10000 });
    await reqBtn.click();
    const revModal = hostPage.locator('div[role="dialog"][aria-labelledby="host-review-modal-title"]');
    await expect(revModal).toBeVisible({ timeout: 5000 });
    await revModal.getByRole('button', { name: /Zaakceptuj/i }).click();

    // Both in Active Trip HUD
    await expect(hostPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });
    await expect(compPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });

    // Celina cancels as companion (low-guilt cancellation)
    const compCancelBtn = compPage.getByRole('button', { name: /Zrezygnuj z wyjścia/i });
    await expect(compCancelBtn).toBeVisible({ timeout: 10000 });
    await compCancelBtn.click();
    const cancelDialog = compPage.locator('#trip-cancel-dialog');
    await expect(cancelDialog).toBeVisible({ timeout: 5000 });
    await cancelDialog.locator('button').filter({ hasText: /Potwierdź rezygnację/i }).click();

    // Both screens clear active trip and display cancellation notice
    await expect(compPage.getByRole('status').filter({ hasText: /Wyjście zostało anulowane/i }).first()).toBeVisible({ timeout: 10000 });
    await expect(hostPage.getByRole('status').filter({ hasText: /Wyjście zostało anulowane/i }).first()).toBeVisible({ timeout: 10000 });

    await hostContext.close();
    await compContext.close();
  });

  test('third outing journey: mutual completion, idempotent complete, and private follow-up until mutual opt-in (RT-08 completion)', async ({
    browser,
    request,
  }) => {
    await request.post('/_op_qa/reset-rate-limits');

    const opCredsRes = await request.get('/_op_qa/operator-credentials');
    const { token: opToken } = await opCredsRes.json();
    const opHeaders = { Authorization: `Bearer ${opToken}` };

    const hTok = (await (await request.post('/_op_qa/issue-token?intended_for=Kamil+Komplet')).json()).token;
    const cTok = (await (await request.post('/_op_qa/issue-token?intended_for=Kamila+Komplet')).json()).token;

    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const compContext = await browser.newContext();
    const compPage = await compContext.newPage();
    const compFrames = captureRealtimeFrames(compPage);

    const enrollOne = async (page: Page, tok: string, name: string) => {
      await page.goto('/');
      const modal = page.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
      await modal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();
      await modal.locator('#auth-act-token').fill(tok);
      await modal.locator('#auth-act-name').fill(name);
      await modal.locator('#auth-act-city').selectOption('Katowice');
      await modal.locator('#auth-act-gender').selectOption('male');
      await modal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();
      await expect(modal).not.toBeVisible({ timeout: 10000 });
      const session = await page.evaluate(() => localStorage.getItem('cartmate_token'));
      const user = await (await request.get('/api/users/me', { headers: { Authorization: `Bearer ${session}` } })).json();
      await page.getByRole('button', { name: /Wygeneruj kod do sprawdzenia 18\+/i }).click();
      const ch = (await page.locator('p[role="status"] code').last().textContent())?.trim();
      await request.post(`/api/moderation/users/${user.id}/adult-attestation`, {
        headers: opHeaders,
        data: { method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: ch },
      });
      await page.getByRole('button', { name: /Sprawdź ponownie/i }).click();
      await expect(page.getByRole('heading', { name: /CartMate · 18\+/i })).not.toBeVisible({ timeout: 10000 });
      return { user, session };
    };

    const { user: hUser, session: hSession } = await enrollOne(hostPage, hTok, 'Kamil Komplet');
    const { user: cUser, session: cSession } = await enrollOne(compPage, cTok, 'Kamila Komplet');

    // Host creates outing
    const newPingBtn = hostPage.locator('button[title*="Wyjście"], nav button').filter({ hasText: /Wyjście/i }).first();
    await newPingBtn.click();
    const createPingDialog = hostPage.locator('#create-ping-dialog');
    await expect(createPingDialog).toBeVisible({ timeout: 6000 });
    await createPingDialog.locator('button[type="button"]').filter({ hasText: /Makro|Biedronka/i }).first().click();
    await createPingDialog.locator('button[type="submit"]').click();
    await expect(createPingDialog).not.toBeVisible({ timeout: 8000 });

    // Companion joins
    const card = compPage.locator(`text=${hUser.name}`).first();
    await expect(card).toBeVisible({ timeout: 10000 });
    await compPage.locator('button').filter({ hasText: /Dołącz/i }).first().click();
    const joinModal = compPage.locator('div[role="dialog"][aria-labelledby="join-request-modal-title"]');
    await joinModal.getByRole('button', { name: /Wyślij zgłoszenie|Dołącz/i }).click();

    // Host accepts
    const reqBtn = hostPage.locator('button').filter({ hasText: /Zgłoszenia/i }).first();
    await expect(reqBtn).toBeVisible({ timeout: 10000 });
    await reqBtn.click();
    const revModal = hostPage.locator('div[role="dialog"][aria-labelledby="host-review-modal-title"]');
    await revModal.getByRole('button', { name: /Zaakceptuj/i }).click();

    await expect(hostPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });
    await expect(compPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });

    // Host sets concrete meeting plan
    const whenInput = hostPage.locator('input[placeholder*="27.09"]');
    await expect(whenInput).toBeVisible({ timeout: 5000 });
    await whenInput.fill('Dziś o 19:00 przy wejściu');
    await hostPage.getByRole('button', { name: /Zapisz plan i poproś o akceptację/i }).click();

    // Both accept plan
    const hostAcceptPlanBtn = hostPage.getByRole('button', { name: /Akceptuję warunki spotkania/i });
    await expect(hostAcceptPlanBtn).toBeVisible({ timeout: 5000 });
    await hostAcceptPlanBtn.click();
    const compAcceptPlanBtn = compPage.getByRole('button', { name: /Akceptuję warunki spotkania/i });
    await expect(compAcceptPlanBtn).toBeVisible({ timeout: 5000 });
    await compAcceptPlanBtn.click();

    await expect(hostPage.getByText(/Plan zaakceptowany/i).first()).toBeVisible({ timeout: 10000 });
    await expect(compPage.getByText(/Plan zaakceptowany/i).first()).toBeVisible({ timeout: 10000 });

    // Host check-in reveals PIN
    await hostPage.getByRole('button', { name: /Jestem na miejscu/i }).click();
    const hostPinEl = hostPage.locator('span.font-mono.tracking-widest');
    await expect(hostPinEl).toBeVisible({ timeout: 6000 });
    const pinCode = (await hostPinEl.textContent())?.trim();
    expect(pinCode).toMatch(/^\d{4}$/);

    // Companion enters PIN
    const companionPinInput = compPage.locator('input[placeholder="0000"]');
    await expect(companionPinInput).toBeVisible({ timeout: 5000 });
    await companionPinInput.fill(pinCode!);
    await compPage.getByRole('button', { name: /Potwierdź spotkanie/i }).click();

    await expect(hostPage.getByText(/Wpisano zgodny PIN/i).first()).toBeVisible({ timeout: 10000 });
    await expect(compPage.getByText(/Wpisano zgodny PIN/i).first()).toBeVisible({ timeout: 10000 });

    // Retrieve active trip ID
    const activeTripRes = await request.get('/api/trips/active/current', { headers: { Authorization: `Bearer ${hSession}` } });
    expect(activeTripRes.status()).toBe(200);
    const tripId = (await activeTripRes.json()).id;
    expect(tripId).toBeTruthy();

    // Verify completion count before completion
    const hostProfileBeforeRes = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${hSession}` } });
    const compProfileBeforeRes = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${cSession}` } });
    const hostCompletedBefore = (await hostProfileBeforeRes.json()).trips_completed || 0;
    const compCompletedBefore = (await compProfileBeforeRes.json()).trips_completed || 0;

    // Host completes outing via UI
    const hostDialogs: string[] = [];
    hostPage.on('dialog', (dialog) => {
      hostDialogs.push(dialog.message());
      dialog.accept();
    });
    const finishBtn = hostPage.getByRole('button', { name: /Zakończ wyjście/i }).first();
    await expect(finishBtn).toBeVisible({ timeout: 5000 });
    await finishBtn.click();

    const reviewDialog = hostPage.locator('#trip-review-dialog');
    await expect(reviewDialog).toBeVisible({ timeout: 5000 });

    // Host rates 5 stars, selects would meet again, adds exact private vibe tag and note
    await reviewDialog.getByRole('button', { name: '5 / 5' }).click();
    const hostMeetBtn = reviewDialog.getByRole('button', { name: /Tak, chętnie/i });
    await hostMeetBtn.scrollIntoViewIfNeeded();
    await hostMeetBtn.click();
    await expect(hostMeetBtn).toHaveAttribute('aria-pressed', 'true');
    // Select exact private vibe tag (without emoji) and populate unique private note
    await reviewDialog.getByRole('button', { name: 'Punktualność', exact: true }).click();
    const privateNoteInput = reviewDialog.locator('input[placeholder*="prywatna notatka"]');
    await privateNoteInput.fill('Prywatna notatka gospodarza 98765');
    const hostSubmitBtn = reviewDialog.getByRole('button', { name: /Zapisz ocenę i zakończ/i });
    await hostSubmitBtn.scrollIntoViewIfNeeded();
    await hostSubmitBtn.click();
    await expect(reviewDialog).not.toBeVisible({ timeout: 8000 });

    // Verify Host completed count increased by exactly 1
    const hostProfileAfterRes = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${hSession}` } });
    const hostCompletedAfter = (await hostProfileAfterRes.json()).trips_completed || 0;
    expect(hostCompletedAfter).toBe(hostCompletedBefore + 1);

    // 1. Assert idempotent completion: calling /complete again returns 200 without error and does NOT increment completion count
    const idempRes = await request.post(`/api/trips/${tripId}/complete`, {
      headers: { Authorization: `Bearer ${hSession}` },
    });
    expect(idempRes.status()).toBe(200);
    const idempData = await idempRes.json();
    expect(idempData.status).toBe('completed');

    const hostProfileSecondRes = await request.get('/api/users/me', { headers: { Authorization: `Bearer ${hSession}` } });
    expect((await hostProfileSecondRes.json()).trips_completed).toBe(hostCompletedAfter);

    // 2. Assert private answers until mutual opt-in:
    // Host checks their own trip view: sees their own follow-up feedback and vibe tag
    const hostTripRes = await request.get(`/api/trips/${tripId}`, {
      headers: { Authorization: `Bearer ${hSession}` },
    });
    expect(hostTripRes.status()).toBe(200);
    const hostTripData = await hostTripRes.json();
    expect(JSON.stringify(hostTripData)).toContain('Prywatna notatka gospodarza 98765');
    expect(JSON.stringify(hostTripData)).toContain('Punktualność');

    // Companion checks trip: is_mutual_buddy is false and Host's private follow-up answers are not disclosed in REST or WS
    const compTripRes = await request.get(`/api/trips/${tripId}`, {
      headers: { Authorization: `Bearer ${cSession}` },
    });
    expect(compTripRes.status()).toBe(200);
    const compTripData = await compTripRes.json();
    expect(compTripData.is_mutual_buddy).toBe(false);
    expect(JSON.stringify(compTripData)).not.toContain('Prywatna notatka gospodarza 98765');
    expect(JSON.stringify(compTripData)).not.toContain('Punktualność');
    // Companion does not see host's unilateral would_meet_again answer in follow_ups
    const compFollowUps = compTripData.follow_ups || {};
    expect(compFollowUps[hUser.id]).toBeUndefined();

    // Assert absence of host's private follow-up tags and note in companion's WebSocket frames
    const leakedFrame = compFrames.some((f) => {
      const s = JSON.stringify(f);
      return s.includes('Prywatna notatka gospodarza 98765') || s.includes('Punktualność');
    });
    expect(leakedFrame).toBe(false);

    // Companion now submits follow-up via UI
    compPage.on('dialog', (dialog) => dialog.accept());
    const compFinishBtn = compPage.getByRole('button', { name: /Zakończ wyjście/i }).first();
    await expect(compFinishBtn).toBeVisible({ timeout: 5000 });
    await compFinishBtn.click();

    const compReviewDialog = compPage.locator('#trip-review-dialog');
    await expect(compReviewDialog).toBeVisible({ timeout: 5000 });
    await compReviewDialog.getByRole('button', { name: '5 / 5' }).click();
    const compMeetBtn = compReviewDialog.getByRole('button', { name: /Tak, chętnie/i });
    await compMeetBtn.scrollIntoViewIfNeeded();
    await compMeetBtn.click();
    await expect(compMeetBtn).toHaveAttribute('aria-pressed', 'true');
    const compSubmitBtn = compReviewDialog.getByRole('button', { name: /Zapisz ocenę i zakończ/i });
    await compSubmitBtn.scrollIntoViewIfNeeded();
    await compSubmitBtn.click();
    await expect(compReviewDialog).not.toBeVisible({ timeout: 8000 });

    // 3. Now both opted in -> mutual shopping buddy confirmed!
    await expect.poll(async () => {
      const res = await request.get(`/api/trips/${tripId}`, {
        headers: { Authorization: `Bearer ${hSession}` },
      });
      if (res.status() !== 200) return false;
      const data = await res.json();
      return data.is_mutual_buddy;
    }, { timeout: 10000 }).toBe(true);

    await hostContext.close();
    await compContext.close();
  });

  test('browser reload/rehydration and state convergence without duplicate chat (RT-09 reload)', async ({
    browser,
    request,
  }) => {
    await request.post('/_op_qa/reset-rate-limits');

    const opCredsRes = await request.get('/_op_qa/operator-credentials');
    const { token: opToken } = await opCredsRes.json();
    const opHeaders = { Authorization: `Bearer ${opToken}` };

    const hTok = (await (await request.post('/_op_qa/issue-token?intended_for=Dariusz+Disconnect')).json()).token;
    const cTok = (await (await request.post('/_op_qa/issue-token?intended_for=Dorota+Disconnect')).json()).token;

    const hostContext = await browser.newContext();
    const hostPage = await hostContext.newPage();
    const compContext = await browser.newContext();
    const compPage = await compContext.newPage();

    const enrollOne = async (page: Page, tok: string, name: string) => {
      await page.goto('/');
      const modal = page.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
      await modal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();
      await modal.locator('#auth-act-token').fill(tok);
      await modal.locator('#auth-act-name').fill(name);
      await modal.locator('#auth-act-city').selectOption('Katowice');
      await modal.locator('#auth-act-gender').selectOption('male');
      await modal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();
      await expect(modal).not.toBeVisible({ timeout: 10000 });
      const session = await page.evaluate(() => localStorage.getItem('cartmate_token'));
      const user = await (await request.get('/api/users/me', { headers: { Authorization: `Bearer ${session}` } })).json();
      await page.getByRole('button', { name: /Wygeneruj kod do sprawdzenia 18\+/i }).click();
      const ch = (await page.locator('p[role="status"] code').last().textContent())?.trim();
      await request.post(`/api/moderation/users/${user.id}/adult-attestation`, {
        headers: opHeaders,
        data: { method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: ch },
      });
      await page.getByRole('button', { name: /Sprawdź ponownie/i }).click();
      await expect(page.getByRole('heading', { name: /CartMate · 18\+/i })).not.toBeVisible({ timeout: 10000 });
      return user;
    };

    const hUser = await enrollOne(hostPage, hTok, 'Dariusz Disconnect');
    await enrollOne(compPage, cTok, 'Dorota Disconnect');

    const newPingBtn = hostPage.locator('button[title*="Wyjście"], nav button').filter({ hasText: /Wyjście/i }).first();
    await newPingBtn.click();
    const createPingDialog = hostPage.locator('#create-ping-dialog');
    await expect(createPingDialog).toBeVisible({ timeout: 6000 });
    await createPingDialog.locator('button[type="button"]').filter({ hasText: /Makro|Biedronka/i }).first().click();
    await createPingDialog.locator('button[type="submit"]').click();
    await expect(createPingDialog).not.toBeVisible({ timeout: 8000 });

    const card = compPage.locator(`text=${hUser.name}`).first();
    await expect(card).toBeVisible({ timeout: 10000 });
    await compPage.locator('button').filter({ hasText: /Dołącz/i }).first().click();
    const joinModal = compPage.locator('div[role="dialog"][aria-labelledby="join-request-modal-title"]');
    await joinModal.getByRole('button', { name: /Wyślij zgłoszenie|Dołącz/i }).click();

    const reqBtn = hostPage.locator('button').filter({ hasText: /Zgłoszenia/i }).first();
    await expect(reqBtn).toBeVisible({ timeout: 10000 });
    await reqBtn.click();
    const revModal = hostPage.locator('div[role="dialog"][aria-labelledby="host-review-modal-title"]');
    await revModal.getByRole('button', { name: /Zaakceptuj/i }).click();

    await expect(hostPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });
    await expect(compPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });

    // Host sends message 1
    const hChat = hostPage.locator('input[placeholder*="czarnej kurtce"]');
    await hChat.fill('Wiadomość przed reloadem');
    await hostPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();
    await expect(compPage.locator('text=Wiadomość przed reloadem').first()).toBeVisible({ timeout: 10000 });

    // Reload companion page to simulate network reconnect / client rehydration
    await compPage.reload();
    await expect(compPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });
    // Verify pre-reload message rehydrated exactly once (no duplicates)
    await expect(compPage.locator('text=Wiadomość przed reloadem')).toHaveCount(1);

    // Host sends message 2 post-reload
    await hChat.fill('Wiadomość po reloadzie');
    await hostPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();
    await expect(compPage.locator('text=Wiadomość po reloadzie').first()).toBeVisible({ timeout: 10000 });
    await expect(compPage.locator('text=Wiadomość przed reloadem')).toHaveCount(1);

    // Cancel trip and reload: trip must not reappear as active
    await hostPage.getByRole('button', { name: /Zrezygnuj z wyjścia/i }).click();
    await hostPage.locator('#trip-cancel-dialog button').filter({ hasText: /Potwierdź rezygnację/i }).click();
    await expect(compPage.getByRole('status').filter({ hasText: /Wyjście zostało anulowane/i }).first()).toBeVisible({ timeout: 10000 });

    await compPage.reload();
    await expect(compPage.getByText(/Plan spotkania/i)).not.toBeVisible({ timeout: 5000 });

    await hostContext.close();
    await compContext.close();
  });

  test('actual offline send failure, backend process stop/restart, fresh-ticket reconnection, and state convergence (RT-09 restart)', async ({
    browser,
  }) => {
    test.setTimeout(90_000);
    const restartDbPath = path.join(os.tmpdir(), `cartmate-restart-${Date.now()}-${Math.random().toString(36).slice(2)}.db`);
    const port = 8018;
    const baseUrl = `http://127.0.0.1:${port}`;

    let proc = startHarness(restartDbPath, port);
    try {
      await waitForHarness(port);
      const opCredsRes = await fetch(`${baseUrl}/_op_qa/operator-credentials`);
      const { token: opToken } = await opCredsRes.json();
      const opHeaders = { Authorization: `Bearer ${opToken}` };

      const hTokRes = await fetch(`${baseUrl}/_op_qa/issue-token?intended_for=Restart+Host`, { method: 'POST' });
      const hTok = (await hTokRes.json()).token;
      const cTokRes = await fetch(`${baseUrl}/_op_qa/issue-token?intended_for=Restart+Companion`, { method: 'POST' });
      const cTok = (await cTokRes.json()).token;

      const hostContext = await browser.newContext();
      const hostPage = await hostContext.newPage();
      const compContext = await browser.newContext();
      const compPage = await compContext.newPage();

      const hostFrames = captureRealtimeFrames(hostPage);
      const compFrames = captureRealtimeFrames(compPage);

      const enrollOne = async (page: Page, tok: string, name: string) => {
        await page.goto(baseUrl);
        const modal = page.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
        await modal.getByRole('button', { name: /Aktywuj kod operatora pilotażu/i }).click();
        await modal.locator('#auth-act-token').fill(tok);
        await modal.locator('#auth-act-name').fill(name);
        await modal.locator('#auth-act-city').selectOption('Katowice');
        await modal.locator('#auth-act-gender').selectOption('male');
        await modal.getByRole('button', { name: /Aktywuj konto pilotażu/i }).click();
        await expect(modal).not.toBeVisible({ timeout: 10000 });
        const session = await page.evaluate(() => localStorage.getItem('cartmate_token'));
        const userRes = await fetch(`${baseUrl}/api/users/me`, { headers: { Authorization: `Bearer ${session}` } });
        const user = await userRes.json();
        await page.getByRole('button', { name: /Wygeneruj kod do sprawdzenia 18\+/i }).click();
        const ch = (await page.locator('p[role="status"] code').last().textContent())?.trim();
        await fetch(`${baseUrl}/api/moderation/users/${user.id}/adult-attestation`, {
          method: 'POST',
          headers: { ...opHeaders, 'Content-Type': 'application/json' },
          body: JSON.stringify({ method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: ch }),
        });
        await page.getByRole('button', { name: /Sprawdź ponownie/i }).click();
        await expect(page.getByRole('heading', { name: /CartMate · 18\+/i })).not.toBeVisible({ timeout: 10000 });
        return { user, session };
      };

      const { user: hUser } = await enrollOne(hostPage, hTok, 'Restart Host');
      await enrollOne(compPage, cTok, 'Restart Companion');

      // Verify connection.ready frames received on initial connection
      await expect.poll(() => hostFrames.some((f) => f.type === 'connection.ready'), { timeout: 10000 }).toBe(true);
      await expect.poll(() => compFrames.some((f) => f.type === 'connection.ready'), { timeout: 10000 }).toBe(true);

      // Host creates outing
      const newPingBtn = hostPage.locator('button[title*="Wyjście"], nav button').filter({ hasText: /Wyjście/i }).first();
      await newPingBtn.click();
      const createPingDialog = hostPage.locator('#create-ping-dialog');
      await expect(createPingDialog).toBeVisible({ timeout: 6000 });
      await createPingDialog.locator('button[type="button"]').filter({ hasText: /Makro|Biedronka/i }).first().click();
      await createPingDialog.locator('button[type="submit"]').click();
      await expect(createPingDialog).not.toBeVisible({ timeout: 8000 });

      // Companion joins
      const card = compPage.locator(`text=${hUser.name}`).first();
      await expect(card).toBeVisible({ timeout: 10000 });
      await compPage.locator('button').filter({ hasText: /Dołącz/i }).first().click();
      const joinModal = compPage.locator('div[role="dialog"][aria-labelledby="join-request-modal-title"]');
      await joinModal.getByRole('button', { name: /Wyślij zgłoszenie|Dołącz/i }).click();

      // Host accepts
      const reqBtn = hostPage.locator('button').filter({ hasText: /Zgłoszenia/i }).first();
      await expect(reqBtn).toBeVisible({ timeout: 10000 });
      await reqBtn.click();
      const revModal = hostPage.locator('div[role="dialog"][aria-labelledby="host-review-modal-title"]');
      await revModal.getByRole('button', { name: /Zaakceptuj/i }).click();

      await expect(hostPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });
      await expect(compPage.getByText(/Plan spotkania/i)).toBeVisible({ timeout: 10000 });

      // Host sends initial message
      const hChat = hostPage.locator('input[placeholder*="czarnej kurtce"]');
      await hChat.fill('Wiadomość przed awarią');
      await hostPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();
      await expect(compPage.locator('text=Wiadomość przed awarią').first()).toBeVisible({ timeout: 10000 });

      // --- Offline Test: Honest offline send failure and draft retention ---
      await hostContext.setOffline(true);
      await hChat.fill('Próba wysłania offline');
      await hostPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();
      await expect(hostPage.locator('p[role="alert"]').filter({ hasText: /Could not send message|Błąd|Failed to fetch|NetworkError/i })).toBeVisible({ timeout: 6000 });
      // Assert draft retention in input
      await expect(hChat).toHaveValue('Próba wysłania offline');

      // Companion sends message while host is offline
      const compChatOffline = compPage.locator('input[placeholder*="czarnej kurtce"]');
      await compChatOffline.fill('Wiadomość wysłana gdy host był offline');
      await compPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();
      await expect(compPage.locator('text=Wiadomość wysłana gdy host był offline').first()).toBeVisible({ timeout: 10000 });

      // Host reconnects: message sent during offline must rehydrate without page reload
      await hostContext.setOffline(false);
      await expect(hostPage.locator('text=Wiadomość wysłana gdy host był offline').first()).toBeVisible({ timeout: 15000 });

      // Track initial connection.ready count before restart
      const hostReadyCountBefore = hostFrames.filter((f) => f.type === 'connection.ready').length;
      const compReadyCountBefore = compFrames.filter((f) => f.type === 'connection.ready').length;

      // --- Actual Server Stop & Restart against SAME DB ---
      // Stop backend process while both pages remain open (no page reload)
      await stopHarness(proc);

      // Start new backend process pointing to the EXACT SAME disposable database
      proc = startHarness(restartDbPath, port);
      await waitForHarness(port);

      // Wait for both open browsers' RealtimeClient to reconnect with fresh ticket and resubscribe
      await expect.poll(
        () => hostFrames.filter((f) => f.type === 'connection.ready').length,
        { timeout: 25000 }
      ).toBeGreaterThan(hostReadyCountBefore);
      await expect.poll(
        () => compFrames.filter((f) => f.type === 'connection.ready').length,
        { timeout: 25000 }
      ).toBeGreaterThan(compReadyCountBefore);

      await new Promise((r) => setTimeout(r, 800));

      // Send a new message after process restart to prove full two-way convergence
      const compChat = compPage.locator('input[placeholder*="czarnej kurtce"]');
      await compChat.fill('Wiadomość po restarcie procesu');
      await compPage.locator('form:has(input[placeholder*="czarnej kurtce"]) button[type="submit"]').click();

      await expect(hostPage.locator('text=Wiadomość po restarcie procesu').first()).toBeVisible({ timeout: 15000 });
      // Assert no duplicate chat messages: exactly 1 instance of pre-restart message
      await expect(hostPage.locator('text=Wiadomość przed awarią')).toHaveCount(1);
      await expect(compPage.locator('text=Wiadomość przed awarią')).toHaveCount(1);

      // Cancel trip on restarted server
      await hostPage.getByRole('button', { name: /Zrezygnuj z wyjścia/i }).click();
      await hostPage.locator('#trip-cancel-dialog button').filter({ hasText: /Potwierdź rezygnację/i }).click();
      await expect(compPage.getByRole('status').filter({ hasText: /Wyjście zostało anulowane/i }).first()).toBeVisible({ timeout: 10000 });

      // Restart server a second time: verify cancelled trip remains cancelled and does not resurrect
      await stopHarness(proc);
      proc = startHarness(restartDbPath, port);
      await waitForHarness(port);

      // Open companion page checks that cancelled trip does not resurrect
      await compPage.waitForTimeout(1000);
      await expect(compPage.getByText(/Plan spotkania/i)).not.toBeVisible({ timeout: 5000 });

      await hostContext.close();
      await compContext.close();
    } finally {
      await stopHarness(proc);
      try { fs.unlinkSync(restartDbPath); } catch {}
      try { fs.unlinkSync(`${restartDbPath}-wal`); } catch {}
      try { fs.unlinkSync(`${restartDbPath}-shm`); } catch {}
    }
  });

  test('focused accessibility: modal Escape dismissal, focus restoration, named control traversal, wraparound, and 320px responsive layout (RT-12)', async ({
    browser,
    request,
  }) => {
    const context = await browser.newContext({ viewport: { width: 320, height: 600 } });
    const page = await context.newPage();
    await page.goto('/');

    // 1. Initial 320px responsive layout without horizontal overflow
    const hasHorizontalOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
    });
    expect(hasHorizontalOverflow).toBe(false);

    const authModal = page.locator('div[role="dialog"][aria-labelledby="auth-modal-title"]');
    await expect(authModal).toBeVisible({ timeout: 10000 });

    // 2. Escape key dismisses initial modal
    await page.keyboard.press('Escape');
    await expect(authModal).not.toBeVisible({ timeout: 5000 });

    // 3. Open auth modal via UI button
    const openAuthBtn = page.getByRole('button', { name: /Zaloguj/i }).first();
    await expect(openAuthBtn).toBeVisible();
    await openAuthBtn.click();
    await expect(authModal).toBeVisible({ timeout: 5000 });

    // 4. Switch to Aktywuj tab
    const actTabBtn = authModal.getByRole('button', { name: /Aktywuj kod operatora|Aktywuj/i });
    await actTabBtn.click();

    // Measure 320px responsive overflow while activate form is visible
    const actFormOverflow = await page.evaluate(() => {
      return document.documentElement.scrollWidth > document.documentElement.clientWidth + 1;
    });
    expect(actFormOverflow).toBe(false);

    // 5. Named control keyboard flow traversal
    const actTokenInput = authModal.locator('#auth-act-token');
    const actNameInput = authModal.locator('#auth-act-name');
    const actCitySelect = authModal.locator('#auth-act-city');
    const actGenderSelect = authModal.locator('#auth-act-gender');
    const actBioTextarea = authModal.locator('#auth-act-bio');
    const actSubmitBtn = authModal.locator('button[type="submit"]');

    // Fill required fields so submit button is enabled for keyboard focus traversal
    await actTokenInput.fill('CMACT-KB-FLOW');
    await actNameInput.fill('Klaudia Klawiatura');

    await actTokenInput.focus();
    expect(await actTokenInput.evaluate((el) => el === document.activeElement)).toBe(true);

    await page.keyboard.press('Tab');
    expect(await actNameInput.evaluate((el) => el === document.activeElement)).toBe(true);

    await page.keyboard.press('Tab');
    expect(await actCitySelect.evaluate((el) => el === document.activeElement)).toBe(true);

    await page.keyboard.press('Tab');
    expect(await actGenderSelect.evaluate((el) => el === document.activeElement)).toBe(true);

    await page.keyboard.press('Tab');
    expect(await actBioTextarea.evaluate((el) => el === document.activeElement)).toBe(true);

    await page.keyboard.press('Tab');
    // 6a. Forward Tab wraparound from last element (submit button wraps to first element: close button)
    await actSubmitBtn.focus();
    expect(await actSubmitBtn.evaluate((el) => el === document.activeElement)).toBe(true);
    await page.keyboard.press('Tab');
    const closeBtn = authModal.locator('button[aria-label="Zamknij okno autoryzacji"]');
    expect(await closeBtn.evaluate((el) => el === document.activeElement)).toBe(true);

    // 6b. Reverse Shift+Tab wraparound from first element (close button wraps to submit button)
    await page.keyboard.press('Shift+Tab');
    expect(await actSubmitBtn.evaluate((el) => el === document.activeElement)).toBe(true);

    // 6c. Recovery error & focus behavior (tested separately from activation traversal):
    // Invalid recovery token displays accessible role="alert"
    await actTokenInput.fill('CMREC-INVALID-TEST');
    await actSubmitBtn.click();
    const alertDiv = authModal.locator('div[role="alert"]');
    await expect(alertDiv).toBeVisible({ timeout: 5000 });
    await expect(alertDiv).toContainText(/Błąd|Nieprawidłowy|nie istnieje/i);

    // 7. Escape key dismisses modal and restores focus to trigger button
    await page.keyboard.press('Escape');
    await expect(authModal).not.toBeVisible({ timeout: 5000 });
    await expect(openAuthBtn).toBeFocused();
    await context.close();

    // 8. Empty-feed presentation & action with admitted account:
    // Create an admitted account via operator token + witnessed 18+ attestation
    const modCreds = await (await request.get('/_op_qa/operator-credentials')).json();
    const tokenEmpty = (await (await request.post('/_op_qa/issue-token', { data: {} })).json()).token;
    const emptyUser = await (await request.post('/api/auth/redeem-operator-activation', {
      data: { activation_token: tokenEmpty, name: 'Zofia Pusta', city: 'Katowice', gender: 'female' },
    })).json();
    const chEmpty = (await (await request.post('/api/users/me/age-check-challenge', { headers: { Authorization: `Bearer ${emptyUser.token}` } })).json()).challenge;
    await request.post(`/api/moderation/users/${emptyUser.user.id}/adult-attestation`, {
      headers: { Authorization: `Bearer ${modCreds.token}` },
      data: { method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: chEmpty },
    });

    const emptyContext = await browser.newContext({ viewport: { width: 320, height: 600 } });
    const emptyPage = await emptyContext.newPage();
    // Intercept pings route for this context to guarantee a deliberately empty feed
    await emptyPage.route('**/api/pings*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      });
    });
    await emptyPage.addInitScript(({ token, id }) => {
      localStorage.setItem('cartmate_token', token);
      localStorage.setItem('cartmate_user_id', id);
    }, { token: emptyUser.token, id: emptyUser.user.id });

    await emptyPage.goto('/');

    // Assert explanatory empty-feed copy
    await expect(emptyPage.getByText(/Brak aktywnych wyjść/i).first()).toBeVisible({ timeout: 10000 });

    // Assert create-outing action is visible and opens #create-ping-dialog
    const createOutingBtn = emptyPage.getByRole('button', { name: /Bądź pierwszą osobą, która doda wyjście!/i });
    await expect(createOutingBtn).toBeVisible({ timeout: 5000 });
    await createOutingBtn.click();

    // Verify create-outing dialog opens
    const createPingDialog = emptyPage.locator('#create-ping-dialog');
    await expect(createPingDialog).toBeVisible({ timeout: 5000 });

    await emptyContext.close();
  });

  test('deliberate lost response after commit and truthful recovery without double submission (MR-05)', async ({
    page,
    request,
  }) => {
    // 1. Issue operator activation tokens for host and companion
    const modCreds = await (await request.get('/_op_qa/operator-credentials')).json();
    const tokenA = (await (await request.post('/_op_qa/issue-token', { data: {} })).json()).token;
    const tokenB = (await (await request.post('/_op_qa/issue-token', { data: {} })).json()).token;

    const hostAcct = await (await request.post('/api/auth/redeem-operator-activation', {
      data: { activation_token: tokenA, name: 'Host Retry', city: 'Katowice', gender: 'male' },
    })).json();

    const joinerAcct = await (await request.post('/api/auth/redeem-operator-activation', {
      data: { activation_token: tokenB, name: 'Joiner Retry', city: 'Katowice', gender: 'female' },
    })).json();

    // Witnessed 18+ attestations
    const chA = (await (await request.post('/api/users/me/age-check-challenge', { headers: { Authorization: `Bearer ${hostAcct.token}` } })).json()).challenge;
    await request.post(`/api/moderation/users/${hostAcct.user.id}/adult-attestation`, {
      headers: { Authorization: `Bearer ${modCreds.token}` },
      data: { method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: chA },
    });
    const chB = (await (await request.post('/api/users/me/age-check-challenge', { headers: { Authorization: `Bearer ${joinerAcct.token}` } })).json()).challenge;
    await request.post(`/api/moderation/users/${joinerAcct.user.id}/adult-attestation`, {
      headers: { Authorization: `Bearer ${modCreds.token}` },
      data: { method: 'physical_identity_document', confirmed_over_18: true, subject_present: true, subject_consented: true, account_bound: true, account_challenge: chB },
    });

    // Host creates ping
    const pingRes = await request.post('/api/pings', {
      headers: { Authorization: `Bearer ${hostAcct.token}` },
      data: {
        category: 'grocery',
        destination_name: 'Biedronka Retry Katowice',
        destination_lat: 50.2649,
        destination_lng: 19.0238,
        address: 'ul. 3 Maja',
        intent_tags: ['zakupy'],
        ttl_minutes: 60,
      },
    });
    const ping = await pingRes.json();

    // Setup browser session as joiner
    await page.addInitScript(({ token, id }) => {
      localStorage.setItem('cartmate_token', token);
      localStorage.setItem('cartmate_user_id', id);
    }, { token: joinerAcct.token, id: joinerAcct.user.id });

    // Handle dialog alerts on page (e.g. from network error)
    page.on('dialog', (dialog) => dialog.accept());

    // Simulate lost response after commit on join request:
    // Route handler intercepts POST /api/pings/:id/join, fetches response from backend (committing the join),
    // then simulates network drop by aborting the response to the client.
    let joinRouteHits = 0;
    await page.route(`**/api/pings/${ping.id}/join`, async (route) => {
      joinRouteHits++;
      if (joinRouteHits === 1) {
        const response = await route.fetch();
        expect(response.status()).toBe(200);
        await route.abort('failed');
      } else {
        await route.continue();
      }
    });

    await page.goto('/');
    const pingCard = page.locator(`#ping-${ping.id}`);
    await expect(pingCard).toBeVisible({ timeout: 10000 });
    const joinBtn = pingCard.locator('button').filter({ hasText: /Dołącz/i }).first();
    await joinBtn.scrollIntoViewIfNeeded();
    await joinBtn.click();
    const joinModal = page.locator('div[role="dialog"][aria-labelledby="join-request-modal-title"]');
    await expect(joinModal).toBeVisible({ timeout: 5000 });
    await joinModal.getByRole('button', { name: /Wyślij zgłoszenie|Dołącz/i }).click();

    // Verify on server that exactly ONE join request was committed from the initial request
    let originalReqId = '';
    await expect.poll(async () => {
      const res = await request.get(`/api/pings/${ping.id}/requests`, {
        headers: { Authorization: `Bearer ${hostAcct.token}` },
      });
      if (!res.ok()) return 0;
      const data = await res.json();
      if (data.length === 1) {
        originalReqId = data[0].id;
      }
      return data.length;
    }, { timeout: 10000 }).toBe(1);
    expect(originalReqId).toBeTruthy();

    // 2. Client recovers and performs a real retry from the participant UI
    await page.reload();
    await expect(pingCard).toBeVisible({ timeout: 10000 });
    const retryJoinBtn = pingCard.locator('button').filter({ hasText: /Dołącz/i }).first();
    await retryJoinBtn.scrollIntoViewIfNeeded();
    await retryJoinBtn.click();
    const retryModal = page.locator('div[role="dialog"][aria-labelledby="join-request-modal-title"]');
    await expect(retryModal).toBeVisible({ timeout: 5000 });
    await retryModal.getByRole('button', { name: /Wyślij zgłoszenie|Dołącz/i }).click();

    // Verify server retains exactly 1 record with identical request ID (idempotency confirmed)
    await expect.poll(async () => {
      const res = await request.get(`/api/pings/${ping.id}/requests`, {
        headers: { Authorization: `Bearer ${hostAcct.token}` },
      });
      if (!res.ok()) return 0;
      const data = await res.json();
      return data.length;
    }, { timeout: 10000 }).toBe(1);

    const requestsResAfter = await request.get(`/api/pings/${ping.id}/requests`, {
      headers: { Authorization: `Bearer ${hostAcct.token}` },
    });
    const requestsAfter = await requestsResAfter.json();
    expect(requestsAfter.length).toBe(1);
    expect(requestsAfter[0].id).toBe(originalReqId);

    // Participant UI proves honest pending state (confirmation toast / banner)
    await expect(
      page.getByText(/Wysłano prośbę o dołączenie|Czekaj na potwierdzenie/i).first()
    ).toBeVisible({ timeout: 10000 });
  });
});

