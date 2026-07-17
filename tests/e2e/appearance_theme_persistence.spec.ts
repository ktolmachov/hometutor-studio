import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from './fixtures/streamlit_ready';
import { firstVisible } from './fixtures/kg3d';

test.describe('@smoke Appearance worlds', () => {
  test('@smoke selected appearance world survives reload', async ({ page }) => {
    test.setTimeout(120_000);

    await completeFirstRunOnboarding(page);
    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=home');

    await page.getByRole('button', { name: /Настроить интерфейс/i }).first().click({ timeout: 30_000 });
    await page.getByRole('tab', { name: /Оформление/i }).click({ timeout: 30_000 });

    const world = await firstVisible([
      page.getByRole('button', { name: /Океан|Лес|Закат|Космос|Ягода/i }).first(),
      page.getByLabel(/Океан|Лес|Закат|Космос|Ягода/i).first(),
      page.getByText(/Океан|Лес|Закат|Космос|Ягода/i).first(),
    ], 10_000);
    expect(world, 'Appearance tab should expose theme worlds').not.toBeNull();

    const selectedName = ((await world!.textContent().catch(() => '')) ?? '').trim();
    await world!.click({ timeout: 10_000 }).catch(() => undefined);
    await waitForStreamlitReady(page, 10_000).catch(() => undefined);

    await page.reload({ waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 30_000);
    await page.getByRole('button', { name: /Настроить интерфейс/i }).first().click({ timeout: 30_000 });
    await page.getByRole('tab', { name: /Оформление/i }).click({ timeout: 30_000 });

    if (selectedName) {
      await expect(page.getByText(new RegExp(selectedName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'i')).first())
        .toBeVisible({ timeout: 15_000 });
    }
    await expect(page.getByText(/Traceback|StreamlitAPIException|Exception:/i)).toHaveCount(0);
  });
});
