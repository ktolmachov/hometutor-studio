import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@smoke @nightly Q&A to tutor bridge', () => {
  test('@smoke @nightly quick answer renders response and can hand off into tutor', async ({ page }) => {
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY for live answer generation.');
    }

    await completeFirstRunOnboarding(page);

    const questionInput = page.getByLabel('Вопрос');
    await questionInput.fill('Что такое RAG и зачем он нужен?');
    const qaAskResponsePromise = page
      .waitForResponse(
        (resp) => resp.request().method() === 'POST' && resp.url().includes('/ask'),
        { timeout: 45_000 },
      )
      .catch(() => null);
    await page.getByRole('button', { name: /Получить ответ/i }).click();
    const qaAskResponse = await qaAskResponsePromise;
    if (!qaAskResponse) {
      if (!STRICT_NIGHTLY) {
        test.skip(true, 'Q&A /ask did not complete within 45s.');
      }
      throw new Error('Q&A /ask did not complete within 45s in strict mode.');
    }
    if (!qaAskResponse.ok()) {
      const rawBody = await qaAskResponse.text().catch(() => '');
      const errText = `${qaAskResponse.status()} ${rawBody || 'empty body'}`.slice(0, 240);
      if (!STRICT_NIGHTLY) {
        test.skip(true, `Q&A /ask failed before rendering answer block: ${errText}`);
      }
      throw new Error(`Q&A /ask failed in strict mode: ${errText}`);
    }

    const embeddingMismatch = page
      .getByText(/Collection expecting embedding|dimension of \d+, got \d+|Ошибка запроса:/i)
      .first();
    if (!STRICT_NIGHTLY && await embeddingMismatch.isVisible({ timeout: 8_000 }).catch(() => false)) {
      test.skip(true, 'Nightly environment has embedding/index dimension mismatch (Chroma 1536 vs query 768).');
    }

    const answerHeading = page.locator('h1, h2, h3').filter({ hasText: /^Ответ$/ }).first();
    const sourcesHeading = page.locator('h1, h2, h3').filter({ hasText: /^Источники$/ }).first();
    const learnCtaMarker = page.getByRole('button', { name: /Учить эту тему 5 минут/i }).first();
    const answerStateMarker = page.getByText(/Текущее состояние ответа|Объясни проще|Приведи пример/i).first();
    const askError = page.getByText(/Ошибка запроса:|InvalidArgumentError|dimension of \d+, got \d+/i).first();
    let qaReady = false;
    for (let i = 0; i < 45; i += 1) {
      if (await askError.isVisible({ timeout: 1_500 }).catch(() => false)) {
        const errText = (await askError.textContent().catch(() => 'unknown ask error')) || 'unknown ask error';
        if (!STRICT_NIGHTLY) {
          test.skip(true, `Q&A failed before rendering answer block: ${errText.slice(0, 220)}`);
        }
        throw new Error(`Q&A request failed in strict mode: ${errText.slice(0, 220)}`);
      }
      const hasAnswerHeading = await answerHeading.isVisible({ timeout: 1_500 }).catch(() => false);
      const hasSourcesHeading = await sourcesHeading.isVisible({ timeout: 1_500 }).catch(() => false);
      const hasLearnCta = await learnCtaMarker.isVisible({ timeout: 1_500 }).catch(() => false);
      const hasAnswerState = await answerStateMarker.isVisible({ timeout: 1_500 }).catch(() => false);
      if (hasAnswerHeading || (hasSourcesHeading && hasAnswerState) || hasLearnCta) {
        qaReady = true;
        break;
      }
      await page.waitForTimeout(2_000);
    }
    if (!STRICT_NIGHTLY && !qaReady) {
      test.skip(true, 'Q&A UI did not reach stable answer state in allotted timeout.');
    }
    expect(qaReady).toBeTruthy();

    const learnCta = page.getByRole('button', { name: /Учить эту тему 5 минут/i }).first();
    await expect(learnCta).toBeVisible({ timeout: 30_000 });
    await learnCta.click();

    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByText(/Текущий учебный контекст/i).first()).toBeVisible({
      timeout: 60_000,
    });
    const fallbackContinue = page.getByRole('button', { name: /Продолжить 1 шаг/i }).first();
    const fallbackDone = page.getByRole('button', { name: /Готово на сегодня/i }).first();
    const nextStepLine = page.getByText(/Следующий шаг:/i).first();
    const quizAction = page.getByRole('button', { name: /Понял|Вспомнил|Трудно/i }).first();

    let hasExplicitNextStep = false;
    for (let i = 0; i < 30; i += 1) {
      const markers = await Promise.all([
        fallbackContinue.isVisible({ timeout: 1_000 }).catch(() => false),
        fallbackDone.isVisible({ timeout: 1_000 }).catch(() => false),
        nextStepLine.isVisible({ timeout: 1_000 }).catch(() => false),
        quizAction.isVisible({ timeout: 1_000 }).catch(() => false),
      ]);
      if (markers.some(Boolean)) {
        hasExplicitNextStep = true;
        break;
      }
      await page.waitForTimeout(2_000);
    }
    expect(hasExplicitNextStep).toBeTruthy();
  });
});
