import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 31 — Честный сбой LLM: circuit breaker и fallback", () => {
  test("@demo captures LLM failure flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_31");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: настройка circuit breaker / offline-мода
      // TODO: задать вопрос, дождаться fallback-ответа
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_normal_answer_with_fallback_hint
      await demo.shot("01_normal_answer_with_fallback_hint", {
        caption: "Ответ без LLM: fallback по локальному retrieval",
        narration: "Система отвечает из индекса, но сообщает, что LLM-генерация временно недоступна.",
        waitMs: 800,
      });

      // 02_circuit_breaker_banner
      await demo.shot("02_circuit_breaker_banner", {
        caption: "Circuit breaker banner: провайдер помечен как недоступный",
        narration: "Интерфейс показывает, какой провайдер упал, и подсказывает проверить .env.",
        waitMs: 800,
      });

      // 03_manual_retry_cta
      await demo.shot("03_manual_retry_cta", {
        caption: "Кнопка повторной попытки после восстановления",
        narration: "Когда провайдер снова доступен, система предлагает перегенерировать ответ.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
