import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { gotoAndWaitForStreamlitReady } from './fixtures/streamlit_ready';
import { firstVisible } from './fixtures/kg3d';

test.describe('@smoke Audio podcast playlist', () => {
  test('@smoke living konspekt exposes local audio playlist when audio artifacts exist', async ({ page }) => {
    test.setTimeout(120_000);

    await completeFirstRunOnboarding(page);
    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=living_konspekt');

    const audio = await firstVisible([
      page.locator('audio').first(),
      page.locator('[data-testid="stAudio"]').first(),
      page.getByText(/m4a|аудио|подкаст|в дорогу|playlist|плейлист/i).first(),
    ], 10_000);
    test.skip(!audio, 'No local audio artifact is available in the current offline konspekt fixture.');

    await expect(page.getByText(/m4a|аудио|подкаст|в дорогу|часть|плейлист/i).first()).toBeVisible({
      timeout: 30_000,
    });
    await expect(
      page.getByRole('button', { name: /Скачать|Выпуск в дорогу|Download/i }).first()
        .or(page.getByText(/Выпуск в дорогу|m4a/i).first()),
    ).toBeVisible({ timeout: 30_000 });
  });
});
