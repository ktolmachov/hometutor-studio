import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 25 — mastery graduation", () => {
  test("@demo captures mastery vector → graduated → weak → tutor CTA", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_25");

    try {
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await waitForStreamlitReady(page);
      await demo.shot("01_mastery_vector_overview", {
        caption: "Mastery vector: обзор по концептам",
        narration: "Один экран показывает, что уже устойчиво, а что требует внимания.",
        fullPage: true,
        waitMs: 500,
      });

      await page.evaluate(() => window.scrollTo(0, 280));
      await waitForStreamlitReady(page);
      await demo.shot("02_graduated_concepts", {
        caption: "Graduated: стабильно освоенные темы",
        narration: "Зелёные концепты можно не трогать перед экзаменом.",
        fullPage: false,
        waitMs: 400,
      });

      await page.getByText(/слаб|weak|mastery/i).first().scrollIntoViewIfNeeded().catch(() => undefined);
      await page.evaluate(() => window.scrollTo(0, 520));
      await waitForStreamlitReady(page);
      await demo.shot("03_weak_concepts_priority", {
        caption: "Weak spots: приоритет на последние дни",
        narration: "Система сама находит темы ниже порога mastery.",
        fullPage: false,
        waitMs: 400,
      });

      await page.evaluate(() => window.scrollTo(0, 120));
      await waitForStreamlitReady(page);
      await demo.shot("04_cta_to_tutor", {
        caption: "CTA «Разобрать» по weak-концепту",
        narration: "Один клик — целевая tutor-сессия по слабому месту.",
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
