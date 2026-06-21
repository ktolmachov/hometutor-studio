import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

/**
 * Demo scenario #03 — Ответ → Tutor за один клик.
 *
 * Снимает 5 кадров по doc/scenarios/scenario_03_answer_to_tutor.yaml.
 * Под HOME_RAG_E2E_OFFLINE=1 показывает qa-view с offline-ответом,
 * затем переходит в tutor-view через e2e_view=tutor.
 *
 * Запуск: npm run test:e2e:demo
 */
test.describe("@demo Scenario 03 — answer to tutor", () => {
  test("@demo captures answer → tutor context handoff → plan → explanation", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_03");

    try {
      await completeFirstRunOnboarding(page);

      // Shot 01 — qa-view с ответом и CTA "Учить эту тему".
      let quickAnswerReady = false;
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        await gotoAndWaitForStreamlitReady(page, "/?e2e_view=qa");
        const inputProbe = page.getByRole("textbox").first();
        quickAnswerReady = await inputProbe
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false);
        if (quickAnswerReady) {
          break;
        }
        await page.waitForTimeout(300);
      }
      if (!quickAnswerReady) {
        throw new Error("Scenario 03: Quick Answer input did not become visible");
      }
      const input = page.getByRole("textbox").first();

      const hasLiveLlm = Boolean(process.env.OPENAI_API_KEY);
      if (hasLiveLlm) {
        await input.click();
        await input.pressSequentially("Что такое retrieval augmented generation?", { delay: 30 });
        await waitForStreamlitReady(page);
        const submitBtn = page.getByRole("button", { name: /Получить ответ/i }).first();
        await submitBtn.waitFor({ state: "visible", timeout: DEMO.ctaMs });
        await submitBtn.click();
        await page
          .getByText(/E2E offline stub response|offline stub|Stub source/i)
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      }
      await waitForStreamlitReady(page);

      // CTA «Учить эту тему» — показываем если есть, иначе раскрываем эксперт-блок.
      const learnCta = page
        .getByRole("button", { name: /Учить эту тему/i })
        .first();
      if (await learnCta.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await learnCta.scrollIntoViewIfNeeded();
      } else {
        const expertExpander = page
          .getByRole("button", { name: /Расширенное управление/i })
          .first();
        if (
          await expertExpander
            .isVisible({ timeout: DEMO.ctaMs })
            .catch(() => false)
        ) {
          await expertExpander.click();
          await waitForStreamlitReady(page);
        }
      }
      await demo.shot("01_answer_with_learn_cta", {
        caption: "Готовый ответ с кнопкой «Учить эту тему 5 минут»",
        narration:
          "Аня видит ответ — и прямо здесь предложение перейти в режим обучения.",
        fullPage: true,
        waitMs: 400,
      });

      // Shot 02 — tutor-view: контекст передан.
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=tutor");
      await page
        .locator('[data-testid="stSidebar"]')
        .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);
      await demo.shot("02_tutor_context_handoff", {
        caption: "Tutor открыт: контекст темы и вопроса сохранён",
        narration:
          "Переход без потери контекста — тема и исходный вопрос уже в Tutor.",
        fullPage: true,
        waitMs: 600,
      });

      // Shot 03 — план разбора (3 шага).
      await waitForStreamlitReady(page);
      await demo.shot("03_tutor_topic_plan", {
        caption: "План разбора темы: 3 шага",
        narration:
          "Система предлагает структуру: что объяснить и в каком порядке.",
        fullPage: true,
      });

      // Shot 04 — объяснение простыми словами.
      await waitForStreamlitReady(page);
      await demo.shot("04_tutor_simple_explanation", {
        caption: "Объяснение простыми словами — шаг 1",
        narration: "Первый шаг плана: концепция объяснена без жаргона.",
        fullPage: true,
      });

      // Shot 05 — CTA «Следующий шаг: проверь понимание».
      await waitForStreamlitReady(page);
      const nextStepCta = page
        .getByRole("button", { name: /Следующий шаг|проверь понимание/i })
        .first();
      if (await nextStepCta.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await nextStepCta.scrollIntoViewIfNeeded();
      }
      await demo.shot("05_tutor_next_step_cta", {
        caption: "CTA «Следующий шаг: проверь понимание»",
        narration:
          "Tutor сам предлагает перейти к проверке — мост к мини-квизу.",
        fullPage: true,
        // Stabilize final frame in CI before recording CTA shot.
        waitMs: 600,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
