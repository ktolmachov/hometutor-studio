/**
 * @smoke CJM §2 First Answer — доверие к ответу и handoff в тьютор (offline stub).
 *
 * Привязка к пакету epoch-answer-trust-to-learning-path: QA с confidence/источниками,
 * подписи continuity bridge, CTA «Учить эту тему» — без live LLM.
 */
import { test, expect } from '@playwright/test';
import { waitForStreamlitReady } from './fixtures/streamlit_ready';
import { DEMO } from './fixtures/demo_timeouts';
import { openQuickAnswerWithOfflineStub } from './fixtures/qa_offline_quick_answer';

test.describe('@smoke First Answer trust → learning path (QA tab)', () => {
  // onboarding + QA + poll до stub (до 120s во фикстуре) — 180s на весь кейс маловато на медленном CI
  test.describe.configure({ timeout: 300_000 });
  test('@smoke epoch-answer-trust: confidence line, sources column, bridge captions (offline)', async ({
    page,
  }) => {
    test.setTimeout(300_000);
    await openQuickAnswerWithOfflineStub(page);

    await expect(page.getByText(/E2E offline stub response|offline stub/i).first()).toBeVisible({
      timeout: DEMO.visibleMs,
    });

    await expect
      .poll(async () => /источников/i.test(await page.locator("body").innerText()), {
        timeout: DEMO.visibleMs,
      })
      .toBeTruthy();
    await expect
      .poll(async () => /avg score/i.test(await page.locator("body").innerText()), {
        timeout: DEMO.visibleMs,
      })
      .toBeTruthy();
    await expect
      .poll(async () => (await page.locator("body").innerText()).includes("RAG combines"), {
        timeout: DEMO.visibleMs,
      })
      .toBeTruthy();

    await expect(
      page.getByText(/тот же черновик/i).first(),
    ).toBeVisible({ timeout: DEMO.visibleMs });
    await expect(
      page.getByText(/мини-проверка/i).first(),
    ).toBeVisible({ timeout: DEMO.visibleMs });
  });

  test('@smoke epoch-answer-trust: «Учить эту тему» ведёт в тьютор с контекстом Q&A (offline)', async ({
    page,
  }) => {
    test.setTimeout(300_000);
    await openQuickAnswerWithOfflineStub(page);

    const learnCta = page.getByRole('button', { name: /Учить эту тему/i }).first();
    await learnCta.waitFor({ state: 'visible', timeout: DEMO.ctaMs });
    await learnCta.scrollIntoViewIfNeeded();
    await learnCta.click();
    await waitForStreamlitReady(page, DEMO.streamlitReadyMs);

    await expect(
      page.getByText(/Последний вопрос \(Q&A\)|Начать диалог/i).first(),
    ).toBeVisible({ timeout: DEMO.visibleMs });
  });
});
