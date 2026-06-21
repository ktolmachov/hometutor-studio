import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import {
  gotoAndWaitForStreamlitReady,
  waitForStreamlitReady,
} from "../fixtures/streamlit_ready";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 10 — day2 resume", () => {
  test("@demo captures resume + soft-recovery flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_10");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/");
      const homeReady = await Promise.race([
        page
          .locator(".tutorial-ribbon, .mode-card, .home-dash-card")
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
        throw new Error("Scenario 10: home view did not become ready");
      }
      await demo.shot("01_home_resume_card", {
        caption: "Resume-карта на главной",
        narration: "Сразу видно, откуда продолжить и какой следующий шаг.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await waitForStreamlitReady(page);
      await demo.shot("02_plan_diff_today", {
        caption: "План на сегодня с diff «что изменилось»",
        narration: "План подстроился под паузу и текущий контекст.",
        fullPage: true,
      });

      await page
        .getByText(/к повторению|due|повтор/i)
        .first()
        .scrollIntoViewIfNeeded()
        .catch(() => undefined);
      await waitForStreamlitReady(page);
      await demo.shot("03_due_queue_soft_recovery", {
        caption: "Due-очередь после пропуска без перегруза",
        narration: "Очередь распределена мягко, без лавины overdue.",
        fullPage: true,
        waitMs: 300,
      });

      await page
        .getByText(/reindex|индекс|профил/i)
        .first()
        .scrollIntoViewIfNeeded()
        .catch(() => undefined);
      await waitForStreamlitReady(page);
      await demo.shot("04_reindex_profile_badge", {
        caption: "Бейдж обновления профиля после reindex",
        narration: "Учебное состояние сохраняется после обновления индекса.",
        fullPage: true,
        waitMs: 300,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});

