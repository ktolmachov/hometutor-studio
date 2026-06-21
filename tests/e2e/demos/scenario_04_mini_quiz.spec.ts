import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";

/**
 * Demo scenario #04 — Мини-квиз: проверь понимание за 2 мин.
 *
 * Снимает 4 кадра по doc/scenarios/scenario_04_mini_quiz.yaml.
 * Под HOME_RAG_E2E_OFFLINE=1 открывает quiz-view напрямую через e2e_view=quiz.
 *
 * Запуск: npm run test:e2e:demo
 */
test.describe("@demo Scenario 04 — mini quiz", () => {
  test("@demo captures quiz question → answer → feedback → next action", async ({
    page,
  }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_04");

    try {

      // Shot 01 — quiz-view с вопросом.
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=quiz");
      await page
        .locator('[data-testid="stSidebar"]')
        .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);
      await demo.shot("01_quiz_question_presented", {
        caption: "Вопрос квиза: 3 варианта ответа",
        narration: "Система сформулировала вопрос по теме — Аня выбирает из трёх.",
        fullPage: true,
        waitMs: 600,
        watermark: "scenario_04 • step_01",
      });

      // Shot 02 — выбранный вариант (если есть radio-кнопки, кликаем первую).
      const firstOption = page.getByRole("radio").first();
      if (await firstOption.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await firstOption.click();
        await waitForStreamlitReady(page);
      }
      await page.evaluate(() => window.scrollTo(0, 220));
      await demo.shot("02_quiz_answer_selected", {
        caption: "Выбранный вариант подсвечен",
        narration: "Один клик — вариант зафиксирован, ожидание feedback.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_04 • step_02",
      });

      // Shot 03 — feedback после submit (если есть кнопка «Проверить»).
      const checkBtn = page
        .getByRole("button", { name: /Проверить|Submit|Check/i })
        .first();
      if (await checkBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await checkBtn.click();
        await waitForStreamlitReady(page);
      }
      await page.evaluate(() => window.scrollTo(0, 420));
      await demo.shot("03_quiz_feedback_correct_or_hint", {
        caption: "Feedback: ✅ правильно или ❌ + подсказка",
        narration: "Мгновенный ответ с объяснением — не просто «неверно».",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_04 • step_03",
      });

      // Shot 04 — CTA «Создать flashcard» / «Продолжить».
      const nextCta = page
        .getByRole("button", { name: /Создать flashcard|Продолжить|Следующий/i })
        .first();
      if (await nextCta.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await nextCta.scrollIntoViewIfNeeded();
      }
      await page.evaluate(() => window.scrollTo(0, 640));
      await demo.shot("04_quiz_next_action_cta", {
        caption: "CTA: «Создать flashcard» / «Продолжить»",
        narration: "Правильно? Идём дальше. Ошиблись? Карточка в SRS-очередь.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_04 • step_04",
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
