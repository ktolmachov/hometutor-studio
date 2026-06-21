import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 24 — SSR Pedagogy", () => {
  test("@demo captures SSR pedagogy controls", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_24");

    try {
      await completeFirstRunOnboarding(page);

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=adaptive_plan");
      await page.getByText(/Адаптивный план/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      
      // 01_pedagogy_label
      await demo.shot("01_pedagogy_label", {
        caption: "Педагогическая метка на SSR-карточке",
        narration: "Рекомендация сразу показывает тип действия: retention, recovery или new learning.",
        waitMs: 800,
      });

      // 02_tradeoff_explanation
      await demo.shot("02_tradeoff_explanation", {
        caption: "Visible tradeoffs",
        narration: "Система объясняет, что произойдёт, если отложить повторение или выбрать новую тему.",
        waitMs: 800,
      });

      // 03_learner_steering
      const steeringBtn = page.getByRole("button", { name: /Изменить приоритеты/i }).first();
      if (await steeringBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await steeringBtn.click();
      }
      await waitForStreamlitReady(page);
      await demo.shot("03_learner_steering", {
        caption: "Learner steering",
        narration: "Пользователь меняет приоритеты и видит обновлённую рекомендацию.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
