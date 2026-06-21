import type { Locator, Page } from '@playwright/test';
import { expect } from '@playwright/test';
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from './streamlit_ready';
import { completeFirstRunOnboarding } from './onboarding';
import { DEMO } from './demo_timeouts';

/** Тот же вопрос, что в demo scenario_01 и AQE smoke — совместим с E2E offline stub в `POST /ask`. */
export const QA_OFFLINE_STUB_QUESTION = 'Что такое retrieval augmented generation?';

async function locateQuestionInput(page: Page): Promise<Locator> {
  const labeled = page.getByLabel('Вопрос');
  if (await labeled.isVisible({ timeout: 5_000 }).catch(() => false)) {
    return labeled;
  }
  return page.getByRole('textbox').first();
}

/**
 * Onboarding → Quick Answer → POST /ask под HOME_RAG_E2E_OFFLINE (стек Playwright).
 * Ждёт появление offline stub или блока ответа.
 */
export async function openQuickAnswerWithOfflineStub(page: Page): Promise<void> {
  await completeFirstRunOnboarding(page);
  let input!: Locator;
  let quickAnswerReady = false;
  for (let attempt = 1; attempt <= 3; attempt += 1) {
    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=qa', DEMO.navigationReadyMs);
    input = await locateQuestionInput(page);
    quickAnswerReady = await input
      .waitFor({ state: 'visible', timeout: DEMO.visibleMs })
      .then(() => true)
      .catch(() => false);
    if (quickAnswerReady) {
      break;
    }
    await page.waitForTimeout(400);
  }
  if (!quickAnswerReady) {
    throw new Error('Quick Answer offline stub flow: question input not visible');
  }
  await input.scrollIntoViewIfNeeded();
  await input.click();
  await input.fill('');
  await input.pressSequentially(QA_OFFLINE_STUB_QUESTION, { delay: 25 });
  await waitForStreamlitReady(page, DEMO.streamlitReadyMs);
  const askPromise = page
    .waitForResponse((r) => r.request().method() === 'POST' && r.url().includes('/ask'), {
      timeout: 120_000,
    })
    .catch(() => null);
  const submitBtn = page.getByRole('button', { name: /Получить ответ/i }).first();
  const btnVisible = await submitBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false);
  if (btnVisible) {
    await expect(submitBtn).toBeEnabled({ timeout: DEMO.ctaMs });
    await submitBtn.click();
  } else {
    await input.press('Enter');
  }
  const askResp = await askPromise;
  if (askResp && !askResp.ok()) {
    const body = await askResp.text().catch(() => '');
    throw new Error(`Q&A /ask failed: ${askResp.status()} ${body.slice(0, 240)}`);
  }

  // Не использовать Promise.race по waitFor(...).catch(false): первым «выигрывает»
  // промис с таймаутом=false, хотя через мгновень stub мог бы появиться в другой ветке.
  await expect
    .poll(
      async () => {
        const text = await page.locator('body').innerText();
        return (
          /E2E offline stub response|offline stub/i.test(text) ||
          (/RAG combines/i.test(text) && /источников/i.test(text))
        );
      },
      {
        timeout: 120_000,
        intervals: [400, 1_000, 2_000],
      },
    )
    .toBeTruthy();
  await waitForStreamlitReady(page, DEMO.streamlitReadyMs);
}
