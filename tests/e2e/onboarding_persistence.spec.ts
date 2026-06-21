import { test, expect } from '@playwright/test';

/**
 * P0 skeleton: real first-run onboarding is not reachable in the default
 * e2e harness because scripts/e2e_run_stack.mjs pre-seeds onboarding_v1_done=1.
 * Keep the scenario visible until a dedicated "fresh profile" harness exists.
 */
test.describe('@smoke Onboarding persistence', () => {
  test.fixme(
    'first-run onboarding completes once and stays hidden after reload',
    'Default Playwright stack pre-seeds onboarding_v1_done in SQLite.',
  );

  test('@smoke post-onboarding state remains stable after reload', async ({ page }) => {
    await page.goto('/');
    await page.locator('[data-testid="stSidebar"]').waitFor({
      state: 'visible',
      timeout: 90_000,
    });

    await expect(page.getByRole('button', { name: 'Начать обучение' })).toHaveCount(0);

    const tutorHeading = page.getByText(/Чат с тьютором/i).first();
    const progressButton = page.getByRole('button', { name: /^Мой прогресс$/i }).first();
    const resumeButton = page.getByRole('button', { name: /Продолжить обучение/i }).first();

    const beforeReload =
      (await tutorHeading.isVisible({ timeout: 3_000 }).catch(() => false)) ||
      (await progressButton.isVisible({ timeout: 3_000 }).catch(() => false)) ||
      (await resumeButton.isVisible({ timeout: 3_000 }).catch(() => false));
    expect(beforeReload).toBeTruthy();

    await page.reload();
    await page.locator('[data-testid="stSidebar"]').waitFor({
      state: 'visible',
      timeout: 90_000,
    });

    await expect(page.getByRole('button', { name: 'Начать обучение' })).toHaveCount(0);
  });
});
