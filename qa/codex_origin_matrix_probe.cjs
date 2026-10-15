// Independent follow-up to MR-02: real TS modules, fake fetch, synthetic tokens.
// No HTTP, DNS, actual WebSocket or database access. Run from repository root.
// Exit 1 identifies a failed policy assertion; exit 2 is a probe setup failure.
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
const origin = 'https://review-pilot.example';

function context({ native = true, env = {}, bound, stored } = {}) {
  const values = new Map([['cartmate_token', 'synthetic-origin-matrix-token']]);
  if (bound) values.set('cartmate_token_bound_backend', bound);
  if (stored) values.set('cartmate_backend_url', stored);
  const calls = [];
  const sandbox = {
    exports: {}, importMeta: { env }, console, URL,
    window: { location: new URL(native ? 'https://localhost/' : `${origin}/`), Capacitor: { isNativePlatform: () => native } },
    localStorage: { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v), removeItem: k => values.delete(k) },
    fetch: async (url, init) => {
      calls.push({ url: String(url), bearer: Boolean(init?.headers?.Authorization) });
      return { ok: true, status: 200, json: async () => ({ id: 'synthetic-member', ticket: 'synthetic-origin-ticket' }) };
    },
  };
  vm.runInNewContext(apiSource, sandbox);
  const api = sandbox.exports;
  sandbox.exports = {};
  sandbox.require = name => { if (name === '../api') return api; throw new Error(`Unexpected import ${name}`); };
  vm.runInNewContext(socketSource, sandbox);
  return { api, calls, values, socket: new sandbox.exports.RealtimeClient() };
}

(async () => {
  const checks = [];
  const check = (name, pass) => checks.push({ name, pass: Boolean(pass) });
  const native = context({ env: { VITE_BACKEND_ORIGIN: origin }, stored: 'https://ignored-storage.example' });
  await native.api.fetchCurrentUser();
  const ws = await native.socket.resolveUrl();
  check('native_positive_and_storage_override_ignored', native.calls.length === 2 && native.calls.every(c => c.bearer && new URL(c.url).origin === origin) && ws.startsWith('wss://review-pilot.example/ws?ticket='));
  check('native_full_path_allowed', native.api.isApprovedBackendOrigin(`${origin}/api/users/me`));
  for (const target of ['https://different-review.example/api', `${origin}:8443/api`, 'http://review-pilot.example/api', 'https://review-pilot.example.suffix.example/api', 'https://user:password@review-pilot.example/api']) {
    check(`native_reject_${target}`, !native.api.getAuthHeaders(target).Authorization);
  }
  const rebound = context({ env: { VITE_BACKEND_ORIGIN: origin }, bound: 'https://previous-backend.example' });
  check('previous_backend_session_cleared', !rebound.api.getAuthHeaders().Authorization && !rebound.values.has('cartmate_token'));
  for (const configured of [undefined, 'http://review-pilot.example', `${origin}?q=1`, `${origin}#fragment`, `${origin}/not-api`, 'https://user:password@review-pilot.example']) {
    const c = context({ env: configured ? { VITE_BACKEND_ORIGIN: configured } : {} });
    check(`invalid_configuration_withholds_bearer_${configured}`, !c.api.getAuthHeaders().Authorization);
    let rejected = false;
    try { await c.socket.resolveUrl(); } catch { rejected = true; }
    check(`invalid_configuration_no_ticket_fetch_${configured}`, rejected && c.calls.length === 0);
  }
  const web = context({ native: false, stored: 'https://ignored-web.example' });
  check('web_relative_positive', Boolean(web.api.getAuthHeaders('/api/users/me').Authorization));
  check('web_absolute_same_origin_positive', Boolean(web.api.getAuthHeaders(`${origin}/api/users/me`).Authorization));
  check('web_absolute_other_origin_rejected', !web.api.getAuthHeaders('https://different-review.example/api').Authorization);
  const slashBackslash = '/\\different-review.example/api';
  const resolved = new URL(slashBackslash, origin);
  check('web_backslash_authority_rejected', resolved.origin !== origin && !web.api.getAuthHeaders(slashBackslash).Authorization);
  const conflict = context({ native: false, env: { VITE_WS_URL: 'wss://different-review.example/ws' } });
  let rejected = false;
  try { await conflict.socket.resolveUrl(); } catch { rejected = true; }
  check('web_ws_conflict_rejected_before_ticket', rejected && conflict.calls.length === 0);
  console.log(JSON.stringify({ checks, failures: checks.filter(c => !c.pass) }, null, 2));
  process.exitCode = checks.every(c => c.pass) ? 0 : 1;
})().catch(error => { console.error(`Probe incomplete: ${error.message}`); process.exitCode = 2; });
