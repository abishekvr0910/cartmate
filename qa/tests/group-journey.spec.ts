import { test, expect } from '@playwright/test';

test('votes do not auto-join; explicit group join, chat and report work', async ({ page }) => {
  expect(process.env.CARTMATE_E2E_ISOLATED, 'Group browser test writes to a disposable local database').toBe('1');
  const name = `Group consent browser ${Date.now()}`;
  const zuzanna = { Authorization: 'Bearer token_zuzanna' };
  const jakub = { Authorization: 'Bearer token_jakub' };
  const ola = { Authorization: 'Bearer token_ola' };
  const created = await page.request.post('/api/hotspots', {
    headers: zuzanna,
    data: {
      city: 'Katowice', name, category: 'cafe', emoji: '☕',
      address: 'Rynek 1, Katowice', target_time: 'Tomorrow 16:00',
      description: 'A short public cafe outing', cost_policy: 'Each person pays their own order',
    },
  });
  expect(created.status()).toBe(200);
  const spotId = (await created.json()).id;
  expect((await page.request.put(`/api/hotspots/${spotId}/vote`, { headers: jakub })).status()).toBe(200);
  const threshold = await page.request.put(`/api/hotspots/${spotId}/vote`, { headers: ola });
  expect(threshold.status()).toBe(200);
  const outingId = (await threshold.json()).outing_id;
  const roomId = `room_${outingId}`;
  expect((await page.request.get(`/api/outings/${outingId}`, { headers: zuzanna })).status()).toBe(403);
  expect((await page.request.get(`/api/chat/rooms/${roomId}`, { headers: zuzanna })).status()).toBe(403);

  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('cartmate_token', 'token_zuzanna');
    localStorage.setItem('cartmate_user_id', 'usr_zuzanna');
  });
  await page.reload();
  await page.getByRole('navigation').getByRole('button', { name: /W pobliżu|Nearby/i }).click();
  const card = page.locator('div[class*="p-3.5"]').filter({ has: page.getByText(name, { exact: true }) }).first();
  await expect(card).toBeVisible();
  await card.getByRole('button', { name: /Dołącz do ekipy|Join the crew/i }).click();
  const joinDialog = page.getByRole('dialog', { name });
  await expect(joinDialog.getByText(/udział wymaga potwierdzenia|joining requires confirmation/i)).toBeVisible();
  await joinDialog.getByRole('button', { name: /Potwierdź udział|Confirm joining/i }).click();
  const chat = page.getByRole('dialog', { name: new RegExp(name) });
  await expect(chat).toBeVisible();
  expect((await page.request.get(`/api/chat/rooms/${roomId}`, { headers: zuzanna })).status()).toBe(200);

  expect((await page.request.post(`/api/outings/${outingId}/join`, { headers: jakub })).status()).toBe(200);
  const message = await page.request.post(`/api/chat/rooms/${roomId}/messages`, {
    headers: jakub, data: { text: 'Please review this test message' },
  });
  expect(message.status()).toBe(200);
  await expect(chat.getByText('Please review this test message')).toBeVisible({ timeout: 5000 });
  await chat.getByRole('button', { name: /Opuść ekipę|Leave group/i }).click();
  await expect(chat).toBeVisible();
  await expect(chat.getByRole('status').getByText(/Opuściłeś ekipę|You left the group/i)).toBeVisible();
  await expect(chat.getByRole('textbox', { name: /Wiadomość do ekipy|Message to group/i })).toHaveCount(0);
  expect((await page.request.get(`/api/chat/rooms/${roomId}`, { headers: zuzanna })).status()).toBe(403);
  await chat.getByRole('button', { name: /Zgłoś wiadomość użytkownika Jakub|Report message from Jakub/i }).click();
  await chat.getByRole('textbox', { name: /Co się wydarzyło|What happened/i }).fill('Please review the cited message from the group chat.');
  const reportResponse = page.waitForResponse((response) => response.url().endsWith('/api/reports') && response.request().method() === 'POST');
  await chat.getByRole('button', { name: /Wyślij zgłoszenie|Submit report/i }).click();
  expect((await reportResponse).status()).toBe(200);
  await expect(chat.getByRole('status').getByText(/Zgłoszenie zapisano|Report saved/i)).toBeVisible();
  await chat.getByRole('button', { name: /Zamknij czat|Close chat/i }).click();
  await expect(chat).not.toBeVisible();
});
