import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Tutor restore session', () => {
  test('@nightly day 2 resume card appears and restores context', async ({ page }) => {
    test.setTimeout(360_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY for tutor response persistence.');
    }
    await completeFirstRunOnboarding(page);

    // 1. Создаем начальный стейт — переходим к тьютору напрямую
    await page.goto('/?e2e_view=tutor');
    
    await expect(page.getByPlaceholder('Спросите тьютора…')).toBeVisible({ timeout: 30_000 });
    
    // Отправляем первое сообщение, чтобы создать сессию и снимок в БД
    const chatInput = page.getByPlaceholder('Спросите тьютора…');
    await chatInput.fill('Привет тьютор');
    const tutorAskPromise = page.waitForResponse(
      (r) => r.request().method() === 'POST' && r.url().includes('/ask'),
      { timeout: 60_000 },
    ).catch(() => null);
    await chatInput.press('Enter');
    const tutorAsk = await tutorAskPromise;

    if (!tutorAsk?.ok()) {
      const body = await tutorAsk?.text().catch(() => '');
      const msg = `Tutor /ask failed before resume snapshot: ${tutorAsk?.status()} ${(body ?? '').slice(0, 200)}`;
      if (!STRICT_NIGHTLY) test.skip(true, msg);
      throw new Error(msg);
    }

    // Ждём не UI-селектор, а факт сохранения snapshot в API.
    const apiBase = e2eApiOrigin();
    let snapshotReady = false;
    const snapshotDeadline = Date.now() + 180_000;
    while (Date.now() < snapshotDeadline) {
      const health = await page.evaluate(async (base: string) => {
        const r = await fetch(`${base}/learner/state/health`).catch(() => null);
        return r?.ok ? (r.json() as Promise<Record<string, unknown>>) : null;
      }, apiBase);
      const snapshot = (health as Record<string, unknown> | null)?.tutor_learning_resume;
      if (snapshot) {
        snapshotReady = true;
        break;
      }
      await page.waitForTimeout(2_000);
    }
    if (!STRICT_NIGHTLY && !snapshotReady) {
      test.skip(true, 'Tutor snapshot не сохранился в allotted timeout.');
    }
    expect(snapshotReady, 'Tutor snapshot должен сохраниться после первого ответа.').toBeTruthy();

    // 2. Симулируем новый день: возвращаемся на главную
    await page.goto('/');
    
    // Проверяем наличие карточки `🎯 Продолжить чат с тьютором` или `📍 Следующий шаг` с кнопкой `Продолжить`
    // Кнопка продолжить имеет текст "▶️ Продолжить" или "Продолжить"
    const resumeBtn = page.getByRole('button', { name: /(▶️ Продолжить|Продолжить обучение)/i }).first();
    await expect(resumeBtn).toBeVisible({ timeout: 30_000 });

    // Кликаем и возвращаемся в чат
    await resumeBtn.click();
    
    // 3. Убеждаемся, что возврат из карточки работает:
    // в зависимости от конфигурации это может быть tutor/qa/progress.
    const restoreMarkers = [
      page.getByPlaceholder('Спросите тьютора…'),
      page.getByRole('button', { name: /Получить ответ/i }).first(),
      page.getByText(/Обучение — Прогресс обучения|Сводка Progress/i).first(),
    ];
    let restored = false;
    for (const marker of restoreMarkers) {
      if (await marker.isVisible({ timeout: 5_000 }).catch(() => false)) {
        restored = true;
        break;
      }
    }
    expect(restored).toBeTruthy();
    await expect(page.locator('[data-testid="stChatMessage"], .stChatMessage').filter({ hasText: /Привет тьютор/i }).first()).toBeVisible({
      timeout: 30_000,
    });
  });
});
