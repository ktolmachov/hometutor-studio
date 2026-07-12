import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 32 — Гость HF Spaces: запуск без установки и ключей", () => {
  test("@demo captures HF Spaces guest flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_32");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: установка DEMO_MODE для имитации HF Spaces
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_hf_spaces_landing
      await demo.shot("01_hf_spaces_landing", {
        caption: "Страница HF Spaces: README + Open кнопка",
        narration: "Репозиторий на HF Spaces — документация и кнопка запуска.",
        waitMs: 800,
      });

      // 02_guest_main_view
      await demo.shot("02_guest_main_view", {
        caption: "Guest UI: упрощённый онбординг с демо-данными",
        narration: "После запуска — рабочий интерфейс без регистрации, предзагруженные примеры.",
        waitMs: 800,
      });

      // 03_guest_limitations_banner
      await demo.shot("03_guest_limitations_banner", {
        caption: "Баннер об ограничениях guest mode",
        narration: "Система сообщает: сохранение сессии временное, ключи не настроены.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
