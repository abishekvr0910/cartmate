// Independent destination-policy retest. VM-executed source, intercepted fetch only.
// No real token, DNS lookup, HTTP request or WebSocket is used.
// Run from root: node qa/codex_mr02_destination_probe.cjs
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('../frontend/node_modules/typescript');
const compile = relative => ts.transpileModule(
  fs.readFileSync(path.join(__dirname, relative), 'utf8').replaceAll('import.meta', 'importMeta'),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
).outputText;
const apiSource = compile('../frontend/src/api.ts');
const socketSource = compile('../frontend/src/realtime/socket.ts');

async function inspect({ native = true, stored = null, env = {} } = {}) {
  const values = new Map([['cartmate_token', 'synthetic-destination-review-token']]);
  if (stored) values.set('cartmate_backend_url', stored);
  const calls = [];
  const sandbox = {
    exports: {}, importMeta: { env }, console, URL,
    window: {
      location: { protocol: 'https:', host: native ? 'localhost' : 'pilot.example', href: native ? 'https://localhost/' : 'https://pilot.example/' },
      Capacitor: { isNativePlatform: () => native, getPlatform: () => native ? 'android' : 'web' },
    },
    localStorage: { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) },
    fetch: async (url, init) => {
      calls.push({ url, bearerAttached: init?.headers?.Authorization === 'Bearer synthetic-destination-review-token' });
      return { ok: true, status: 200, json: async () => ({ id: 'synthetic-member', ticket: 'synthetic-ticket' }) };
    },
  };
  vm.runInNewContext(apiSource, sandbox);
  const api = sandbox.exports;
  await api.fetchCurrentUser();
  await api.fetchPodTemplates();
  await api.fetchThirdPlaces('Katowice');
  await api.fetchPodFeed('Katowice', 'synthetic-destination-review-token');
  await api.joinPod(1, 'synthetic-destination-review-token');
  await api.leavePod(1, 'synthetic-destination-review-token');
  await api.fetchPodMessages(1, 'synthetic-destination-review-token');
  await api.sendPodMessage(1, 'Hello', 'synthetic-destination-review-token');
  await api.fetchVoiceStatus('synthetic-destination-review-token');
  await api.rateVoiceCall('call_1', { rating: 'respectful' }, 'synthetic-destination-review-token');
  await api.hangupVoiceCall('call_1', 'synthetic-destination-review-token', false);
  sandbox.exports = {};
  sandbox.require = name => { if (name === '../api') return api; throw new Error(`Unexpected import: ${name}`); };
  vm.runInNewContext(socketSource, sandbox);
  let resolvedSocket = null;
  let socketError = null;
  try { resolvedSocket = await new sandbox.exports.RealtimeClient().resolveUrl('synthetic-destination-review-token'); }
  catch (error) { socketError = error.message; }
  return { backend: api.getBackendBaseUrl(), calls, resolvedSocket, socketError };
}

(async () => {
  const result = {
    literalPreviousTestHostname: await inspect({ stored: 'https://unapproved.example' }),
    differentUnapprovedHostname: await inspect({ stored: 'https://outside.example' }),
    secondUnapprovedHostname: await inspect({ stored: 'https://ordinary-review.example' }),
    missingNativeConfig: await inspect(),
    webSocketOverride: await inspect({ native: false, env: { VITE_WS_URL: 'wss://outside.example/ws' } }),
  };
  console.log(JSON.stringify(result, null, 2));
  const unsafe = result.differentUnapprovedHostname.calls.some(call => call.bearerAttached)
    || result.secondUnapprovedHostname.calls.some(call => call.bearerAttached)
    || result.missingNativeConfig.calls.some(call => call.bearerAttached)
    || result.webSocketOverride.resolvedSocket?.startsWith('wss://outside.example/');
  process.exitCode = unsafe ? 1 : 0;
})().catch(error => { console.error(`Probe incomplete: ${error.message}`); process.exitCode = 2; });
