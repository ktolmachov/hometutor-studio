import type { Page } from '@playwright/test';
import { DEMO } from './demo_timeouts';

export const STREAMLIT_READY_SELECTOR = '[data-testid="e2e-streamlit-ready"]';
const STREAMLIT_APP_SELECTOR = '.stApp';

export async function waitForStreamlitReady(
  page: Page,
  timeout = 6_000,
): Promise<void> {
  const deadline = Date.now() + timeout;
  let lastError: unknown;
  while (Date.now() < deadline) {
    try {
      const hasReadyMarker = (await page.locator(STREAMLIT_READY_SELECTOR).count()) > 0;
      if (hasReadyMarker) {
        await page.locator(STREAMLIT_READY_SELECTOR).last().waitFor({
          state: 'attached',
          timeout: Math.min(1_500, Math.max(250, deadline - Date.now())),
        });
        return;
      }
      // Fallback for transient marker loss during rerun: app root is attached and visible.
      const appRoot = page.locator(STREAMLIT_APP_SELECTOR).first();
      if (await appRoot.isVisible({ timeout: 500 }).catch(() => false)) {
        return;
      }
    } catch (err) {
      lastError = err;
    }
    await page.waitForTimeout(250);
  }
  const currentUrl = page.url();
  throw new Error(
    `Streamlit ready timeout after ${timeout}ms at ${currentUrl}. ` +
      `Marker: ${STREAMLIT_READY_SELECTOR}. Last error: ${String(lastError ?? 'none')}`,
  );
}

export async function gotoAndWaitForStreamlitReady(
  page: Page,
  url: string,
  timeout = DEMO.navigationReadyMs,
): Promise<void> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= 2; attempt += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded' });
      lastError = undefined;
      break;
    } catch (err) {
      lastError = err;
      if (attempt === 2) {
        throw err;
      }
      await page.waitForTimeout(300);
    }
  }
  await waitForStreamlitReady(page, timeout);
}
