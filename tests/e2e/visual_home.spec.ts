import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

test.describe('@smoke Home visual snapshot', () => {
  test('@smoke home main viewport matches screenshot', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    const mainLink = page.getByRole('link', { name: /^main$/i });
    if (await mainLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await mainLink.click();
    }

    const hero = page.locator('.hero').first();
    await expect(hero).toBeVisible({ timeout: 30_000 });
    await expect(page.getByRole('heading', { name: /Личная база знаний/i }).first()).toBeVisible({
      timeout: 60_000,
    });
    await page.waitForTimeout(500);

    await expect(hero).toHaveScreenshot('home-hero.png', {
      animations: 'disabled',
      // Streamlit/WebSocket UI: стабильный контент, но антиалиасинг/спиннеры дают небольшой дрейф между прогонами.
      maxDiffPixels: 22_000,
      threshold: 0.25,
    });
  });
});
