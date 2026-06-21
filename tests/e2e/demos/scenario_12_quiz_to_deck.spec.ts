import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import {
  gotoAndWaitForStreamlitReady,
  waitForStreamlitReady,
} from "../fixtures/streamlit_ready";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 12 — quiz to deck", () => {
  test("@demo captures quiz summary to deck flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_12");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=quiz");
      await waitForStreamlitReady(page);
      await demo.shot("01_quiz_summary", {
        caption: "Итоги квиза по теме",
        narration: "Видны сильные и слабые концепты.",
        fullPage: true,
      });

      await page
        .getByText(/quiz|вопрос|ответ|результат/i)
        .first()
        .scrollIntoViewIfNeeded()
        .catch(() => undefined);
      await demo.shot("02_convert_to_deck", {
        caption: "CTA «Сделать колоду из квиза»",
        narration: "Переход к карточкам запускается напрямую из summary.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=flashcards&e2e_fc_section=create");
      await waitForStreamlitReady(page);
      await demo.shot("03_generated_cards_preview", {
        caption: "Предпросмотр карточек из ошибок",
        narration: "Можно проверить и отредактировать карточки перед сохранением.",
        fullPage: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=flashcards&e2e_fc_section=decks");
      await waitForStreamlitReady(page);
      await demo.shot("04_saved_deck_review_ready", {
        caption: "Колода сохранена и готова к review",
        narration: "Новая колода сразу попадает в цикл повторений.",
        fullPage: true,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});

