import { test, expect, type Locator, type Page } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "./fixtures/streamlit_ready";
import { completeFirstRunOnboarding } from "./fixtures/onboarding";
import { DEMO } from "./fixtures/demo_timeouts";

const QA_QUESTION = "Что такое retrieval augmented generation?";

/**
 * audit group_10 / wave-production-health — один проход Quick Answer под оффлайн-стеком.
 * Заголовок содержит оба package id, чтобы `npx playwright test -g <id>` находил один и тот же тест.
 */

async function locateQuestionInput(page: Page) {
  const labeled = page.getByLabel("Вопрос");
  if (await labeled.isVisible({ timeout: 5_000 }).catch(() => false)) {
    return labeled;
  }
  return page.getByRole("textbox").first();
}

async function openQuickAnswerWithOfflineStub(page: Page): Promise<void> {
  await completeFirstRunOnboarding(page);
  let input!: Locator;
  let quickAnswerReady = false;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    await gotoAndWaitForStreamlitReady(page, "/?e2e_view=qa", DEMO.navigationReadyMs);
    input = await locateQuestionInput(page);
    quickAnswerReady = await input
      .waitFor({ state: "visible", timeout: DEMO.visibleMs })
      .then(() => true)
      .catch(() => false);
    if (quickAnswerReady) {
      break;
    }
    await page.waitForTimeout(400);
  }
  if (!quickAnswerReady) {
    throw new Error("production-health smoke: question input not visible on Quick Answer view");
  }
  await input.scrollIntoViewIfNeeded();
  await input.click();
  await input.fill("");
  await input.pressSequentially(QA_QUESTION, { delay: 25 });
  await waitForStreamlitReady(page, DEMO.streamlitReadyMs);
  const askPromise = page
    .waitForResponse(
      (r) => r.request().method() === "POST" && r.url().includes("/ask"),
      { timeout: 120_000 },
    )
    .catch(() => null);
  const submitBtn = page.getByRole("button", { name: /Получить ответ/i }).first();
  if (await submitBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
    await submitBtn.click();
  } else {
    await input.press("Enter");
  }
  const askResp = await askPromise;
  if (askResp && !askResp.ok()) {
    const body = await askResp.text().catch(() => "");
    throw new Error(`Q&A /ask failed: ${askResp.status()} ${body.slice(0, 240)}`);
  }

  const revealMs = 120_000;
  const revealDeadline = Date.now() + revealMs;
  let answerReady = false;
  while (Date.now() < revealDeadline) {
    const stubOk = await page
      .getByText(/E2E offline stub response|offline stub|Stub source/i)
      .first()
      .isVisible({ timeout: 2_000 })
      .catch(() => false);
    const labelOk = await page
      .getByText("Ответ", { exact: true })
      .first()
      .isVisible({ timeout: 500 })
      .catch(() => false);
    const sourcesOk = await page
      .getByText("Источники", { exact: true })
      .first()
      .isVisible({ timeout: 500 })
      .catch(() => false);
    if (stubOk || labelOk || sourcesOk) {
      answerReady = true;
      break;
    }
    await waitForStreamlitReady(page, 3_000);
  }
  expect(answerReady, "Quick Answer: offline stub or answer block must render").toBeTruthy();
  await waitForStreamlitReady(page, DEMO.streamlitReadyMs);
}

test.describe("@smoke wave-production-health (group_10)", () => {
  test("@smoke epoch-latency-slo-gate + epoch-llm-regression-baseline: offline quick answer shows first response and sources/trust", async ({
    page,
  }) => {
    test.setTimeout(360_000);
    await openQuickAnswerWithOfflineStub(page);

    await test.step("epoch-latency-slo-gate: first answer body", async () => {
      await expect(page.getByText("Ответ", { exact: true }).first()).toBeVisible({
        timeout: 60_000,
      });
      const stubLine = page.getByText(/E2E offline stub response|offline stub/i).first();
      const stubText = (await stubLine.textContent().catch(() => "")) ?? "";
      expect(stubText.length).toBeGreaterThan(12);
    });

    await test.step("epoch-llm-regression-baseline: retrieval trust / sources", async () => {
      const trustOrSources = page.getByText(/Stub source|Источники|Confidence/i).first();
      await expect(trustOrSources).toBeVisible({ timeout: 60_000 });
    });
  });
});
