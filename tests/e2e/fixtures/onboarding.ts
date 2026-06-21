import type { Page } from "@playwright/test";
import { waitForStreamlitReady } from "./streamlit_ready";

/** First launch shows onboarding until «Начать обучение» (KV onboarding_v1_done). */
export async function completeFirstRunOnboarding(page: Page): Promise<void> {
  await page.goto("/");
  // Детеминированный e2e-профиль: приводим старт к post-onboarding состоянию, если onboarding показан.
  await page.locator('[data-testid="stSidebar"]').waitFor({
    state: "visible",
    timeout: 120_000,
  });

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

  // Детерминированная точка синхронизации: view-switcher Streamlit отрисовывает
  // после mode selector + основного контента. `attached` — потому что native
  // select скрыт Streamlit'ом, но присутствует в DOM.
  await page.locator('[data-testid="e2e-view-switcher"]').waitFor({
    state: "attached",
    timeout: 180_000,
  });

  // Плюс `.mode-card` visible — гарантирует, что Mission Control завершил
  // рендер домашних плиток после первого запуска.
  await page
    .locator(".mode-card")
    .first()
    .waitFor({ state: "visible", timeout: 60_000 });

  // Streamlit keeps a websocket open, so networkidle is not a reliable ready signal.
  await waitForStreamlitReady(page, 60_000);
}
