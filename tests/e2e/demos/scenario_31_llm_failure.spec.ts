import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 31 — Честный сбой LLM: локальный endpoint недоступен", () => {
  test("@demo captures LLM failure flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_31");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: настройка недоступного локального LLM endpoint / offline-мода
      // TODO: открыть SSR/offline banner и диагностику local LLM
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_llm_local_banner_reachable_false
      await demo.shot("01_llm_local_banner_reachable_false", {
        caption: "Баннер: локальная LLM недоступна",
        narration: "«Локальная LLM недоступна — SSR работает в template-режиме»: endpoint не отвечает, карточка формируется по шаблону без персонализации.",
        waitMs: 800,
      });

      // 02_banner_action_hint
      await demo.shot("02_banner_action_hint", {
        caption: "Конкретное действие: какой сервер запустить и какую модель загрузить",
        narration: "Баннер называет base_url и модель — запустите LM Studio и загрузите именно её.",
        waitMs: 800,
      });

      // 03_diagnostics_expander
      await demo.shot("03_diagnostics_expander", {
        caption: "Раскрытые детали диагностики: base_url и модель одной строкой",
        narration: "Expander «Подробности диагностики local LLM» — тот же base_url/model в code-блоке.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
