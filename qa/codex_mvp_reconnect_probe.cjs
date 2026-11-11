// Independent missed-event review. Synthetic accounts, owned loopback server and DB only.
// Run from repository root: node qa/codex_mvp_reconnect_probe.cjs
const { chromium } = require('@playwright/test');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const net = require('node:net');
const assert = require('node:assert/strict');
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

async function until(check, message, timeout = 20000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (await check()) return;
    await delay(150);
  }
  throw new Error(message);
}

async function stop(proc) {
  if (!proc || proc.exitCode !== null || proc.signalCode !== null) return;
  const exited = once(proc, 'exit');
  if (process.platform === 'win32') {
    const killer = spawn('taskkill', ['/pid', String(proc.pid), '/f', '/t'], { windowsHide: true, stdio: 'ignore' });
    await once(killer, 'exit');
  } else proc.kill('SIGTERM');
  let timer;
  try {
    await Promise.race([exited, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('Owned server did not exit')), 10000); })]);
  } finally { clearTimeout(timer); }
}

(async () => {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), 'cartmate-codex-missed-'));
  const db = path.join(scratch, 'probe.db');
  const listener = net.createServer();
  listener.listen(0, '127.0.0.1');
  await once(listener, 'listening');
  const port = listener.address().port;
  await new Promise(resolve => listener.close(resolve));
  const base = `http://127.0.0.1:${port}`;
  const venvWin = path.join(__dirname, '..', 'backend', '.venv', 'Scripts', 'python.exe');
  const venvPosix = path.join(__dirname, '..', 'backend', '.venv', 'bin', 'python');
  const pythonBin = process.env.PYTHON || (process.platform === 'win32' && fs.existsSync(venvWin) ? venvWin : (fs.existsSync(venvPosix) ? venvPosix : 'python'));
  const start = () => spawn(pythonBin, [path.join(__dirname, 'operator_pilot_harness.py')], {
    cwd: __dirname, windowsHide: true, stdio: 'ignore',
    env: { ...process.env, CARTMATE_DATABASE_PATH: db, CARTMATE_OPERATOR_PILOT_PORT: String(port), JEV_MODE: 'disabled' },
  });
  const waitHealthy = () => until(async () => {
    try { return (await fetch(`${base}/api/health`, { signal: AbortSignal.timeout(1000) })).ok; }
    catch { return false; }
  }, 'Owned harness failed to start');
  async function api(route, token, body, method = body === undefined ? 'GET' : 'POST') {
    const res = await fetch(base + route, {
      method, signal: AbortSignal.timeout(5000),
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    assert.equal(res.status, 200, `${method} ${route} failed (${res.status})`);
    return res.json();
  }
  let proc;
  let browser;
  try {
    proc = start();
    await waitHealthy();
    const operator = await api('/_op_qa/operator-credentials');
    async function member(name) {
      const activation = await api('/_op_qa/issue-token', null, {});
      const account = await api('/api/auth/redeem-operator-activation', null, {
        activation_token: activation.token, name, city: 'Katowice', gender: 'male',
      });
      const challenge = await api('/api/users/me/age-check-challenge', account.token, {});
      await api(`/api/moderation/users/${account.user.id}/adult-attestation`, operator.token, {
        method: 'physical_identity_document', confirmed_over_18: true, subject_present: true,
        subject_consented: true, account_bound: true, account_challenge: challenge.challenge,
      });
      return account;
    }
    const host = await member('Probe Host');
    const companion = await member('Probe Companion');
    const ping = await api('/api/pings', host.token, {
      category: 'grocery', destination_name: 'Probe Katowice', destination_lat: 50.2649,
      destination_lng: 19.0238, address: 'Synthetic public point', intent_tags: ['zakupy'], ttl_minutes: 45,
    });
    const join = await api(`/api/pings/${ping.id}/join`, companion.token, { message: 'Synthetic probe' });
    const trip = await api(`/api/pings/${ping.id}/requests/${join.id}/accept`, host.token, {});
    const chatRoute = `/api/chat/rooms/${trip.chat_room_id}/messages`;
    browser = await chromium.launch();
    const context = await browser.newContext();
    await context.addInitScript(({ token, id }) => {
      localStorage.setItem('cartmate_token', token);
      localStorage.setItem('cartmate_user_id', id);
    }, { token: host.token, id: host.user.id });
    const page = await context.newPage();
    let readyCount = 0;
    page.on('websocket', ws => ws.on('framereceived', event => {
      try { if (JSON.parse(event.payload.toString()).type === 'connection.ready') readyCount++; } catch {}
    }));
    await page.goto(base);
    const input = page.locator('input[placeholder*="czarnej kurtce"]');
    await input.waitFor({ state: 'visible' });
    await until(() => readyCount > 0, 'Initial socket not ready');
    await api(chatRoute, companion.token, { text: 'probe-initial-positive-control' });
    await until(async () => await page.getByText('probe-initial-positive-control', { exact: true }).count() === 1, 'Initial chat not received');

    await context.setOffline(true);
    // Closing the owned server guarantees no lingering socket receives the missed event.
    await stop(proc);
    proc = start();
    await waitHealthy();
    await api(chatRoute, companion.token, { text: 'probe-message-during-host-offline' });
    const oldReadyCount = readyCount;
    await context.setOffline(false);
    await until(() => readyCount > oldReadyCount, 'Fresh socket not ready after reconnect', 25000);
    // Positive control: a later event on the recovered subscription is visible.
    await delay(250);
    await api(chatRoute, companion.token, { text: 'probe-message-after-reconnect' });
    await until(async () => await page.getByText('probe-message-after-reconnect', { exact: true }).count() === 1, 'Recovered chat subscription not working');
    await delay(5000);
    const room = await api(`/api/chat/rooms/${trip.chat_room_id}`, host.token);
    const result = {
      freshConnectionObserved: readyCount > oldReadyCount,
      missedMessagePersisted: room.messages.some(m => m.text === 'probe-message-during-host-offline'),
      missedMessageVisibleWithoutReload: await page.getByText('probe-message-during-host-offline', { exact: true }).count(),
      postReconnectMessageVisible: await page.getByText('probe-message-after-reconnect', { exact: true }).count(),
    };
    // Reload is a diagnostic positive control, not a proposed fix.
    await page.reload();
    await until(async () => await page.getByText('probe-message-during-host-offline', { exact: true }).count() === 1, 'Persisted message not visible even on reload');
    result.missedMessageVisibleAfterReload = true;
    console.log(JSON.stringify(result, null, 2));
    process.exitCode = result.missedMessageVisibleWithoutReload === 1 ? 0 : 1;
  } finally {
    if (browser) await browser.close();
    await stop(proc);
    // Remove only the three exact synthetic DB paths in this probe's own directory.
    for (const suffix of ['', '-wal', '-shm']) if (fs.existsSync(db + suffix)) fs.unlinkSync(db + suffix);
    fs.rmdirSync(scratch);
  }
})().catch(error => { console.error(`Probe incomplete: ${error.message}`); process.exitCode = 2; });
