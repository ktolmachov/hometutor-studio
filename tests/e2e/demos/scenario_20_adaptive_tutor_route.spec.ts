import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 20 — Adaptive Tutor Route", () => {
  test("@demo captures adaptive tutor progression", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_20");

    try {
      await completeFirstRunOnboarding(page);

      // 01_open_tutor_with_topic
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=tutor");
      await page.locator('[data-testid="stSidebar"]').waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await demo.shot("01_open_tutor_with_topic", {
        caption: "Tutor открыт с активной темой",
        narration: "Пользователь приходит не в пустой чат, а в учебную сессию с контекстом.",
        waitMs: 800,
      });

      // 02_micro_quiz_or_explanation
      const askBtn = page.getByRole("button", { name: /Начать|Отправить/i }).first();
      if (await askBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await askBtn.click();
      }
      await waitForStreamlitReady(page);
      await demo.shot("02_micro_quiz_or_explanation", {
        caption: "Педагогический роутер выбирает turn",
        narration: "Система предлагает объяснение, проверку или разбор в зависимости от состояния.",
        waitMs: 800,
      });

      // 03_after_answer_next_step
      const checkBtn = page.getByRole("button", { name: /Проверить|Далее|Следующий/i }).first();
      if (await checkBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await checkBtn.click();
      }
      await waitForStreamlitReady(page);
      await demo.shot("03_after_answer_next_step", {
        caption: "После ответа есть следующий шаг",
        narration: "Ошибка ведёт к hint и recovery, а успех — к закреплению или новой теме.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
