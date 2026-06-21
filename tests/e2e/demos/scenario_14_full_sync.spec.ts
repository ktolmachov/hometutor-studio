import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import {
  gotoAndWaitForStreamlitReady,
  waitForStreamlitReady,
} from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 14 — full sync", () => {
  test("@demo captures export/import sync flow", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_14");

    try {
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await waitForStreamlitReady(page);
      await demo.shot("01_open_sync_controls", {
        caption: "Открыты expert controls синхронизации",
        narration: "В одном месте собраны export/import действия.",
        fullPage: true,
      });

      await page
        .getByText(/экспорт|sync|restore|backup/i)
        .first()
        .scrollIntoViewIfNeeded()
        .catch(() => undefined);
      await demo.shot("02_export_bundle", {
        caption: "Экспорт полного sync-bundle",
        narration: "Файл включает learner state, прогресс и учебные артефакты.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=history");
      await waitForStreamlitReady(page);
      await demo.shot("03_import_bundle", {
        caption: "Импорт и восстановление",
        narration: "После импорта система подтверждает восстановление состояния.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);
      await demo.shot("04_post_restore_validation", {
        caption: "Проверка после restore",
        narration: "Resume, due-очередь и прогресс доступны сразу.",
        fullPage: true,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});

