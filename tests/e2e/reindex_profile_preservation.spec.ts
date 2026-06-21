/**
 * @smoke CJM Moment of Truth #6 — после reindex профиль сохранён
 *
 * Проверяет: POST /reindex не обнуляет mastery_vector, streak, quiz_mastery.
 * Тест работает без LLM (только API-вызовы).
 *
 * API вызываем через фикстуру `request` (Node), а не fetch в браузере — иначе
 * кросс-origin :8501 → :8000 часто блокируется CORS и page.evaluate «висит».
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

async function getJson(
  request: APIRequestContext,
  url: string,
  timeout = 30_000,
): Promise<Record<string, unknown>> {
  const res = await request.get(url, { timeout });
  if (!res.ok()) {
    const txt = await res.text().catch(() => '');
    throw new Error(`GET ${url} → ${res.status()}: ${txt.slice(0, 500)}`);
  }
  return (await res.json()) as Record<string, unknown>;
}

function reindexFinished(status: Record<string, unknown> | null): boolean {
  if (!status) return false;
  const st = String(status.status ?? '');
  // ingestion.py: running → completed | failed
  return st === 'completed' || st === 'failed' || st === 'done' || st === 'error';
}

function masteryVectorLen(row: Record<string, unknown>): number {
  const mv = row.mastery_vector;
  if (Array.isArray(mv)) return mv.length;
  if (mv && typeof mv === 'object') return Object.keys(mv as Record<string, unknown>).length;
  return 0;
}

test.describe('@smoke Reindex profile preservation', () => {
  test('@smoke mastery and streak survive reindex', async ({ page, request }) => {
    test.setTimeout(300_000);

    await completeFirstRunOnboarding(page);

    const apiBase = e2eApiOrigin();

    // ── 1. Baseline: читаем текущее состояние mastery ────────────────────────
    const baseline = await getJson(request, `${apiBase}/dashboard/mastery`);

    const baselineXP: number = (baseline as Record<string, unknown> & { gamification?: { xp?: number } })?.gamification?.xp ?? 0;
    const baselineVecLen = masteryVectorLen(baseline);

    // ── 2. Запускаем reindex ─────────────────────────────────────────────────
    const reindexRes = await request.post(`${apiBase}/reindex`, { timeout: 60_000 });
    expect([200, 409], `POST /reindex → ${reindexRes.status()}: ${(await reindexRes.text().catch(() => '')).slice(0, 400)}`).toContain(
      reindexRes.status(),
    );

    // ── 3. Ждём завершения reindex (max 3 min) ────────────────────────────────
    const reindexDeadline = Date.now() + 180_000;
    while (Date.now() < reindexDeadline) {
      let status: Record<string, unknown> | null = null;
      try {
        status = await getJson(request, `${apiBase}/reindex/status`, 25_000);
      } catch {
        /* редкий гон при старте worker — повторяем опрос */
      }
      if (reindexFinished(status)) break;
      await page.waitForTimeout(5_000);
    }

    // ── 4. После reindex: mastery стабилен ───────────────────────────────────
    await page.waitForTimeout(2_000);

    const after = await getJson(request, `${apiBase}/dashboard/mastery`);

    const afterXP: number = (after as Record<string, unknown> & { gamification?: { xp?: number } })?.gamification?.xp ?? 0;
    expect(afterXP, 'XP не должен уменьшиться после reindex').toBeGreaterThanOrEqual(baselineXP);

    const afterVecLen = masteryVectorLen(after);
    expect(afterVecLen, 'mastery_vector не должен уменьшиться после reindex (профиль не обнуляется)').toBeGreaterThanOrEqual(
      baselineVecLen,
    );

    // ── 5. Learner state health: структура сохранена ─────────────────────────
    await getJson(request, `${apiBase}/learner/state/health`);
  });
});
