import { chromium, type FullConfig } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const DEMO_STORAGE_STATE = path.resolve(
  process.cwd(),
  'tests',
  'e2e',
  '.auth',
  'demo-storage-state.json',
);
const DEMO_AUTH_DIR = path.dirname(DEMO_STORAGE_STATE);

function isDemoRun(): boolean {
  const args = process.argv;
  const hasProjectFilter = args.some(
    (arg) => arg === '--project' || arg.startsWith('--project='),
  );
  if (!hasProjectFilter) {
    return true;
  }
  return args.some((arg, index) => {
    if (arg === '--project=demo') return true;
    return arg === '--project' && args[index + 1] === 'demo';
  });
}

/**
 * Preflight только для `npm run test:e2e:nightly:strict` (см. package.json: PLAYWRIGHT_NIGHTLY_STRICT=1).
 * Не привязываем к наличию проекта `nightly-strict` в playwright.config — иначе любой прогон
 * (включая `--project=smoke`) требовал бы ключ в globalSetup.
 */
export default async function globalSetup(config: FullConfig): Promise<void> {
  if (process.env.PLAYWRIGHT_NIGHTLY_STRICT !== '1') {
    if (!isDemoRun()) {
      return;
    }

    const demoProject = config.projects.find((project) => project.name === 'demo');
    const baseURL = String(demoProject?.use?.baseURL ?? config.projects[0]?.use?.baseURL ?? '');
    if (!baseURL) {
      throw new Error('demo globalSetup failed: baseURL is not configured.');
    }

    fs.mkdirSync(path.dirname(DEMO_STORAGE_STATE), { recursive: true });
    const workerCount = Math.max(1, parseInt(process.env.DEMO_WORKERS ?? '2', 10) || 2);
    const browser = await chromium.launch();
    try {
      const page = await browser.newPage({ baseURL });
      await completeFirstRunOnboarding(page);
      await page.context().storageState({ path: DEMO_STORAGE_STATE });
      const stateRaw = fs.readFileSync(DEMO_STORAGE_STATE, 'utf-8');
      for (let idx = 0; idx < workerCount; idx += 1) {
        const workerStatePath = path.join(DEMO_AUTH_DIR, `demo-storage-state-${idx}.json`);
        fs.writeFileSync(workerStatePath, stateRaw, 'utf-8');
      }
    } finally {
      await browser.close();
    }

    return;
  }

  const apiKey = (process.env.OPENAI_API_KEY || '').trim();
  if (!apiKey) {
    throw new Error(
      'nightly-strict preflight failed: OPENAI_API_KEY is required. ' +
        'Set OPENAI_API_KEY before running "npm run test:e2e:nightly:strict".',
    );
  }
}
