import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import {
  gotoAndWaitForStreamlitReady,
  waitForStreamlitReady,
} from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 13 — course workspace", () => {
  test("@demo captures course activation to mastery loop", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_13");

    try {
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=topics");
      await page
        .locator('[data-testid="stMain"]')
        .first()
        .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      const topicsReady = await Promise.race([
        page
          .getByRole("button", { name: /Обновить каталог тем/i })
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
        page
          .getByText(/Темы и synthesis/i)
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
      ]);
      if (!topicsReady) {
        throw new Error("Scenario 13: topics view did not become visible");
      }
      await page
        .getByText(/Карта тем/i)
        .first()
        .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await page.waitForTimeout(500);
      await demo.shot("01_activate_course_scope", {
        caption: "Активация папки как курса",
        narration: "Курс выбирается в Темах и становится активной областью.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(
        page,
        "/?e2e_view=qa&e2e_scope_folder=data&e2e_scope_title=Курс%3A+data",
      );
      await waitForStreamlitReady(page);
      await demo.shot("02_scoped_quick_answer", {
        caption: "Scoped быстрый ответ внутри курса",
        narration: "Запросы автоматически ограничены материалами курса.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await waitForStreamlitReady(page);
      await demo.shot("03_course_plan", {
        caption: "План изучения курса",
        narration: "План формируется на основе структуры и текущего прогресса.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=flashcards");
      await waitForStreamlitReady(page);
      await demo.shot("04_course_flashcards", {
        caption: "Генерация карточек курса",
        narration: "Карточки запускают закрепление ключевых концептов.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=tutor");
      await waitForStreamlitReady(page);
      await demo.shot("05_tutor_unknown_recovery", {
        caption: "Маршрут «Не знаю» через Tutor",
        narration: "Тьютор помогает пройти сложные места без срыва сессии.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      await waitForStreamlitReady(page);
      await demo.shot("06_course_mastery_dashboard", {
        caption: "Dashboard курса и mastery",
        narration: "Видно рост mastery и сигнал graduation по курсу.",
        fullPage: true,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});

