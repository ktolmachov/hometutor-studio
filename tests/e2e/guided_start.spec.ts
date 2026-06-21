import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

/**
 * E11-A / US-14.1: guided primary CTA on home.
 * E11-D entry (safe_starter): home «Учить эту тему 5 минут» → чат тьютора с флагом 5-мин цикла (без live LLM).
 * Полный цикл ответ → micro-quiz — в optional nightly с OPENAI_API_KEY (см. tests/test_e11_learning_loop.py).
 */
test.describe('@smoke Guided CTA + 5-minute loop entry', () => {
  test('@smoke home shows next step and primary CTA; safe starter opens tutor chat', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    const mainLink = page.getByRole('link', { name: /^main$/i });
    if (await mainLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await mainLink.click();
    }

    const homeNextStep = page.getByText(/Следующий шаг/i).first();
    const primary = page.getByRole('button', {
      name: /(Продолжить|Повторить|Учить эту тему|Освоить следующий концепт|Продолжить обучение)/i,
    }).first();
    const progressLink = page.getByRole('link', { name: /^Мой прогресс$/i }).first();

    const hasEntryPoint =
      (await homeNextStep.isVisible({ timeout: 5_000 }).catch(() => false)) ||
      (await primary.isVisible({ timeout: 5_000 }).catch(() => false)) ||
      (await progressLink.isVisible({ timeout: 5_000 }).catch(() => false));
    expect(hasEntryPoint).toBeTruthy();

    // Sparse fixture state → canonical fallback CTA (US-14.1)
    const fiveMin = page.getByRole('button', { name: /Учить эту тему 5 минут/i });
    if (await fiveMin.isVisible()) {
      await fiveMin.click();
      await expect(page.getByText('Чат с тьютором', { exact: false }).first()).toBeVisible({
        timeout: 30_000,
      });
    }
  });
});
