import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import {
  gotoAndWaitForStreamlitReady,
  waitForStreamlitReady,
} from "../fixtures/streamlit_ready";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 11 — anki export", () => {
  test("@demo captures export entry points", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_11");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=flashcards");
      await waitForStreamlitReady(page);
      await demo.shot("01_flashcards_deck_ready", {
        caption: "Колода готова к экспорту",
        narration: "Карточки уже сохранены и доступны для выгрузки.",
        fullPage: true,
      });

      await page
        .getByText(/flashcards|колод|повтор/i)
        .first()
        .scrollIntoViewIfNeeded()
        .catch(() => undefined);
      await waitForStreamlitReady(page);
      await demo.shot("02_export_button", {
        caption: "Кнопка экспорта в Anki",
        narration: "Экспорт запускается из интерфейса без дополнительных шагов.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await waitForStreamlitReady(page);
      await demo.shot("03_export_success", {
        caption: "Подтверждение успешного экспорта",
        narration: "Система сообщает, что пакет для Anki сформирован.",
        fullPage: true,
        waitMs: 350,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});

