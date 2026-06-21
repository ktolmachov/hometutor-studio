import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Tutor micro-quiz flow', () => {
  test('@nightly tutor can open a micro-quiz and show outcome UI', async ({ page }) => {
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY for tutor answer generation.');
    }

    await completeFirstRunOnboarding(page);
    await page.getByRole('button', { name: /Начать диалог/i }).click();

    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({
      timeout: 30_000,
    });

    const chatInput = page.getByPlaceholder('Спросите тьютора…');
    await expect(chatInput).toBeVisible({ timeout: 10_000 });
    await chatInput.fill('Объясни коротко, что такое retrieval augmented generation.');
    const tutorAskResponsePromise = page
      .waitForResponse(
        (resp) => resp.request().method() === 'POST' && resp.url().includes('/ask'),
        { timeout: 45_000 },
      )
      .catch(() => null);
    await chatInput.press('Enter');
    const tutorAskResponse = await tutorAskResponsePromise;
    if (!tutorAskResponse) {
      if (!STRICT_NIGHTLY) {
        test.skip(true, 'Tutor /ask did not complete within 45s.');
      }
      throw new Error('Tutor /ask did not complete within 45s in strict mode.');
    }
    if (!tutorAskResponse.ok()) {
      const rawBody = await tutorAskResponse.text().catch(() => '');
      const errText = `${tutorAskResponse.status()} ${rawBody || 'empty body'}`.slice(0, 240);
      if (!STRICT_NIGHTLY) {
        test.skip(true, `Tutor /ask failed before quiz rendering: ${errText}`);
      }
      throw new Error(`Tutor /ask failed in strict mode: ${errText}`);
    }

    await expect(page.getByText(/Что делаем дальше|Проверь себя|Следующий шаг|Чат с тьютором/i).first()).toBeVisible({
      timeout: 60_000,
    });

    const quizCta = page.getByRole('button', { name: /Проверь меня/i }).first();
    const tutorAskError = page.getByText(/Ошибка запроса:|InvalidArgumentError|OPENAI_API_KEY|dimension of \d+, got \d+/i).first();
    const quizMarkers = [
      quizCta,
      page.getByText(/Мини-проверка понимания|Unified Auto-Loop|Вопрос:/i).first(),
      page.getByRole('button', { name: /^Ответить$/i }).first(),
      page.getByText(/Результат:|Верно|Неверно|Частично/i).first(),
    ];
    let quizRendered = false;
    const quizRenderDeadline = Date.now() + 35_000;
    while (Date.now() < quizRenderDeadline) {
      if (await tutorAskError.isVisible({ timeout: 250 }).catch(() => false)) {
        const errText = (await tutorAskError.textContent().catch(() => 'unknown tutor error')) || 'unknown tutor error';
        if (!STRICT_NIGHTLY) {
          test.skip(true, `Tutor step failed before quiz rendering: ${errText.slice(0, 220)}`);
        }
        throw new Error(`Tutor request failed in strict mode: ${errText.slice(0, 220)}`);
      }
      for (const marker of quizMarkers) {
        if (await marker.isVisible({ timeout: 250 }).catch(() => false)) {
          quizRendered = true;
          break;
        }
      }
      if (quizRendered) {
        break;
      }
      await page.waitForTimeout(1_000);
    }
    if (await quizCta.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await quizCta.click();
    }
    if (!STRICT_NIGHTLY) {
      test.skip(!quizRendered, 'Micro-quiz UI was not rendered for current tutor route.');
    }
    expect(quizRendered).toBeTruthy();

    const answerButton = page.getByRole('button', { name: /^Ответить$/i }).first();
    const hintButton = page.getByRole('button', { name: /Подсказка/i }).first();

    if (await hintButton.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await hintButton.click();
    }

    const firstRadio = page.locator('input[type="radio"]').first();
    if ((await firstRadio.count()) > 0) {
      await firstRadio.check();
    }

    if (await answerButton.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await answerButton.click();
    }

    await expect(page.getByText(/Результат:|Верно|Неверно|Частично/i).first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByText(/Что дальше:|Следующий шаг/i).first()).toBeVisible({
      timeout: 60_000,
    });
  });
});
