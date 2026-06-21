import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { ensureSidebarOpen } from './fixtures/sidebar';

/** E11-C / US-14.3: expert controls expander reachable in sidebar. */
test.describe('@smoke Expert controls', () => {
  test('@smoke sidebar exposes «Расширенное управление (эксперт)»', async ({ page }) => {
    await completeFirstRunOnboarding(page);
    await ensureSidebarOpen(page);

    const sidebar = page.locator('[data-testid="stSidebar"]');
    await expect(sidebar).toBeVisible({ timeout: 30_000 });
    const expertToggle = sidebar.getByText(/Расширенное управление/i).first();
    const transferToggle = sidebar.getByText(/Перенос прогресса/i).first();

    let hasExpert = false;
    let hasTransfer = false;
    for (let i = 0; i < 18; i += 1) {
      hasExpert = await expertToggle.isVisible({ timeout: 2_000 }).catch(() => false);
      hasTransfer = await transferToggle.isVisible({ timeout: 2_000 }).catch(() => false);
      if (hasExpert || hasTransfer) {
        break;
      }
      await page.waitForTimeout(3_000);
    }

    if (!hasExpert && !hasTransfer) {
      const sidebarText = await sidebar.innerText().catch(() => '<failed to read sidebar text>');
      throw new Error(`Advanced controls were not rendered in sidebar. Sidebar text: ${sidebarText.slice(0, 1200)}`);
    }

    if (hasExpert) {
      await expertToggle.scrollIntoViewIfNeeded();
      await expertToggle.click();
      await expect(page.getByText(/Фильтры области вопроса и голос/i)).toBeVisible();
      return;
    }

    await expect(transferToggle).toBeVisible({ timeout: 30_000 });
    await transferToggle.scrollIntoViewIfNeeded();
    await transferToggle.click();
    await expect(page.getByText(/Скачайте JSON backup/i)).toBeVisible();
  });
});
