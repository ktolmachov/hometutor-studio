import { test, expect, type Page } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { waitForStreamlitReady } from './fixtures/streamlit_ready';

/**
 * wave-interactive-tour / epoch-tour-skeleton-ch1: learner-visible overlay, глава 1 «Первый ответ».
 * epoch-tour-persistence-ch2-5: прогресс тура поднимается из persistence после reload.
 *
 * Один тест специально: worker DB сохраняет tutorial progress между кейсами в одном worker.
 */
test.describe('@smoke Interactive tour (ch1 + resume)', () => {
  test.setTimeout(240_000);

  async function clickTutorialCta(page: Page, name: RegExp) {
    const btn = page.getByRole('button', { name }).first();
    await expect(btn).toBeVisible({ timeout: 60_000 });
    await btn.scrollIntoViewIfNeeded().catch(() => {});
    await btn.click();
    await waitForStreamlitReady(page, 90_000);
  }

  test('@smoke глава 1 + переход в гл.2 + resume после reload', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    await expect(page.locator('.tutorial-ribbon')).toContainText(/Тур: глава/i, { timeout: 60_000 });

    await clickTutorialCta(page, /Пройти интерактивный тур \(5 глав\)/i);

    await expect(page.locator('.tutorial-callout')).toBeVisible({ timeout: 60_000 });
    await expect(page.locator('.tutorial-callout')).toContainText(/Глава 1\. Первый ответ/i);
    await expect(page.locator('.tutorial-callout')).toContainText(/Добро пожаловать в интерактивный тур/i);

    await clickTutorialCta(page, /^Начать$/);
    await expect(page.locator('.tutorial-callout')).toContainText(/Попробуйте пример вопроса/i);

    await clickTutorialCta(page, /^Дальше$/);
    await expect(page.locator('.tutorial-callout')).toContainText(/Проверьте источники и доверие/i);

    await clickTutorialCta(page, /К главе 2/i);
    await expect(page.locator('.tutorial-callout')).toContainText(/Глава 2\. От ответа к обучению/i);
    await expect(page.locator('.tutorial-callout')).toContainText(/Переключение в Tutor/i);
    await expect(page.locator('.tutorial-ribbon')).toContainText(/Тур: глава 2 из 5/i);

    await page.reload({ waitUntil: 'domcontentloaded' });
    await completeFirstRunOnboarding(page);

    await expect(page.locator('.tutorial-ribbon')).toContainText(/Тур: глава 2 из 5/i, { timeout: 90_000 });

    const resume = page.getByRole('button', { name: /Продолжить тур/i }).first();
    const overlay = page.locator('.tutorial-callout');

    const hasResume = await resume.isVisible({ timeout: 15_000 }).catch(() => false);
    const hasOverlay = await overlay.isVisible({ timeout: 5_000 }).catch(() => false);

    if (!hasOverlay && hasResume) {
      await resume.click();
      await waitForStreamlitReady(page, 90_000);
    }

    await expect(page.locator('.tutorial-callout')).toBeVisible({ timeout: 60_000 });
    await expect(page.locator('.tutorial-callout')).toContainText(/Глава 2\. От ответа к обучению/i);
  });
});
