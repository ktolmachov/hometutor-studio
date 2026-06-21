import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@smoke @nightly unified context block', () => {
  test('@smoke @nightly shows context block on Tutor, Home, and Progress', async ({ page }) => {
    test.setTimeout(240_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY for live answer generation.');
    }

    await completeFirstRunOnboarding(page);

    // 1) Build continuity payload via Quick Answer -> Learn CTA.
    const questionInput = page.getByLabel('Вопрос');
    await questionInput.fill('Кратко объясни, зачем нужен RAG');
    const qaAskResponsePromise = page
      .waitForResponse(
        (resp) => resp.request().method() === 'POST' && resp.url().includes('/ask'),
        { timeout: 45_000 },
      )
      .catch(() => null);
    await page.getByRole('button', { name: /Получить ответ/i }).click();
    const qaAskResponse = await qaAskResponsePromise;
    if (!qaAskResponse || !qaAskResponse.ok()) {
      const err = qaAskResponse ? `${qaAskResponse.status()}` : 'no-response';
      if (!STRICT_NIGHTLY) {
        test.skip(true, `Q&A /ask unavailable in smoke env: ${err}`);
      }
      throw new Error(`Q&A /ask failed in strict mode: ${err}`);
    }

    const learnCta = page.getByRole('button', { name: /Учить эту тему 5 минут/i }).first();
    await expect(learnCta).toBeVisible({ timeout: 45_000 });
    await learnCta.click();

    // 2) Tutor checks.
    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Текущий учебный контекст/i).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Почему сейчас:/i).first()).toBeVisible({ timeout: 60_000 });
    await expect(page.getByText(/Следующий шаг:/i).first()).toBeVisible({ timeout: 60_000 });
    const tutorNextStepLine = page.getByText(/Следующий шаг:/i).first();
    const tutorFallbackButton = page.getByRole('button', { name: /Продолжить 1 шаг|Готово на сегодня/i }).first();
    let tutorHasNextStep = false;
    for (let i = 0; i < 20; i += 1) {
      const hasLine = await tutorNextStepLine.isVisible({ timeout: 1_000 }).catch(() => false);
      const hasFallback = await tutorFallbackButton.isVisible({ timeout: 1_000 }).catch(() => false);
      if (hasLine || hasFallback) {
        tutorHasNextStep = true;
        break;
      }
      await page.waitForTimeout(1_500);
    }
    expect(tutorHasNextStep).toBeTruthy();

    // 3) Home checks.
    const mainLink = page.getByRole('link', { name: /^main$/i }).first();
    if (await mainLink.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await mainLink.click();
    } else {
      await page.goto('/');
    }
    await expect(page.getByText(/Текущий учебный контекст/i).first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Почему сейчас:/i).first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Следующий шаг:/i).first()).toBeVisible({ timeout: 45_000 });

    // 4) Progress checks.
    await page.goto('/?e2e_view=progress');
    await expect(page.getByText(/Текущий учебный контекст/i).first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Почему сейчас:/i).first()).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/Следующий шаг:/i).first()).toBeVisible({ timeout: 45_000 });
  });
});
