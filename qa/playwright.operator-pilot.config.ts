import { defineConfig, devices } from '@playwright/test';

const baseURL = 'http://127.0.0.1:8010';

export default defineConfig({
  testDir: './tests',
  testMatch: /operator-pilot\.spec\.ts/,
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
    command: 'python operator_pilot_harness.py',
    port: 8010,
    reuseExistingServer: false,
    timeout: 25000,
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
