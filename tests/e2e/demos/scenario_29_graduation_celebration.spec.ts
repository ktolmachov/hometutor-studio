import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 29 — graduation celebration", () => {
  test("@demo captures delight rail → celebration overlay → graduation CTAs", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_29");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_delight_complete=1&e2e_delight_session=demo-scenario-29");
      await page.locator('[data-testid="delight-step-graduation"], [data-testid="delight-step-review"]').first()
        .waitFor({ state: "visible", timeout: DEMO.visibleMs })
        .catch(() => null);
      await waitForStreamlitReady(page);
      await demo.shot("01_delight_progress_rail", {
        caption: "Delight loop: progress rail на Home",
        narration: "Виден путь Q&A → Tutor → Quiz → Card → Review → Graduation.",
        fullPage: true,
        waitMs: 500,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress&e2e_graduation_celebration=1");
      await page.getByText(/Поздравляем|зафиксирован как освоенный/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await waitForStreamlitReady(page);
      await demo.shot("02_celebration_overlay", {
        caption: "Celebration overlay после mastery ≥ 80%",
        narration: "Система поздравляет с освоением темы и показывает метрики сессии.",
        fullPage: true,
        waitMs: 500,
      });

      await page.getByRole("button", { name: /Следующая тема|Разобрать слабые|На главную/i }).first()
        .waitFor({ state: "visible", timeout: DEMO.ctaMs })
        .catch(() => null);
      await demo.shot("03_graduation_ctas", {
        caption: "CTA: следующая тема / weak / home",
        narration: "Три безопасных следующих шага после graduation.",
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
