import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 27 — incremental reindex", () => {
  test("@demo captures topics → reindex badge → preserved mastery → new plan", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_27");

    try {
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=topics");
      await page.getByText(/Темы|Карта тем/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await waitForStreamlitReady(page);
      await demo.shot("01_topics_catalog_ready", {
        caption: "Темы: каталог после добавления материалов",
        narration: "Новые документы попадают в каталог тем без ручной разметки.",
        fullPage: true,
        waitMs: 400,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress&e2e_reindex_badge=1");
      await page.getByText(/Профиль обновлён после переиндексации/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await waitForStreamlitReady(page);
      await demo.shot("02_reindex_profile_badge", {
        caption: "Бейдж: профиль обновлён после reindex",
        narration: "Mastery rehydrated — learner state сохранён поверх нового индекса.",
        fullPage: true,
        waitMs: 400,
      });

      await page.evaluate(() => window.scrollTo(0, 200));
      await waitForStreamlitReady(page);
      await demo.shot("03_mastery_preserved", {
        caption: "Mastery vector без обнуления",
        narration: "Прежние концепты остаются на своих уровнях освоения.",
        fullPage: false,
        waitMs: 400,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=adaptive_plan");
      await page.getByText(/план|Plan|New|нов/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await waitForStreamlitReady(page);
      await demo.shot("04_new_concepts_in_plan", {
        caption: "Adaptive Plan: новые концепты в блоке New",
        narration: "Система предлагает свежие темы из новых файлов отдельно от gap.",
        fullPage: true,
        waitMs: 400,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
