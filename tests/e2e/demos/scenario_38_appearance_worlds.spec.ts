import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 38 — оформление: миры темы", () => {
  test("@demo captures appearance worlds panel", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_38");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=home");
      await waitForStreamlitReady(page);

      await page.getByRole("button", { name: /Настроить интерфейс/i }).first().click({ timeout: DEMO.visibleMs });
      await page.getByRole("tab", { name: /Оформление/i }).click({ timeout: DEMO.visibleMs });
      await page.getByText(/Лес|Океан|Закат|Космос|Ягода/i).first().waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      });
      await waitForStreamlitReady(page);

      await demo.shot("01_appearance_worlds", {
        caption: "Панель оформления: миры темы",
        narration: "Пять цветовых миров помогают быстро подобрать комфортный режим чтения и повторения.",
        fullPage: true,
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
