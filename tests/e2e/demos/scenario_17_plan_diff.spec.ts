import { test, expect } from "@playwright/test";
import {
  gotoAndWaitForStreamlitReady,
  waitForStreamlitReady,
} from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { seedAdaptivePlanConceptsDeltaE2eDb } from "../fixtures/plan_diff_e2e_seed";

test.describe("@demo Scenario 17 — adaptive plan diff", () => {
  test("@demo captures plan delta expander", async ({ page }) => {
    test.setTimeout(240_000);
    const demo = createDemoRecorder(page, "scenario_17");

    try {
      seedAdaptivePlanConceptsDeltaE2eDb();
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=tutor");
      await waitForStreamlitReady(page, 90_000);
      await expect(page.getByText(/Главный режим для обучения/i).first()).toBeVisible({
        timeout: 90_000,
      });
      await demo.shot("01_tutor_plan_header", {
        caption: "Tutor with adaptive plan block",
        narration: "Daily plan sits next to the main learning flow.",
        fullPage: true,
        skipReady: true,
      });

      const planSection = page.getByText(/Адаптивный план и прогноз/i).first();
      await expect(planSection).toBeVisible({ timeout: 30_000 });
      await planSection.click();
      await waitForStreamlitReady(page, 30_000);
      await expect(page.getByText(/Adaptive Daily Plan/i).first()).toBeVisible({
        timeout: 15_000,
      });
      await demo.shot("02_plan_detail_open", {
        caption: "Adaptive Daily Plan expanded",
        narration: "Concrete steps for the day, not a generic todo.",
        fullPage: true,
        skipReady: true,
      });

      const deltaExpander = page.getByText(/Что изменилось в плане/i).first();
      await expect(deltaExpander).toBeVisible({ timeout: 15_000 });
      await deltaExpander.click();
      await page.waitForTimeout(250);
      await waitForStreamlitReady(page, 15_000);
      await demo.shot("03_delta_expander", {
        caption: "Plan delta expander open",
        narration: "One click to see what changed since the last version.",
        fullPage: true,
        skipReady: true,
      });

      await page.getByText(/Появились в шагах|Исчезли из шагов/i).first().waitFor({
        state: "attached",
        timeout: 10_000,
      });
      await page.waitForTimeout(300);
      await demo.shot("04_added_removed_lists", {
        caption: "Added and removed concepts",
        narration: "Explicit concept lists instead of a black-box replan.",
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
