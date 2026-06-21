/**
 * @smoke CJM Moment of Truth #7 — SRS soft-recovery при большой очереди overdue
 *
 * Проверяет контракт POST /flashcards/due/recovery:
 *   - вызов не падает
 *   - количество due-карточек после recovery ≤ keep_limit
 *   - ответ содержит поле moved ≥ 0
 *
 * Работает без LLM — только API. Если due-карточек < keep_limit, moved=0 (тривиально OK).
 */
import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';

const KEEP_LIMIT = 5;

test.describe('@smoke SRS soft-recovery', () => {
  test('@smoke due/recovery limits queue size and returns moved count', async ({ request }) => {
    test.setTimeout(60_000);

    const apiBase = e2eApiOrigin();

    // ── 1. Текущая очередь before ────────────────────────────────────────────
    const dueBeforeRes = await request.get(`${apiBase}/flashcards/due?limit=1000`, { timeout: 30_000 });
    expect(dueBeforeRes.ok(), 'GET /flashcards/due должен отвечать 200').toBeTruthy();
    const dueBefore = (await dueBeforeRes.json()) as { count?: number };
    const countBefore: number = dueBefore.count ?? 0;

    // ── 2. Вызываем recovery ─────────────────────────────────────────────────
    const recoveryRes = await request.post(`${apiBase}/flashcards/due/recovery`, {
      timeout: 30_000,
      data: { keep_limit: KEEP_LIMIT, stagger_days: 3 },
    });
    expect(recoveryRes.ok(), 'POST /flashcards/due/recovery должен отвечать 200').toBeTruthy();
    const recoveryResult = (await recoveryRes.json()) as { moved?: number };
    const moved: number = recoveryResult.moved ?? -1;
    expect(moved, 'Поле moved должно быть >= 0').toBeGreaterThanOrEqual(0);

    // ── 3. Очередь after ≤ keep_limit ────────────────────────────────────────
    const dueAfterRes = await request.get(`${apiBase}/flashcards/due?limit=1000`, { timeout: 30_000 });
    expect(dueAfterRes.ok(), 'GET /flashcards/due должен отвечать 200 после recovery').toBeTruthy();
    const dueAfter = (await dueAfterRes.json()) as { count?: number };
    const countAfter: number = dueAfter.count ?? 0;

    expect(
      countAfter,
      `После recovery очередь должна быть ≤ ${KEEP_LIMIT} (было ${countBefore}, перенесено ${moved})`,
    ).toBeLessThanOrEqual(KEEP_LIMIT);

    // ── 4. Инвариант: moved = countBefore - countAfter ────────────────────────
    if (countBefore > KEEP_LIMIT) {
      expect(moved, 'moved должен совпасть с разницей очередей').toBe(countBefore - countAfter);
    } else {
      // Если карточек и так мало — moved=0, очередь не изменилась
      expect(moved).toBe(0);
    }
  });

  test('@smoke recovery is idempotent — calling twice does not move more than available', async ({ request }) => {
    test.setTimeout(60_000);

    const apiBase = e2eApiOrigin();

    const firstRes = await request.post(`${apiBase}/flashcards/due/recovery`, {
      timeout: 30_000,
      data: { keep_limit: KEEP_LIMIT },
    });
    expect(firstRes.ok()).toBeTruthy();

    const secondRes = await request.post(`${apiBase}/flashcards/due/recovery`, {
      timeout: 30_000,
      data: { keep_limit: KEEP_LIMIT },
    });
    expect(secondRes.ok()).toBeTruthy();
    const secondCall = (await secondRes.json()) as { moved?: number };

    // Второй вызов не должен перемещать уже перемещённые карточки
    const movedSecond: number = secondCall.moved ?? -1;
    expect(movedSecond, 'Второй вызов recovery должен переместить 0 карточек (идемпотентность)').toBe(0);
  });
});
