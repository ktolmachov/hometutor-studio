import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 15 — UX Breakthrough", () => {
  test("@demo captures wait UX → tutor handoff → progress receipt", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_15");

    try {
      await completeFirstRunOnboarding(page);

      // Shot 01 — wait UX (Skeleton screens)
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=qa");
      const input = page.getByRole("textbox").first();
      await input.waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await input.click();
      await input.fill("Test question for UX breakthrough?");
      await input.press("Enter");
      
      // Wait for skeleton or progress indicator
      await page.waitForTimeout(500); 
      await demo.shot("01_wait_ux", {
        caption: "Skeleton/progressive reveal вместо немого ожидания",
        narration: "Пользователь видит первый полезный сигнал меньше чем за две секунды.",
        waitMs: 500,
      });

      // Wait for answer
      await page.getByText("Ответ", { exact: true }).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await waitForStreamlitReady(page);

      // Shot 02 — Tutor handoff
      const learnCta = page.getByRole("button", { name: /Учить эту тему/i }).first();
      if (await learnCta.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await learnCta.click();
      }
      await page.getByText(/Последний вопрос|Начать диалог/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await demo.shot("02_tutor_handoff", {
        caption: "Переход Q&A → Tutor без потери контекста",
        narration: "Тьютор знает вопрос, тему и источники, с которыми пришёл пользователь.",
        waitMs: 800,
      });

      // Shot 03 — Progress receipt
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await page.getByText("Сводка прогресса").first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await demo.shot("03_progress_receipt", {
        caption: "Мотивационный receipt после учебного шага",
        narration: "Система показывает не только действие, но и образовательный результат.",
        waitMs: 800,
        fullPage: true,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
