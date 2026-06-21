import { test } from "@playwright/test";
import {
  gotoAndWaitForStreamlitReady,
  waitForStreamlitReady,
} from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 18 — home retention hub", () => {
  test("@demo captures modes, flashcards surface, progress CTA", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_18");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/");
      const homeReady = await Promise.race([
        page
          .locator(".mode-card")
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
        page
          .locator('[data-testid="e2e-view-switcher"]')
          .first()
          .waitFor({ state: "attached", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
      ]);
      if (!homeReady) {
        throw new Error("Scenario 18: home did not become ready");
      }
      await waitForStreamlitReady(page);
      await demo.shot("01_home_modes_hub", {
        caption: "Six modes on Home",
        narration: "The hub frames the day: answer, tutor, cards, progress.",
        fullPage: true,
        skipReady: true,
        waitMs: 400,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=flashcards");
      await page.locator('[data-testid="stSidebar"]').waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      });
      await waitForStreamlitReady(page);
      await demo.shot("02_flashcards_due_surface", {
        caption: "Flashcards review surface",
        narration: "SM-2 queue has a dedicated mode reachable from Home.",
        fullPage: true,
        skipReady: true,
        waitMs: 400,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await page.getByText("Сводка прогресса").first().waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      });
      await waitForStreamlitReady(page);
      await demo.shot("03_progress_next_actions", {
        caption: "Progress tab with next-step context",
        narration: "Metrics plus a clear suggestion for what to do next.",
        fullPage: true,
        skipReady: true,
        waitMs: 400,
      });

      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);
      await demo.shot("04_back_to_home_rhythm", {
        caption: "Back to Home hub",
        narration: "The loop closes: return to the mode selector after checking progress.",
        fullPage: true,
        skipReady: true,
        waitMs: 400,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
