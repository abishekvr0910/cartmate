import { test, expect } from '@playwright/test';

test.describe('Moderation & Safety Triage Journey', () => {
  test('authorized moderator sees safety queue and requires resolution notes', async ({ page }, testInfo) => {
    expect(process.env.CARTMATE_E2E_ISOLATED, 'This test creates a report; run only against an isolated E2E database').toBe('1');

    const details = `Isolated E2E moderation review ${testInfo.project.name} ${Date.now()}`;
    const createReportRes = await page.request.post('/api/reports', {
      headers: { Authorization: 'Bearer token_mateusz' },
      data: { reported_user_id: 'usr_ola', category: 'other', details },
    });
    expect(createReportRes.status()).toBe(200);
    const createdReport: { id: string } = await createReportRes.json();

    // Authenticate as Zuzanna (configured as moderator in E2E environment)
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_zuzanna');
      localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
    });
    await page.reload();

    // Navigate to Profile tab
    const profileTab = page.getByRole('navigation').getByRole('button', { name: /Profil|Profile/i });
    await expect(profileTab).toBeVisible({ timeout: 5000 });
    await profileTab.click();

    // Check if user has moderator capability from server
    const canModerateRes = await page.request.get('/api/moderation/access', {
      headers: { Authorization: 'Bearer token_zuzanna' },
    });
    expect(canModerateRes.status()).toBe(200);
    const canModerateData = await canModerateRes.json();
    expect(canModerateData.can_moderate).toBe(true);

    const modConsoleBtn = page.getByRole('button', { name: /Kolejka bezpieczeństwa|Safety review queue/i });
    await expect(modConsoleBtn).toBeVisible({ timeout: 5000 });
    await modConsoleBtn.click();

    await expect(page.getByRole('heading', { name: /Kolejka bezpieczeństwa|Safety review queue/i })).toBeVisible();

    // Select the created report in the FIFO queue list if not already first
    const reportBtn = page.locator('ol button').filter({ hasText: 'usr_ola' }).last();
    await expect(reportBtn).toBeVisible({ timeout: 5000 });
    await reportBtn.click();

    await expect(page.getByText(details)).toBeVisible();

    const noteInput = page.locator('#moderation-note');
    await expect(noteInput).toBeVisible();
    const decisionButton = page.getByRole('button', { name: /Odrzuć zgłoszenie|Dismiss report/i });
    await expect(decisionButton).toBeDisabled();
    await noteInput.fill('Reviewed isolated E2E report; no action needed.');
    await expect(decisionButton).toBeEnabled();
    const [actionResponse] = await Promise.all([
      page.waitForResponse((response) => response.url().includes(`/api/moderation/reports/${createdReport.id}/action`)),
      decisionButton.click(),
    ]);
    expect(actionResponse.status()).toBe(200);
    await expect(page.getByText(/Decyzja została zapisana|Decision recorded/i)).toBeVisible();
  });

  test('ordinary user is denied access to moderator queue on frontend and backend', async ({ page }) => {
    // Authenticate as Mateusz (not on moderator allowlist)
    await page.goto('/');
    await page.evaluate(() => {
      localStorage.setItem('cartmate_token', 'token_mateusz');
      localStorage.setItem('cartmate_user_id', 'usr_mateusz');
    });
    await page.reload();

    // 1. Backend authorization check: 403 Forbidden
    const forbiddenRes = await page.request.get('/api/moderation/queue', {
      headers: { Authorization: 'Bearer token_mateusz' },
    });
    expect(forbiddenRes.status()).toBe(403);

    // 2. Frontend check: Moderator button must NOT be rendered
    const profileTab = page.getByRole('navigation').getByRole('button', { name: /Profil|Profile/i });
    await expect(profileTab).toBeVisible({ timeout: 5000 });
    await profileTab.click();

    const modConsoleBtn = page.getByRole('button', { name: /Kolejka bezpieczeństwa|Safety review queue/i });
    await expect(modConsoleBtn).not.toBeVisible();
  });
});
