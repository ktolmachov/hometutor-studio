import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

/** E10.4 / Progress tab: Mastery dashboard shell detailed visible (US-12.6 browser smoke). */
test.describe('@smoke Progress tab', () => {
  test('@smoke can open «Прогресс обучения» and see dashboard sections', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    // Navigate using the new 2x3 mode selector or directly via link
    await page.goto('/?e2e_view=progress');

    // В некоторых окружениях элементы вкладки прогресса появляются не сразу:
    // принимаем любой из стабильных маркеров этой вкладки.
    const progressMarkers = [
      page.getByText(/Обучение — Прогресс обучения/i).first(),
      page.getByText(/Сводка Progress|Сводка прогресса/i).first(),
      page.getByText(/Mastery \(вектор, среднее\)|Mastery radar/i).first(),
      page.getByText(/Геймификация|Ежедневный стрик/i).first(),
    ];
    let foundProgressMarker = false;
    for (let i = 0; i < 20; i += 1) {
      for (const marker of progressMarkers) {
        if (await marker.isVisible({ timeout: 1_500 }).catch(() => false)) {
          foundProgressMarker = true;
          break;
        }
      }
      if (foundProgressMarker) {
        break;
      }
      await page.waitForTimeout(2_000);
    }
    expect(foundProgressMarker).toBeTruthy();

    await expect(page.getByText(/Обучение — Прогресс обучения|Сводка Progress|Mastery/i).first()).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText(/Следующий шаг/i).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(/Почему сейчас:/i).first()).toBeVisible({ timeout: 30_000 });
    
    // Проверяем, что виден хотя бы один блок с ключевыми метриками.
    const metricMarkers = [
      page.getByText(/Покрытие графа|Mastery/i).first(),
      page.getByText(/Повторения|quiz/i).first(),
      page.getByText(/Ежедневный стрик|UI-квизы/i).first(),
      page.getByText(/Геймификация|Слабые концепты/i).first(),
    ];
    let hasMetricMarker = false;
    for (const marker of metricMarkers) {
      if (await marker.isVisible({ timeout: 4_000 }).catch(() => false)) {
        hasMetricMarker = true;
        break;
      }
    }
    expect(hasMetricMarker).toBeTruthy();

    // Check expander section "Персонализация и цели недели"
    const settingsExpander = page.locator('.streamlit-expanderHeader').filter({ hasText: /Персонализация и цели недели/i }).first();
    if (await settingsExpander.isVisible()) {
      await settingsExpander.click();
      await expect(page.getByText(/Как ты лучше всего учишься\?/i).first()).toBeVisible({ timeout: 5_000 });
    }
  });
});
