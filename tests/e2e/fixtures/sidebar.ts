import type { Page } from '@playwright/test';

/** Ensure Streamlit sidebar is expanded (layout-dependent). */
export async function ensureSidebarOpen(page: Page): Promise<void> {
  const collapsed = page.locator('[data-testid="stSidebarCollapsedControl"]');
  if ((await collapsed.count()) > 0) {
    await collapsed.first().click();
  }
  await page.locator('[data-testid="stSidebar"]').waitFor({ state: 'visible' });
}
