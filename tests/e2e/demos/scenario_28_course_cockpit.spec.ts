import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { e2eScopeQuery } from "../fixtures/course_scope";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 28 — course cockpit", () => {
  test("@demo captures cockpit header → briefing → rotator → graduation progress", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_28");

    try {
      await gotoAndWaitForStreamlitReady(
        page,
        `/?${e2eScopeQuery({ e2e_view: "course", e2e_cockpit: "1" })}`,
      );
      await page.getByText(/Course Cockpit/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);
      await demo.shot("01_cockpit_header", {
        caption: "Course Cockpit: заголовок и pace mode",
        narration: "Активный курс открывается в режиме v2-кабины.",
        fullPage: true,
        waitMs: 500,
      });

      await page.getByText(/Активность|обзор|briefing/i).first().scrollIntoViewIfNeeded().catch(() => undefined);
      await waitForStreamlitReady(page);
      await demo.shot("02_daily_briefing", {
        caption: "Daily briefing и активность",
        narration: "Центральная колонка показывает обзор сессии и следующий блок.",
        fullPage: true,
        waitMs: 400,
      });

      const rotatorNext = page.getByRole("button", { name: /Далее/i }).first();
      if (await rotatorNext.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await rotatorNext.click();
        await waitForStreamlitReady(page);
      }
      await demo.shot("03_rotator_panel", {
        caption: "Rotator: карточки активностей курса",
        narration: "Переключение между quiz, tutor и карточками без потери scope.",
        fullPage: true,
        waitMs: 400,
      });

      await page.getByText(/Path Map|Прогресс|graduation|mastery/i).first().scrollIntoViewIfNeeded().catch(() => undefined);
      await waitForStreamlitReady(page);
      await demo.shot("04_graduation_progress", {
        caption: "Прогресс курса до graduation",
        narration: "Видно, сколько осталось до завершения курса.",
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
