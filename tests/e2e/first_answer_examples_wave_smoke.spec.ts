import { test, expect, type Page } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "./fixtures/streamlit_ready";
import { completeFirstRunOnboarding } from "./fixtures/onboarding";
import { DEMO } from "./fixtures/demo_timeouts";

/**
 * audit group_11 / wave-first-answer-ux — US-3.3 hero: три кликабельных example questions
 * (см. SUGGESTED_QUESTIONS в app/ui/constants.py), без вызова /ask.
 */

const EXAMPLE_ONE = "Сравни hybrid retrieval и vector-only на практических кейсах";
const EXAMPLE_TWO = "Сделай обзор по теме AI-агентов в разработке";
const EXAMPLE_THREE = "Какие документы лучше всего покрывают prompt injection?";

async function openQuickAnswerWithExamples(page: Page): Promise<void> {
  let ready = false;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    await gotoAndWaitForStreamlitReady(page, "/?e2e_view=qa", DEMO.navigationReadyMs);
    await waitForStreamlitReady(page, DEMO.streamlitReadyMs);
    await expect(page.getByText("Быстрый старт", { exact: true })).toBeVisible({
      timeout: DEMO.visibleMs,
    });
    const byText = page.getByText(EXAMPLE_ONE, { exact: true }).first();
    ready = await byText
      .waitFor({ state: "visible", timeout: DEMO.visibleMs })
      .then(() => true)
      .catch(() => false);
    if (ready) {
      return;
    }
    await page.waitForTimeout(400);
  }
  throw new Error("first-answer examples smoke: hero example prompts not visible on Quick Answer");
}

async function locateQuestionField(page: Page) {
  const labeled = page.getByLabel("Вопрос");
  if (await labeled.isVisible({ timeout: 5_000 }).catch(() => false)) {
    return labeled;
  }
  return page.getByRole("textbox").first();
}

test.describe("@smoke wave-first-answer-ux (group_11)", () => {
  test("@smoke epoch-first-answer-examples: три примера на быстром ответе и клик подставляет текст в «Вопрос»", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await completeFirstRunOnboarding(page);
    await openQuickAnswerWithExamples(page);

    await expect(page.getByText(EXAMPLE_ONE, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(EXAMPLE_TWO, { exact: true }).first()).toBeVisible();
    await expect(page.getByText(EXAMPLE_THREE, { exact: true }).first()).toBeVisible();

    const exampleBtn = page.getByRole("button", { name: /Сравни hybrid retrieval/i }).first();
    await exampleBtn.scrollIntoViewIfNeeded();
    await exampleBtn.click();
    await waitForStreamlitReady(page, DEMO.streamlitReadyMs);

    const question = await locateQuestionField(page);
    await expect(question).toBeVisible({ timeout: DEMO.visibleMs });
    await expect(question).toHaveValue(EXAMPLE_ONE, { timeout: DEMO.visibleMs });
  });
});
