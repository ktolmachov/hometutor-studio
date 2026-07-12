import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from '../fixtures/onboarding';
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from '../fixtures/streamlit_ready';
import { createDemoRecorder } from '../fixtures/demo_recorder';
import { DEMO } from '../fixtures/demo_timeouts';

/**
 * Demo scenario #21 — Smart Study Router: explainable next step.
 *
 * Запуск: npm run test:e2e:demo -- --grep "@demo Scenario 21"
 */
test.describe('@demo Scenario 21 — smart study router', () => {
  test('@demo captures explainable smart next-step card', async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, 'scenario_21');

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, '/');

      const card = page.locator('[data-testid="mission-control-ssr-banner"]').first();
      await expect(card).toBeVisible({ timeout: DEMO.visibleMs });
      await expect(card.getByRole('heading', { name: /С чего можно продолжить/i })).toBeVisible({
        timeout: DEMO.ctaMs,
      });
      await card.evaluate((element) => {
        element.scrollIntoView({ block: 'center', inline: 'nearest' });
      });
      await waitForStreamlitReady(page);

      await demo.shot('01_smart_study_router_card', {
        caption: 'Умный помощник: следующий шаг с объяснением',
        narration:
          'Система рекомендует один лучший следующий шаг и объясняет, почему именно сейчас.',
        fullPage: true,
        waitMs: 500,
        watermark: 'scenario_21 • smart-router',
      });

      await expect(page.getByRole('button', { name: /Короткая учебная сессия|Учить|Повторить|Открыть|Начать|Спросить/i }).first())
        .toBeVisible({ timeout: DEMO.ctaMs });
      await demo.shot('02_router_reason_and_alternatives', {
        caption: 'Почему сейчас + безопасные альтернативы',
        narration:
          'Главная CTA не прячет другие маршруты: быстрый ответ, тьютор, quiz и прогресс остаются рядом.',
        fullPage: true,
        waitMs: 300,
        watermark: 'scenario_21 • alternatives',
      });

      const trace = page.getByText(/Как выбрана подсказка|Почему это\?/i).first();
      if (await trace.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await trace.click();
      }
      await page.waitForTimeout(300);
      await waitForStreamlitReady(page);
      await demo.shot('03_router_trace_open', {
        caption: 'Краткий след решения роутера',
        narration:
          'Пользователь может раскрыть, какие локальные сигналы стояли за рекомендацией.',
        fullPage: true,
        waitMs: 300,
        watermark: 'scenario_21 • trace',
      });

      await demo.finalize('passed');
    } catch (err) {
      await demo.finalize('failed');
      throw err;
    }
  });
});
