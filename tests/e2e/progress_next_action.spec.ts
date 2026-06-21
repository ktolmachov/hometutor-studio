/**
 * @smoke CJM §6 — переход review→progress: Progress tab предлагает следующий шаг
 *
 * Проверяет: Progress tab не просто показывает метрики, но и содержит
 * actionable CTA — "Следующий шаг", кнопку плана или рекомендацию.
 *
 * Работает без LLM (smoke).
 */
import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

test.describe('@smoke Progress tab next action CTA', () => {
  test('@smoke progress tab contains a next-step recommendation or CTA', async ({ page }) => {
    test.setTimeout(90_000);

    await completeFirstRunOnboarding(page);
    await page.goto('/?e2e_view=progress', { waitUntil: 'domcontentloaded' });

    // Ждём загрузки Progress tab
    const progressMarkers = [
      page.getByText(/Прогресс обучения|Сводка Progress|Mastery/i).first(),
      page.getByText(/Геймификация|Ежедневный стрик/i).first(),
    ];
    let progressLoaded = false;
    for (let i = 0; i < 20; i++) {
      for (const m of progressMarkers) {
        if (await m.isVisible({ timeout: 1_500 }).catch(() => false)) {
          progressLoaded = true; break;
        }
      }
      if (progressLoaded) break;
      await page.waitForTimeout(2_000);
    }
    expect(progressLoaded, 'Progress tab должен загрузиться').toBeTruthy();

    // ── Метрики присутствуют ──────────────────────────────────────────────────
    const metricMarkers = [
      page.getByText(/Mastery|Покрытие графа/i).first(),
      page.getByText(/Повторения|quiz|стрик/i).first(),
    ];
    let hasMetrics = false;
    for (const m of metricMarkers) {
      if (await m.isVisible({ timeout: 5_000 }).catch(() => false)) {
        hasMetrics = true; break;
      }
    }
    expect(hasMetrics, 'Progress tab должен показывать метрики обучения').toBeTruthy();

    // ── Ключевой инвариант: есть actionable следующий шаг ────────────────────
    // Принимаем любой из вариантов CTA / рекомендации / adaptive plan entry
    const nextActionMarkers = [
      page.getByText(/Следующий шаг/i).first(),
      page.getByRole('button', { name: /Начать тест|Учить|Повторить|Продолжить/i }).first(),
      page.getByText(/Рекоменду/i).first(),
      page.getByText(/Adaptive Daily Plan|Адаптивный план/i).first(),
      page.getByText(/Слабые концепты|gap/i).first(),
      page.locator('[data-testid="stButton"]').filter({ hasText: /шаг|план|учить|повтор/i }).first(),
    ];

    let hasNextAction = false;
    for (const m of nextActionMarkers) {
      if (await m.isVisible({ timeout: 5_000 }).catch(() => false)) {
        hasNextAction = true; break;
      }
    }
    expect(
      hasNextAction,
      'Progress tab должен содержать следующий шаг / CTA, а не только статичные метрики (CJM §6: review→progress)',
    ).toBeTruthy();
  });

  test('@smoke dashboard/mastery API returns all required progress fields', async ({ request }) => {
    test.setTimeout(30_000);

    const apiBase = e2eApiOrigin();
    const res = await request.get(`${apiBase}/dashboard/mastery`, { timeout: 30_000 });
    expect(res.ok(), 'GET /dashboard/mastery должен отвечать 200').toBeTruthy();
    const data = (await res.json()) as Record<string, unknown>;

    // Проверяем структуру: все поля для Progress tab должны присутствовать
    const requiredFields = [
      'mastery_vector',
      'gamification',
      'weekly_goals',
      'quiz_mastery_rows',
    ];
    for (const field of requiredFields) {
      expect(data, `Поле ${field} должно присутствовать в /dashboard/mastery`).toHaveProperty(field);
    }

    // gamification (get_snapshot): стрики и XP для Progress tab
    const gamification = (data as Record<string, unknown> & { gamification?: Record<string, unknown> })?.gamification;
    expect(gamification).toHaveProperty('daily_streak');
    expect(gamification).toHaveProperty('total_xp');
  });
});
