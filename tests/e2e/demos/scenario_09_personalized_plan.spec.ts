import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";

/**
 * Demo scenario #09 — Персональный план обучения.
 *
 * Снимает 5 кадров по doc/scenarios/scenario_09_personalized_plan.yaml.
 * Под HOME_RAG_E2E_OFFLINE=1 открывает progress-view через e2e_view=progress.
 *
 * Запуск: npm run test:e2e:demo
 */
test.describe("@demo Scenario 09 — personalized plan", () => {
  test("@demo captures plan overview → gaps → diff → today action → adjust", async ({
    page,
  }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_09");

    try {

      // Shot 01 — progress-view: обзор плана на неделю.
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await page
        .locator('[data-testid="stSidebar"]')
        .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);
      await demo.shot("01_plan_overview", {
        caption: "Обзор плана на неделю: 3 приоритетные темы",
        narration: "Система отобрала три темы — не весь учебник, а именно эти.",
        fullPage: true,
        waitMs: 600,
      });

      // Shot 02 — «Почему здесь» (weak spots per тема).
      await waitForStreamlitReady(page);
      await demo.shot("02_plan_derived_from_gaps", {
        caption: "«Почему здесь»: weak spot по каждой теме",
        narration: "Не просто список — объяснение почему эта тема приоритетна.",
        fullPage: true,
        waitMs: 400,
      });

      // Shot 03 — diff с прошлой сессией.
      const diffSection = page.getByText(/изменилось|diff|прошл|last session/i).first();
      if (await diffSection.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await diffSection.scrollIntoViewIfNeeded();
        await waitForStreamlitReady(page);
      }
      await demo.shot("03_plan_diff_since_last", {
        caption: "Diff с прошлой сессией: что изменилось",
        narration: "План живёт вместе с прогрессом — обновился с последней сессии.",
        fullPage: true,
        waitMs: 400,
      });

      // Shot 04 — «Сегодня: разобрать X».
      const todayCta = page.getByText(/сегодня|today|разобрать/i).first();
      if (await todayCta.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await todayCta.scrollIntoViewIfNeeded();
        await waitForStreamlitReady(page);
      }
      await demo.shot("04_plan_today_action", {
        caption: "«Сегодня: разобрать X (8 мин)»",
        narration: "Одно действие на сегодня — не список на неделю вперёд.",
        fullPage: true,
        waitMs: 400,
      });

      // Shot 05 — корректировка приоритета.
      const adjustBtn = page
        .getByRole("button", { name: /Скорректировать|Изменить|Adjust|Reorder/i })
        .first();
      if (await adjustBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await adjustBtn.click();
        await waitForStreamlitReady(page);
      }
      await demo.shot("05_plan_accepts_adjust", {
        caption: "Корректировка приоритета → пересчёт плана",
        narration: "Сдвинула тему вниз — план пересчитался мгновенно.",
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
