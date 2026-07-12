import type { Page } from '@playwright/test';
import { DEMO } from './demo_timeouts';

export const STREAMLIT_READY_SELECTOR = '[data-testid="e2e-streamlit-ready"]';
const STREAMLIT_APP_FALLBACK_SELECTORS = [
  '[data-testid="stApp"]',
  '[data-testid="stAppViewContainer"]',
  '[data-testid="stMain"]',
  '.stApp',
];
const TRANSIENT_GOTO_ERRORS = [
  'ERR_NO_BUFFER_SPACE',
  'ERR_CONNECTION_RESET',
  'ERR_CONNECTION_CLOSED',
  'ERR_EMPTY_RESPONSE',
];

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
      // Fallback for transient marker loss during rerun and Streamlit DOM changes.
      for (const selector of STREAMLIT_APP_FALLBACK_SELECTORS) {
        const appRoot = page.locator(selector).first();
        if (await appRoot.isVisible({ timeout: 250 }).catch(() => false)) {
          return;
        }
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
  await gotoStreamlitPage(page, url);
  await waitForStreamlitReady(page, timeout);
}

export async function gotoStreamlitPage(
  page: Page,
  url: string,
  attempts = 3,
): Promise<void> {
  let lastError: unknown;
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    try {
      await page.goto(url, { waitUntil: 'domcontentloaded' });
      return;
    } catch (err) {
      lastError = err;
      const message = String(err);
      const transient = TRANSIENT_GOTO_ERRORS.some((part) => message.includes(part));
      if (attempt === attempts || !transient) {
        throw err;
      }
      await page.waitForTimeout(500 * attempt);
    }
  }
  throw lastError;
}
