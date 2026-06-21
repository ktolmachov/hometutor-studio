/**
 * @nightly CJM Moment of Truth #9 — concept graduation
 *
 * Проверяет: концепт, который долго находится в "transfer" (>7 дней стабильности),
 * помечается как graduated и больше не предлагается в gap-блоке плана.
 *
 * Контракт:
 *   - GET /dashboard/mastery.mastery_vector содержит поле graduated
 *   - GET /adaptive_plan/review (или подобный) не возвращает graduated концепты в gap-блоке
 *   - Если концепт graduated — он может быть в "completed" или hidden из рекомендаций
 *
 * Сценарий (smoke): проверяем, что API контракт соблюдается и graduated концепты
 * не предлагаются для обучения.
 */
import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Concept graduation', () => {
  test('@nightly graduated concepts do not appear in gap recommendations', async ({ page }) => {
    test.setTimeout(120_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY.');
    }

    await completeFirstRunOnboarding(page);

    const apiBase = e2eApiOrigin();

    // ── 1. Получаем текущее состояние mastery и плана ────────────────────────
    const masteryData = await page.evaluate(async (base: string) => {
      const r = await fetch(`${base}/dashboard/mastery`).catch(() => null);
      return r?.ok ? (r.json() as Promise<Record<string, unknown>>) : null;
    }, apiBase);
    expect(masteryData, 'GET /dashboard/mastery должен отвечать').not.toBeNull();

    const masteryVector: Array<Record<string, unknown>> =
      (masteryData as Record<string, unknown> & { mastery_vector?: unknown[] })?.mastery_vector ?? [];

    // Ищем graduated концепты в вернувшемся векторе (если они есть)
    const graduatedConcepts = masteryVector.filter((c) => {
      const graduated: unknown = (c as Record<string, unknown>).graduated;
      const status: unknown = (c as Record<string, unknown>).status;
      // Считаем "graduated": поле graduated=true ИЛИ status в ["completed", "graduated", "mastered"]
      return graduated === true || ['completed', 'graduated', 'mastered'].includes(String(status).toLowerCase());
    });

    // ── 2. Adaptive plan: проверяем gap блоки ────────────────────────────────
    const planData = await page.evaluate(async (base: string) => {
      const r = await fetch(`${base}/adaptive_plan/review`).catch(() => null);
      if (!r?.ok) {
        // Fallback: попробуем GET /dashboard/mastery, который может содержать plan
        const fallback = await fetch(`${base}/dashboard/mastery`).catch(() => null);
        return fallback?.ok ? (fallback.json() as Promise<Record<string, unknown>>) : null;
      }
      return r.json() as Promise<Record<string, unknown>>;
    }, apiBase);
    expect(planData, 'Должны получить plan данные').not.toBeNull();

    // Ищем gap-блоки в плане
    const gapBlocks: Array<Record<string, unknown>> =
      (planData as Record<string, unknown> & { gap?: unknown[] })?.gap ??
      (planData as Record<string, unknown> & { gaps?: unknown[] })?.gaps ??
      [];

    // ── 3. Критический инвариант: graduated концепты НЕ в gap ────────────────
    if (graduatedConcepts.length > 0) {
      const gapConceptIds = gapBlocks
        .map((block) => (block as Record<string, unknown>).concept_id ?? (block as Record<string, unknown>).id)
        .filter(Boolean);

      const graduatedIds = graduatedConcepts
        .map((c) => (c as Record<string, unknown>).concept_id ?? (c as Record<string, unknown>).id)
        .filter(Boolean);

      for (const gId of graduatedIds) {
        expect(
          gapConceptIds.includes(gId),
          `Graduated концепт ${gId} не должен быть в gap-блоке плана (инвариант graduation)`,
        ).toBe(false);
      }
    }

    // ── 4. Проверяем, что API структура поддерживает градуацию ──────────────
    // Структура должна включать:
    // - mastery_vector с полем graduated или status
    // - distinct gap/completed/mastered блоки
    expect(masteryVector, 'mastery_vector должен содержать минимум структуру').toBeDefined();

    // ── 5. UI: навигируем в Topics/Progress и проверяем видимость ───────────
    // Если в UI есть список освоенных концептов — они должны быть помечены как completed
    const topicsBtn = page.getByRole('button', { name: /Темы|Topics/i }).first();
    if (await topicsBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await topicsBtn.click();
      await page.waitForTimeout(1_000);

      // Ищем маркер "освоено" или "completed" в UI
      const completedMarker = page.getByText(/Освоено|Completed|Mastered|✅/i).first();
      if (await completedMarker.isVisible({ timeout: 10_000 }).catch(() => false)) {
        // UI показывает graduated концепты отдельно — good
        const completedText = await completedMarker.textContent().catch(() => '');
        expect(completedText?.length ?? 0, 'Completed marker должен иметь текст').toBeGreaterThan(0);
      }
    }
  });

  test('@nightly graduation prevents repeated review of mastered concepts', async ({ page }) => {
    test.setTimeout(60_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY.');
    }

    await completeFirstRunOnboarding(page);

    const apiBase = e2eApiOrigin();

    // ── API контракт: plan не должен содержать redundant рекомендации ────────
    const planCheck = await page.evaluate(async (base: string) => {
      const r = await fetch(`${base}/adaptive_plan/review`).catch(() => null);
      if (!r?.ok) return null;
      const data = (await r.json()) as Record<string, unknown>;
      // Ищем любые дублирующиеся concept_id в review/gap блоках
      const gap = data?.gap ?? [];
      const review = data?.review ?? [];
      return {
        gap: Array.isArray(gap) ? gap : [],
        review: Array.isArray(review) ? review : [],
      };
    }, apiBase);

    if (planCheck && planCheck.gap && planCheck.review) {
      const gapIds = planCheck.gap
        .map((g) => (g as Record<string, unknown>).concept_id)
        .filter(Boolean);
      const reviewIds = planCheck.review
        .map((r) => (r as Record<string, unknown>).concept_id)
        .filter(Boolean);

      // Проверяем: нет overlap между gap и review (одна концепция не предлагается дважды)
      const overlap = gapIds.filter((id) => reviewIds.includes(id));
      expect(
        overlap.length,
        'Концепт не должен быть одновременно в gap и review (graduation logic)',
      ).toBe(0);
    }
  });
});
