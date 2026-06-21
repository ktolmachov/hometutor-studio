import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";

/**
 * Demo scenario #07 — Прогресс и слабые места.
 *
 * Снимает 4 кадра по doc/scenarios/scenario_07_progress_gaps.yaml.
 * Под HOME_RAG_E2E_OFFLINE=1 открывает progress-view через e2e_view=progress.
 *
 * Запуск: npm run test:e2e:demo
 */
test.describe("@demo Scenario 07 — progress gaps", () => {
  test("@demo captures progress strip → timeline → weak spots → streak", async ({
    page,
  }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_07");

    try {

      // Shot 01 — progress-view: полоса прогресса.
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await page
        .locator('[data-testid="stSidebar"]')
        .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);
      await demo.shot("01_progress_unified_strip", {
        caption: "Полоса прогресса: тема / mastery% / due / streak",
        narration: "Один взгляд — вся картина: что знаешь, что пора повторить.",
        fullPage: true,
        waitMs: 600,
        watermark: "scenario_07 • step_01",
      });

      // Shot 02 — скролл к графику mastery.
      await waitForStreamlitReady(page);
      await page.evaluate(() => window.scrollTo(0, 260));
      await demo.shot("02_mastery_timeline", {
        caption: "График mastery за 7 дней",
        narration: "Кривая роста — видно, что знания накапливаются.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_07 • step_02",
      });

      // Shot 03 — слабые темы (weak spots panel).
      const weakPanel = page.getByText(/слабые|weak|mastery/i).first();
      if (await weakPanel.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await weakPanel.scrollIntoViewIfNeeded();
        await waitForStreamlitReady(page);
      }
      await page.evaluate(() => window.scrollTo(0, 520));
      await demo.shot("03_weak_spots_panel", {
        caption: "Слабые темы (mastery < 50%) + CTA «Разобрать»",
        narration: "Три темы, требующие внимания — система сама их нашла.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_07 • step_03",
      });

      // Shot 04 — streak и следующее действие.
      await page.evaluate(() => window.scrollTo(0, 40));
      await waitForStreamlitReady(page);
      await demo.shot("04_streak_and_next_action", {
        caption: "Streak 5 дней + предложение на сегодня",
        narration: "Серия не прерывается — система знает когда ты учился.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_07 • step_04",
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
