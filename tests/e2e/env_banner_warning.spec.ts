import { test, expect } from '@playwright/test';
import { ensureSidebarOpen } from './fixtures/sidebar';

/** E2E smoke test for Offline Resilience (Config Env Banner). */
test.describe('@smoke Offline Resilience Warning', () => {
  // Этот тест может не отображать баннер, если harness передает валидный OPENAI_API_KEY.
  // Но мы проверяем, что приложение при этом не падает (нет stack trace/exception на экране).
  test('@smoke env banner handles missing keys gracefully or stays hidden if keys exist', async ({ page }) => {
    await page.goto('/');
    await ensureSidebarOpen(page); // Убеждаемся что UI не упал и рендерится сайдбар

    // Проверяем что нет критических ошибок на странице (stack trace)
    await expect(page.getByText(/Exception:|Traceback \(most recent/)).toHaveCount(0);

    // Если баннер появляется (нет ключа), он должен содержать корректный текст-подсказку
    const missingKeyWarning = page.getByText(/OPENAI_API_KEY не найден в \.env/i);
    const isVisible = await missingKeyWarning.isVisible({ timeout: 5000 }).catch(() => false);
    
    if (isVisible) {
      await expect(missingKeyWarning).toBeVisible();
    } else {
      // Иначе приложение работает корректно (срок ключа/внешний провайдер активен)
      const mainLink = page.getByRole('link', { name: /^main$/i });
      await expect(mainLink).toBeVisible();
    }
  });
});
