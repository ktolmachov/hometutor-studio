import type { Page } from '@playwright/test';

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/** Streamlit "selectbox" renders as combobox input, not native <select>. */
export async function navigateToSection(page: Page, label: string): Promise<void> {
  const switcher = page.locator('[data-testid="e2e-view-switcher"]').first();
  await switcher.waitFor({ state: 'attached', timeout: 5_000 }).catch(() => undefined);
  const combobox = page.getByRole('combobox').first();
  await combobox.waitFor({ state: 'visible', timeout: 60_000 });
  await combobox.click();

  const option = page.getByRole('option', {
    name: new RegExp(escapeRegExp(label), 'i'),
  }).first();

  if (await option.isVisible({ timeout: 5_000 }).catch(() => false)) {
    await option.click();
    return;
  }

  await combobox.fill(label);
  await combobox.press('Enter');
}
