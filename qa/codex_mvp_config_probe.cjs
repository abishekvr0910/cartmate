// Independent review probe: real client functions, fake fetch, synthetic token only.
// No requests leave this process. Run: node qa/codex_mvp_config_probe.cjs
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('../frontend/node_modules/typescript');
const source = fs.readFileSync(path.join(__dirname, '../frontend/src/api.ts'), 'utf8');
const compiled = ts.transpileModule(source.replaceAll('import.meta', 'importMeta'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText;

async function inspect(storedBase, native = false, mutate = false) {
  const values = new Map([['cartmate_token', 'synthetic-review-token']]);
  if (storedBase) values.set('cartmate_backend_url', storedBase);
  const calls = [];
  const sandbox = {
    exports: {}, importMeta: { env: {} }, console,
    window: { location: { protocol: 'https:', host: native ? 'localhost' : 'pilot.example' },
      Capacitor: { isNativePlatform: () => native, getPlatform: () => native ? 'android' : 'web' } },
    localStorage: { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v), removeItem: k => values.delete(k) },
    fetch: async (url, init) => {
      calls.push({ url, attachedSyntheticBearer: init?.headers?.Authorization === 'Bearer synthetic-review-token' });
      return { ok: true, status: 200, json: async () => ({ id: 'synthetic-user' }) };
    },
  };
  vm.runInNewContext(compiled, sandbox);
  if (mutate) values.set('cartmate_backend_url', 'https://other.example');
  await sandbox.exports.fetchCurrentUser();
  return { calls, currentTicketApiBase: sandbox.exports.getApiBaseUrl() };
}

(async () => {
  const result = {
    browserAcceptsInsecureOverride: await inspect('http://unapproved.example'),
    nativeAcceptsUnapprovedOverride: await inspect('https://unapproved.example', true),
    nativeMissingConfiguration: await inspect(null, true),
    changedOverrideSplitsRestAndTicket: await inspect('https://initial.example', true, true),
  };
  console.log(JSON.stringify(result, null, 2));
  const unsafe = result.browserAcceptsInsecureOverride.calls[0]?.url.startsWith('http:')
    || result.nativeAcceptsUnapprovedOverride.calls[0]?.attachedSyntheticBearer
    || result.nativeMissingConfiguration.calls[0]?.url === '/api/users/me'
    || !result.changedOverrideSplitsRestAndTicket.calls[0]?.url.startsWith(result.changedOverrideSplitsRestAndTicket.currentTicketApiBase);
  process.exitCode = unsafe ? 1 : 0;
})().catch(error => { console.error(error.message); process.exitCode = 2; });
