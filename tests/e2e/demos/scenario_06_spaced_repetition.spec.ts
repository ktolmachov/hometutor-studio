import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

/**
 * Demo scenario #06 — SRS: повторение по интервальному алгоритму.
 *
 * Снимает 5 кадров по doc/scenarios/scenario_06_spaced_repetition.yaml.
 * Под HOME_RAG_E2E_OFFLINE=1 открывает Home и flashcards-view через e2e_view.
 *
 * Запуск: npm run test:e2e:demo
 */
test.describe("@demo Scenario 06 — spaced repetition", () => {
  test("@demo captures due badge → review queue → card flip → grade → progress", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_06");

    try {
      await completeFirstRunOnboarding(page);

      // Shot 01 — Home с бейджем «К повторению».
      await gotoAndWaitForStreamlitReady(page, "/");
      const homeReady = await Promise.race([
        page
          .locator(".mode-card")
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
        page
          .getByText(/К повторению|повторить|review/i)
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
        page
          .locator('[data-testid="e2e-view-switcher"]')
          .first()
          .waitFor({ state: "attached", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
      ]);
      if (!homeReady) {
        throw new Error("Scenario 06: home ready indicators did not appear");
      }
      await waitForStreamlitReady(page);
      await demo.shot("01_home_due_badge", {
        caption: "Бейдж «К повторению» на главном экране",
        narration: "Аня заходит — система уже знает: 12 карточек пора повторить.",
        fullPage: true,
        waitMs: 600,
      });

      // Shot 02 — flashcards-view: очередь повторения.
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=flashcards");
      await page
        .locator('[data-testid="stSidebar"]')
        .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);
      await demo.shot("02_review_queue_opened", {
        caption: "Очередь повторения открыта: верхняя карточка",
        narration: "Одна карточка за раз — без перегрузки.",
        fullPage: true,
        waitMs: 600,
      });

      // Shot 03 — раскрываем карточку (кнопка «Показать ответ» / «Flip»).
      const flipBtn = page
        .getByRole("button", { name: /Показать ответ|Flip|Раскрыть/i })
        .first();
      if (await flipBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await flipBtn.click();
        await waitForStreamlitReady(page);
      }
      await demo.shot("03_card_flipped_answer", {
        caption: "Карточка раскрыта: ответ + 4 кнопки SM-2",
        narration: "Оцени насколько помнишь: от «Забыл» до «Легко».",
        fullPage: true,
        waitMs: 400,
      });

      // Shot 04 — выбираем оценку «Хорошо» (grade=3 / Good).
      const goodBtn = page
        .getByRole("button", { name: /Хорошо|Good|3/i })
        .first();
      if (await goodBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await goodBtn.click();
        await waitForStreamlitReady(page);
      }
      await demo.shot("04_grade_selected_state_update", {
        caption: "Оценка выбрана — карточка уходит из очереди",
        narration: "Выбрал «Хорошо» — карточка переносится на +4 дня.",
        fullPage: true,
        waitMs: 400,
      });

      // Shot 05 — прогресс очереди.
      await waitForStreamlitReady(page);
      await demo.shot("05_queue_progress", {
        caption: "Прогресс очереди: «11 осталось, ~4 мин»",
        narration: "Видно сколько осталось и когда закончишь — не бесконечный список.",
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
