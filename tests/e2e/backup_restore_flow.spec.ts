import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { ensureSidebarOpen } from './fixtures/sidebar';

test.describe('@smoke Backup and restore flow', () => {
  test('@smoke restore requires preview and explicit confirmation', async ({ page }) => {
    await completeFirstRunOnboarding(page);
    await page.goto('/?e2e_restore_preview=1', { waitUntil: 'domcontentloaded' });
    await ensureSidebarOpen(page);

    const sidebar = page.locator('[data-testid="stSidebar"]');
    await expect(sidebar).toBeVisible({ timeout: 30_000 });

    const syncToggle = sidebar.getByText(/Синхронизация|backup|Перенос прогресса|Скачайте JSON backup/i).first();
    let hasSync = false;
    for (let i = 0; i < 18; i += 1) {
      hasSync = await syncToggle.isVisible({ timeout: 2_000 }).catch(() => false);
      if (hasSync) {
        break;
      }
      await page.waitForTimeout(3_000);
    }
    if (!hasSync) {
      const sidebarText = await sidebar.innerText().catch(() => '<failed to read sidebar text>');
      throw new Error(`Sync/backup block was not rendered in sidebar. Sidebar text: ${sidebarText.slice(0, 1200)}`);
    }
    await syncToggle.scrollIntoViewIfNeeded();
    await syncToggle.click();

    await expect(sidebar.getByText(/Предпросмотр готов|Всего строк/i).first()).toBeVisible({
      timeout: 30_000,
    });

    const importButton = sidebar.getByRole('button', { name: /Импортировать снимок/i }).first();
    await expect(importButton).toBeDisabled();

    await sidebar.locator('[data-testid="e2e-restore-confirm"]').first().waitFor({ state: 'attached', timeout: 10_000 });

    const confirmCb = sidebar.getByRole('checkbox', {
      name: /Я понимаю, что импорт перезапишет локальный прогресс на этой машине/i,
    });
    // Playwright check() даже с force иногда ругается на viewport у вложенного скролла Streamlit.
    await confirmCb.evaluate((el: HTMLInputElement) => {
      if (!el.checked) el.click();
    });
    await expect(sidebar.getByRole('button', { name: /Импортировать снимок/i }).first()).toBeEnabled();
  });
});
