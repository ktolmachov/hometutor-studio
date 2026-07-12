import type { Page } from "@playwright/test";
import {
  STREAMLIT_READY_SELECTOR,
  gotoStreamlitPage,
  waitForStreamlitReady,
} from "./streamlit_ready";

const POST_ONBOARDING_SHELL_SELECTOR = [
  '[data-testid="e2e-view-switcher"]',
  STREAMLIT_READY_SELECTOR,
  '[data-testid="mission-control-ssr-banner"]',
  '[data-testid="first-session-hero"]',
].join(", ");

const MISSION_CONTROL_CONTENT_SELECTOR = [
  '[data-testid^="mission-tile-"]',
  ".mode-card",
  '[data-testid="mission-control-ssr-banner"]',
  '[data-testid="first-session-hero"]',
  '[data-testid="mc-kg-card"]',
].join(", ");

/** First launch shows onboarding until «Начать обучение» (KV onboarding_v1_done). */
export async function completeFirstRunOnboarding(page: Page): Promise<void> {
  await gotoStreamlitPage(page, "/");
  // Детеминированный e2e-профиль: приводим старт к post-onboarding состоянию, если onboarding показан.
  await waitForStreamlitReady(page, 120_000);

  const startButton = page.getByRole("button", { name: "Начать обучение" });
  if (await startButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
    const welcomeHeading = page.getByRole("heading", {
      name: /Добро пожаловать/i,
    });
    await startButton.click();
    await welcomeHeading.waitFor({ state: "hidden", timeout: 60_000 });
  }

  const mainLink = page.getByRole("link", { name: /^main$/i });
  if (await mainLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await mainLink.click();
  }

  // Детерминированная точка синхронизации после Streamlit rerun: e2e markers
  // and home anchors are attached even when the native select itself is hidden.
  await page.locator(POST_ONBOARDING_SHELL_SELECTOR).first().waitFor({
    state: "attached",
    timeout: 180_000,
  });

  // Mission Control renders tiles through Streamlit HTML containers. Depending
  // on the current Streamlit build those nodes may be attached while Playwright
  // reports the raw HTML node itself as hidden, so visibility is checked by
  // scenario specs that need visual assertions.
  await page
    .locator(MISSION_CONTROL_CONTENT_SELECTOR)
    .first()
    .waitFor({ state: "attached", timeout: 60_000 });

  // Streamlit keeps a websocket open, so networkidle is not a reliable ready signal.
  await waitForStreamlitReady(page, 60_000);
}
