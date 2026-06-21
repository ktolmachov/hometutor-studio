import { defineConfig, devices } from '@playwright/test';

/**
 * PR smoke: offline/fixture state, no live LLM (see US-12.6).
 * Full 5-minute tutor loop with real answers — optional nightly with OPENAI_API_KEY.
 */
const e2eApiHost = process.env.E2E_API_HOST ?? '127.0.0.1';
const e2eApiPort = process.env.E2E_API_PORT ?? '18000';
const e2eStreamlitPort = process.env.E2E_STREAMLIT_PORT ?? '18501';

process.env.E2E_API_HOST = e2eApiHost;
process.env.E2E_API_PORT = e2eApiPort;
process.env.E2E_STREAMLIT_PORT = e2eStreamlitPort;

const baseURL =
  process.env.PLAYWRIGHT_BASE_URL ?? `http://${e2eApiHost}:${e2eStreamlitPort}`;
const demoStorageState = './tests/e2e/.auth/demo-storage-state.json';
const demoWorkers = Math.max(1, parseInt(process.env.DEMO_WORKERS ?? '1', 10) || 1);
const configuredWorkers = Math.max(
  1,
  parseInt(process.env.PLAYWRIGHT_WORKERS ?? process.env.DEMO_WORKERS ?? '1', 10) || 1,
);

export default defineConfig({
  testDir: './tests/e2e',
  globalSetup: './tests/e2e/global-setup.ts',
  workers: configuredWorkers,
  fullyParallel: configuredWorkers > 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ['list'],
    ['html', { open: 'never', outputFolder: 'playwright-report' }],
  ],
  timeout: 30_000,
  expect: { timeout: 5_000 },
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    ...devices['Desktop Chrome'],
    viewport: { width: 1400, height: 900 },
  },
  projects: [
    {
      name: 'smoke',
      grep: /@smoke/,
    },
    {
      name: 'nightly',
      grep: /@nightly/,
      retries: process.env.CI ? 2 : 0,
      timeout: 120_000,
    },
    {
      name: 'nightly-strict',
      grep: /@nightly/,
      retries: 0,
      timeout: 120_000,
    },
    {
      name: 'demo',
      grep: /@demo/,
      testDir: './tests/e2e/demos',
      workers: demoWorkers,
      fullyParallel: false,
      retries: 0,
      timeout: 90_000,
      use: {
        // Демо-тесты намеренно всегда делают скриншоты сами через DemoRecorder —
        // отключаем авто-скрин на фэйле, чтобы не мешать ручному кадру.
        screenshot: 'off',
        video: 'off',
        trace: 'retain-on-failure',
        storageState: demoStorageState,
      },
    },
  ],
  webServer: process.env.PLAYWRIGHT_SKIP_WEBSERVER
    ? undefined
    : {
        command: 'node scripts/e2e_run_stack.mjs',
        url: `http://${e2eApiHost}:${e2eStreamlitPort}/_stcore/health`,
        // Local: reuse a manually started stack (same health URL). PS: free the port or set reuse.
        reuseExistingServer:
          process.env.DEMO_REUSE_SERVER === '1' ||
          process.env.PLAYWRIGHT_REUSE_SERVER === '1',
        timeout: 120_000,
      },
});
