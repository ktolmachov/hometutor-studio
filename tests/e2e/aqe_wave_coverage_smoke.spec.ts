import { test, expect } from "@playwright/test";
import { DEMO } from "./fixtures/demo_timeouts";
import { openQuickAnswerWithOfflineStub } from "./fixtures/qa_offline_quick_answer";

/**
 * audit group_08 / wave-answer-quality-eval — learner-visible smoke без live LLM
 * (HOME_RAG_E2E_OFFLINE через scripts/e2e_run_stack.mjs).
 */

test.describe("@smoke wave-answer-quality-eval (group_08)", () => {
  test.describe.configure({ timeout: 300_000 });
  test("@smoke epoch-aqe-corpus-choice: quick answer shows grounded stub payload in UI (offline)", async ({
    page,
  }) => {
    test.setTimeout(300_000);
    await openQuickAnswerWithOfflineStub(page);
    await expect(page.getByText(/E2E offline stub response|offline stub/i).first()).toBeVisible({
      timeout: DEMO.visibleMs,
    });
    await expect
      .poll(async () => (await page.locator("body").innerText()).includes("RAG combines"), {
        timeout: DEMO.visibleMs,
      })
      .toBeTruthy();
    await expect
      .poll(async () => /источников/i.test(await page.locator("body").innerText()), {
        timeout: DEMO.visibleMs,
      })
      .toBeTruthy();
  });

  test("@smoke epoch-answer-quality-baseline: first-answer block visible with grounded stub (offline)", async ({
    page,
  }) => {
    test.setTimeout(300_000);
    await openQuickAnswerWithOfflineStub(page);
    await expect(page.getByText("Ответ", { exact: true }).first()).toBeVisible({
      timeout: DEMO.visibleMs,
    });
    const stubLine = page.getByText(/E2E offline stub response|offline stub/i).first();
    const stubText = (await stubLine.textContent().catch(() => "")) ?? "";
    expect(stubText.length).toBeGreaterThan(12);
  });
});
