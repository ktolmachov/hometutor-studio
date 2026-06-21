import { test, expect } from "@playwright/test";
import {
  gotoAndWaitForStreamlitReady,
} from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 16 — interactive tour", () => {
  test("@demo captures chapters 1–2 + resume after reload", async ({ page }) => {
    test.setTimeout(300_000);
    const demo = createDemoRecorder(page, "scenario_16");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_tour_start=1");
      await expect(page.locator(".tutorial-callout")).toContainText(/Глава 1\. Первый ответ/i, {
        timeout: 60_000,
      });
      await demo.shot("01_home_tour_entry", {
        caption: "Home: tour entry overlay",
        narration: "Structured onboarding from the first screen.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_tour_chapter=0&e2e_tour_step=1");
      await expect(page.locator(".tutorial-callout")).toContainText(/Попробуйте пример вопроса/i);
      await demo.shot("02_chapter1_practice_step", {
        caption: "Chapter 1: practice question step",
        narration: "The tour walks through a real first-answer path.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_tour_chapter=0&e2e_tour_step=2");
      await expect(page.locator(".tutorial-callout")).toContainText(
        /Проверьте источники и доверие/i,
      );
      await demo.shot("03_chapter1_trust_step", {
        caption: "Chapter 1: sources and trust",
        narration: "Users see how to verify answers against retrieved evidence.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_tour_chapter=1&e2e_tour_step=0");
      await expect(page.locator(".tutorial-callout")).toContainText(
        /Глава 2\. От ответа к обучению/i,
      );
      await demo.shot("04_chapter2_overlay", {
        caption: "Chapter 2: tutor handoff",
        narration: "From answer mode into structured learning.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_tour_resume=1&e2e_tour_chapter=1&e2e_tour_step=0");
      await expect(page.locator(".tutorial-callout")).toBeVisible({ timeout: 60_000 });
      await expect(page.locator(".tutorial-callout")).toContainText(
        /Глава 2\. От ответа к обучению/i,
      );
      await demo.shot("05_resume_after_reload", {
        caption: "Tour resumes after reload",
        narration: "Chapter progress survives a full page reload.",
        fullPage: true,
        skipReady: true,
        waitMs: 300,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
