import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.CARTMATE_BASE_URL || 'http://localhost:5280';
const hostname = new URL(baseURL).hostname;
if (!['localhost', '127.0.0.1'].includes(hostname) || process.env.CARTMATE_E2E_ISOLATED !== '1') {
  throw new Error('This demo-token suite is local-only and requires CARTMATE_E2E_ISOLATED=1 with a dedicated disposable database.');
}

export default defineConfig({
  testDir: './tests',
  testIgnore: [/no-demo-publishing\.spec\.ts/, /operator-pilot\.spec\.ts/],
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 7'] },
    },
  ],
});
