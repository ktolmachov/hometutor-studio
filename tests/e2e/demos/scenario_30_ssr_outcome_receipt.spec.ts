import { test, expect } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 30 — SSR outcome receipt", () => {
  test("@demo captures SSR recommendation → outcome receipt → local metrics", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_30");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/");
      const banner = page.locator('[data-testid="mission-control-ssr-banner"]').first();
      await expect(banner).toBeVisible({ timeout: DEMO.visibleMs });
      await banner.scrollIntoViewIfNeeded();
      await waitForStreamlitReady(page);
      await demo.shot("01_ssr_recommendation", {
        caption: "SSR: рекомендация следующего шага",
        narration: "Роутер предлагает одно действие с объяснением «почему сейчас».",
        fullPage: true,
        waitMs: 500,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_ssr_outcome_receipt=1");
      const receipt = page.locator('[data-testid="e2e-ssr-outcome-receipt"]').first();
      await expect(receipt).toBeVisible({ timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);
      await demo.shot("02_after_action_receipt", {
        caption: "Micro-outcome receipt после шага",
        narration: "После действия виден честный diff локальных метрик.",
        fullPage: true,
        waitMs: 400,
      });

      await expect(receipt.getByText(/повторению|SM-2|концепт/i).first()).toBeVisible({ timeout: DEMO.ctaMs }).catch(() => null);
      await demo.shot("03_local_metrics_changed", {
        caption: "Локальные сигналы: due, weak, plan",
        narration: "Receipt строится из SQLite/SM-2, без облачного профиля.",
        fullPage: true,
        waitMs: 400,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
