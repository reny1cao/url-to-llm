import { defineConfig } from '@playwright/test';

export default defineConfig({
  use: {
    browserName: 'chromium',
    headless: true,
    viewport: { width: 1366, height: 768 },
    launchOptions: {
      args: [
        '--disable-blink-features=AutomationControlled',
        '--disable-dev-shm-usage',
        '--no-sandbox',
        '--disable-setuid-sandbox',
      ],
      ...(process.env.PROXY && {
        proxy: {
          server: process.env.PROXY,
        },
      }),
    },
  },
  workers: 4,
  retries: 1,
  timeout: 30000,
  expect: {
    timeout: 5000,
  },
});