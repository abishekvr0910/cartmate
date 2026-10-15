// Review-only unsupported-runtime check. Real API source, synthetic token,
// no fetch, DNS, socket or database access. No URL in the VM is deliberate.
// Exit 0: all checks pass; 1: residual fallback finding; 2: incomplete probe.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const ts = require('../frontend/node_modules/typescript');

try {
  const source = ts.transpileModule(
    fs.readFileSync(path.join(__dirname, '../frontend/src/api.ts'), 'utf8').replaceAll('import.meta', 'importMeta'),
    { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } },
  ).outputText;
  const origin = 'https://pilot.example';
  function loadApi(withParser) {
    const sandbox = {
      exports: {}, importMeta: { env: {} }, console, URL: withParser ? URL : undefined,
      window: { location: new URL(origin), Capacitor: { isNativePlatform: () => false } },
      localStorage: { getItem: key => key === 'cartmate_token' ? 'synthetic-fallback-review' : null },
    };
    vm.runInNewContext(source, sandbox);
    return sandbox.exports;
  }
  const checks = [];
  for (const withParser of [true, false]) {
    const api = loadApi(withParser);
    if (withParser) {
      checks.push({ name: 'same_origin_positive', pass: Boolean(api.getAuthHeaders('/api/users/me').Authorization) });
    }
    for (const [label, code] of [['tab', 9], ['linefeed', 10], ['carriage_return', 13]]) {
      const candidate = '/' + String.fromCharCode(code) + '/another-review.example/api';
      if (new URL(candidate, origin).origin === origin) throw new Error('Invalid off-origin fixture');
      checks.push({
        name: `${withParser ? 'parser_available' : 'parser_absent'}_${label}_authority_denied`,
        pass: !api.isApprovedBackendOrigin(candidate) && !api.getAuthHeaders(candidate).Authorization,
      });
    }
  }
  console.log(JSON.stringify({ checks, failures: checks.filter(check => !check.pass) }, null, 2));
  process.exitCode = checks.every(check => check.pass) ? 0 : 1;
} catch (error) {
  console.error(`Probe incomplete: ${error.message}`);
  process.exitCode = 2;
}
