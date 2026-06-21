import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { ensureSidebarOpen } from "../fixtures/sidebar";

test.describe("@demo Scenario 19 — env / sidebar validation", () => {
  test("@demo captures main shell, sidebar hints, home modes", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_19");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/");
      await page.locator(".mode-card").first().waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      });
      await waitForStreamlitReady(page);
      await demo.shot("01_main_view_ready", {
        caption: "Main UI after onboarding",
        narration: "The app shell renders with modes and navigation controls.",
        fullPage: true,
        skipReady: true,
      });

      await ensureSidebarOpen(page);
      await waitForStreamlitReady(page);
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(200);
      await demo.shot("02_sidebar_env_context", {
        caption: "Sidebar with configuration context",
        narration: "API key hints or provider status appear here when relevant.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/");
      await page.locator(".mode-card").first().waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      });
      await waitForStreamlitReady(page);
      await demo.shot("03_mode_cards_confirmed", {
        caption: "Mode cards confirmed",
        narration: "Ready to start the primary learning scenarios.",
        fullPage: true,
        skipReady: true,
        waitMs: 200,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
