import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 33 — Экспорт живой карты: Knowledge Graph в Markdown", () => {
  test("@demo captures KG export flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_33");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: навигация в раздел Knowledge Graph
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_kg_export_button
      await demo.shot("01_kg_export_button", {
        caption: "Knowledge Graph с кнопкой экспорта",
        narration: "В панели графа — кнопка «Экспорт в Markdown».",
        waitMs: 800,
      });

      // 02_export_mermaid_preview
      await demo.shot("02_export_mermaid_preview", {
        caption: "Предпросмотр экспорта: Mermaid-диаграмма",
        narration: "Markdown с Mermaid-блоком: узлы, связи, mastery-статус.",
        waitMs: 800,
      });

      // 03_export_saved
      await demo.shot("03_export_saved", {
        caption: "Файл экспорта сохранён локально",
        narration: "Система сообщает путь к .md файлу и предлагает открыть.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
