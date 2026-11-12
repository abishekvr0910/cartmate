import fs from 'node:fs';
import path from 'node:path';
import { defineConfig, devices } from '@playwright/test';

const baseURL = 'http://127.0.0.1:8010';

const venvWin = path.resolve(__dirname, '../backend/.venv/Scripts/python.exe');
const venvPosix = path.resolve(__dirname, '../backend/.venv/bin/python');
const pythonBin = process.env.PYTHON || (process.platform === 'win32' && fs.existsSync(venvWin) ? `"${venvWin}"` : (fs.existsSync(venvPosix) ? `"${venvPosix}"` : 'python'));

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
    command: `${pythonBin} operator_pilot_harness.py`,
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
