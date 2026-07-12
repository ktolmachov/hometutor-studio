import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 32 — Публичное демо на HF Spaces: без установки и без своего LLM", () => {
  test("@demo captures HF Spaces guest flow", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_32");

    try {
      await completeFirstRunOnboarding(page);

      // TODO: открыть публичный HF Space / локальный стенд deploy/hf-spaces
      await gotoAndWaitForStreamlitReady(page, "/");
      await waitForStreamlitReady(page);

      // 01_hf_spaces_public_url
      await demo.shot("01_hf_spaces_public_url", {
        caption: "Публичная ссылка HF Space: README и статус",
        narration: "Открывает ссылку — сразу видно, что это работающий, а не спящий Space.",
        waitMs: 800,
      });

      // 02_quick_signup
      await demo.shot("02_quick_signup", {
        caption: "Короткая регистрация: email + пароль",
        narration: "AUTH_ENABLED=true — обычная быстрая регистрация, без ключей и настроек.",
        waitMs: 800,
      });

      // 03_demo_course_first_answer
      await demo.shot("03_demo_course_first_answer", {
        caption: "Первый ответ по предзагруженному демо-курсу",
        narration: "Демо-корпус уже в индексе — вопрос и ответ с источниками сразу после входа.",
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
