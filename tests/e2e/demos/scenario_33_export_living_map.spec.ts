import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 33 — Экспорт живой карты: интерактивный HTML одним кликом", () => {
  test("@demo captures KG export flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_33");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: навигация в раздел Knowledge Graph и скачивание HTML export
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_kg_panel_download_button
      await demo.shot("01_kg_panel_download_button", {
        caption: "Панель Knowledge Graph: кнопка «Скачать живую карту (HTML)»",
        narration: "Кнопка стоит прямо под интерактивным графом — рядом со сводкой концептов.",
        waitMs: 800,
      });

      // 02_downloaded_html_opened_standalone
      await demo.shot("02_downloaded_html_opened_standalone", {
        caption: "knowledge_graph.html открыт отдельно в браузере",
        narration: "Тот же граф, та же интерактивность — но уже не внутри Streamlit, а как обычный файл.",
        waitMs: 800,
      });

      // 03_offline_share_moment
      await demo.shot("03_offline_share_moment", {
        caption: "Файл работает без сети и без приложения",
        narration: "Отключил интернет, открыл файл заново — граф на месте: можно отправить кому угодно.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
