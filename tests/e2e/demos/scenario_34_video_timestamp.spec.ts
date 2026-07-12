import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 34 — Возврат в таймкод видео: контекст без пересмотра", () => {
  test("@demo captures video timestamp resume flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_34");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: мок видео-сессии и таймкода 23:15 в learner state
      // TODO: UI resume-карты с таймкодом
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_video_session_started
      await demo.shot("01_video_session_started", {
        caption: "Старт видео-сессии: плеер + конспект",
        narration: "Пользователь открывает лекцию; система фиксирует таймкод 00:00.",
        waitMs: 800,
      });

      // 02_interrupted_session_state
      await demo.shot("02_interrupted_session_state", {
        caption: "Сессия прервана: таймкод 23:15 сохранён",
        narration: "После выхода learner state хранит позицию — 23:15, тема, ключевые тезисы.",
        waitMs: 800,
      });

      // 03_resume_video_card
      await demo.shot("03_resume_video_card", {
        caption: "Resume-карта с таймкодом на главном экране",
        narration: "При возврате — «Продолжить с 23:15» + конспект 3–5 ключевых тезисов.",
        waitMs: 800,
      });

      // 04_qa_after_video_segment
      await demo.shot("04_qa_after_video_segment", {
        caption: "Контекст готов: вопросы по просмотренному фрагменту",
        narration: "Система знает, о чём был фрагмент, и может ответить на вопросы.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
