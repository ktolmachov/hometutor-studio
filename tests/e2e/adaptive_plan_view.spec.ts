import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

test.describe('@smoke Adaptive Plan Rendering', () => {
  test('@smoke can open tutor chat and view the adaptive daily plan expander', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    // Переходим в Чат с тьютором
    await page.goto('/?e2e_view=tutor');

    await expect(page.getByPlaceholder('Спросите тьютора…')).toBeVisible({ timeout: 60_000 });

    // Ищем новый экспандер
    const planExpander = page.getByText(/Адаптивный план и прогноз/i).first();
    await expect(planExpander).toBeVisible({ timeout: 30_000 });
    
    // Кликаем, чтобы развернуть
    await planExpander.click();

    // Проверяем, что KPI панель (XP Forecast) отрисовалась
    await expect(page.getByText(/Цель XP сегодня/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/Всего XP/i).first()).toBeVisible({ timeout: 10_000 });

    // Проверяем элементы управления планом
    await expect(page.getByRole('button', { name: /Пересчитать план/i }).first()).toBeVisible({ timeout: 10_000 });

    // В зависимости от состояния стейта либо будет "Нет блоков в плане.", либо карточки плана.
    // При старте (без квизов) скорее всего план будет пустым или только с Motivation блоком.
    const planSectionTitle = page.getByText(/Adaptive Daily Plan/i).first();
    await expect(planSectionTitle).toBeVisible({ timeout: 10_000 });
  });
});
