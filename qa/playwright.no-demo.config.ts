import { defineConfig, devices } from '@playwright/test';

const baseURL = 'http://127.0.0.1:8008';

export default defineConfig({
  testDir: './tests',
  testMatch: /no-demo-publishing\.spec\.ts/,
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
  webServer: {
    command: 'python staging_harness.py',
    port: 8008,
    reuseExistingServer: false,
    timeout: 15000,
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
