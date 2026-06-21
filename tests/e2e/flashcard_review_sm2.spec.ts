/**
 * @smoke API Contract — Flashcard SM-2 Review
 *
 * Проверяет:
 *   - POST /flashcards/review с разными quality (0-5)
 *   - POST /flashcards/review с quality_label (again/hard/good/easy)
 *   - next_review обновляется после review
 *   - GET /flashcards/due возвращает обновлённую карточку
 *
 * Работает без LLM — только API.
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

async function apiRequest(
  request: APIRequestContext,
  method: string,
  url: string,
  body?: unknown,
  timeout = 30_000,
): Promise<{ status: number; json: Record<string, unknown> }> {
  const res = await request[method as 'get' | 'post' | 'put' | 'delete'](url, {
    timeout,
    data: body,
  });
  const json = res.ok() ? ((await res.json()) as Record<string, unknown>) : {};
  return { status: res.status(), json };
}

test.describe('@smoke Flashcard SM-2 Review', () => {
  test('@smoke review with quality labels updates next_review', async ({ page, request }) => {
    test.setTimeout(90_000);

    await completeFirstRunOnboarding(page);
    const apiBase = e2eApiOrigin();

    // ── 1. Create a test deck with one card ───────────────────────────────────
    const createRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/decks`,
      {
        name: `e2e review test ${Date.now()}`,
        source_type: 'upload',
        cards: [
          { front: 'Test Q', back: 'Test A' },
          { front: 'Test Q2', back: 'Test A2' },
          { front: 'Test Q3', back: 'Test A3' },
          { front: 'Test Q4', back: 'Test A4' },
          { front: 'Test Q5', back: 'Test A5' },
        ],
      },
    );
    expect(createRes.status).toBe(201);
    const deckId = createRes.json.deck_id as number;

    // ── 2. Get due cards ──────────────────────────────────────────────────────
    const dueRes = await apiRequest(request, 'get', `${apiBase}/flashcards/due?limit=10&deck_id=${deckId}`);
    expect(dueRes.status).toBe(200);
    const cards = dueRes.json.cards as Array<{ id: number; front: string; next_review: string }>;
    expect(cards.length, 'New cards should be due').toBeGreaterThan(0);
    const card = cards[0];
    const originalNextReview = card.next_review;

    // ── 3. Review with "good" ─────────────────────────────────────────────────
    const reviewRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/review`,
      { card_id: card.id, quality_label: 'good' },
    );
    expect(reviewRes.status, `POST /flashcards/review → ${reviewRes.status}`).toBe(200);
    const updated = reviewRes.json as { next_review: string; interval: number };
    expect(updated.next_review, 'next_review should be updated').not.toBe(originalNextReview);
    expect(updated.interval_days, 'interval_days should be > 0 after review').toBeGreaterThan(0);

    // ── 4. Review with "again" (quality 0) ────────────────────────────────────
    const againRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/review`,
      { card_id: card.id, quality_label: 'again' },
    );
    expect(againRes.status).toBe(200);
    const againUpdated = againRes.json as { next_review: string; interval_days: number };
    expect(againUpdated.interval_days, 'again resets interval').toBeLessThanOrEqual(updated.interval_days);

    // ── 5. Review with explicit quality numeric ───────────────────────────────
    const numericRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/review`,
      { card_id: card.id, quality: 5 },
    );
    expect(numericRes.status).toBe(200);
    const numericUpdated = numericRes.json as { next_review: string; interval_days: number };
    expect(numericUpdated.interval_days, 'quality=5 (easy) should have interval >= again').toBeGreaterThanOrEqual(againUpdated.interval_days);

    // ── 6. Review invalid card ────────────────────────────────────────────────
    const invalidRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/review`,
      { card_id: 999999, quality: 3 },
    );
    expect(invalidRes.status, 'Invalid card returns 404').toBe(404);

    // ── 7. Invalid quality_label ──────────────────────────────────────────────
    const badLabelRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/review`,
      { card_id: card.id, quality_label: 'invalid' },
    );
    expect(badLabelRes.status, 'Invalid quality_label returns 400').toBe(400);

    // ── Cleanup: delete deck ─────────────────────────────────────────────────
    await apiRequest(request, 'delete', `${apiBase}/flashcards/decks/${deckId}`);
  });

  test('@smoke review updates due count', async ({ page, request }) => {
    test.setTimeout(60_000);

    await completeFirstRunOnboarding(page);
    const apiBase = e2eApiOrigin();

    // Create deck with 2 cards
    const createRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/decks`,
      {
        name: `e2e due count test ${Date.now()}`,
        source_type: 'upload',
        cards: [
          { front: 'Q1', back: 'A1' },
          { front: 'Q2', back: 'A2' },
          { front: 'Q3', back: 'A3' },
          { front: 'Q4', back: 'A4' },
          { front: 'Q5', back: 'A5' },
        ],
      },
    );
    expect(createRes.status).toBe(201);
    const deckId = createRes.json.deck_id as number;

    // Get initial due count
    const dueBeforeRes = await apiRequest(request, 'get', `${apiBase}/flashcards/due?limit=10&deck_id=${deckId}`);
    const cardsBefore = dueBeforeRes.json.cards as Array<{ id: number }>;

    // Review all cards
    for (const c of cardsBefore) {
      const r = await apiRequest(request, 'post', `${apiBase}/flashcards/review`, { card_id: c.id, quality: 3 });
      expect(r.status).toBe(200);
    }

    // Due count should be 0
    const dueAfterRes = await apiRequest(request, 'get', `${apiBase}/flashcards/due?limit=10&deck_id=${deckId}`);
    expect((dueAfterRes.json.cards as unknown[]).length, 'All cards reviewed, no due remaining').toBe(0);

    // Cleanup
    await apiRequest(request, 'delete', `${apiBase}/flashcards/decks/${deckId}`);
  });
});