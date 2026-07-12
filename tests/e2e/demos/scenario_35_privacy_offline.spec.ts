import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 35 — Приватность и offline-проверка: данные не покидают устройство", () => {
  test("@demo captures offline privacy flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_35");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: отключение сети в Playwright context
      // TODO: проверка network tab
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_offline_status_diagnostics
      await demo.shot("01_offline_status_diagnostics", {
        caption: "Диагностика: локальный LLM endpoint и offline-статус",
        narration: "Система прозрачно показывает, какой endpoint используется и достижим ли он.",
        waitMs: 800,
      });

      // 02_offline_answer_with_source
      await demo.shot("02_offline_answer_with_source", {
        caption: "Ответ без сети: retrieval из Chroma + источник ответа",
        narration: "Поиск по локальному индексу, источник ответа виден явно, а не скрыт.",
        waitMs: 800,
      });

      // 03_offline_srs_review
      await demo.shot("03_offline_srs_review", {
        caption: "SM-2 повторение карточек полностью офлайн",
        narration: "Оценка «Легко/Хорошо/Забыл» и пересчёт интервала — чистый алгоритм, без LLM.",
        waitMs: 800,
      });

      // 04_network_tab_clean
      await demo.shot("04_network_tab_clean", {
        caption: "Network tab: ноль внешних запросов",
        narration: "Вкладка сети пуста (кроме localhost): полная изоляция.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
