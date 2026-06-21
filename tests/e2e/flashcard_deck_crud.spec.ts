/**
 * @smoke API Contract — Flashcard Deck CRUD
 *
 * Проверяет полный цикл колод:
 *   - POST /flashcards/decks → create
 *   - GET /flashcards/decks → list
 *   - GET /flashcards/decks/{id} → get single
 *   - DELETE /flashcards/decks/{id} → delete
 *
 * Работает без LLM — только API.
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';

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

test.describe('@smoke Flashcard Deck CRUD', () => {
  test('@smoke create → list → get → delete deck', async ({ request }) => {
    test.setTimeout(60_000);

    const apiBase = e2eApiOrigin();
    const deckName = `e2e deck ${Date.now()}`;

    // ── 1. Create deck ───────────────────────────────────────────────────────
    const createRes = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/decks`,
      {
        name: deckName,
        source_type: 'upload',
        source_identifier: null,
        cards: [
          { front: 'What is RAG?', back: 'Retrieval Augmented Generation' },
          { front: 'What is chunking?', back: 'Splitting documents into smaller pieces' },
          { front: 'What are embeddings?', back: 'Semantic similarity vectors' },
          { front: 'What does retriever do?', back: 'Selects relevant chunks before answering' },
          { front: 'Why use prompts?', back: 'To improve answer quality' },
        ],
      },
    );
    expect(createRes.status, `POST /flashcards/decks → ${createRes.status}`).toBe(201);
    const deckId = createRes.json.deck_id as number;
    expect(deckId, 'deck_id must be returned').toBeGreaterThan(0);

    // ── 2. List decks ────────────────────────────────────────────────────────
    const listRes = await apiRequest(request, 'get', `${apiBase}/flashcards/decks`);
    expect(listRes.status, `GET /flashcards/decks → ${listRes.status}`).toBe(200);
    const decks = listRes.json.decks as Array<{ id: number; name: string }>;
    expect(decks.length, 'At least 1 deck after creation').toBeGreaterThan(0);
    const created = decks.find(d => d.id === deckId);
    expect(created, 'Created deck appears in list').toBeDefined();
    expect(created?.name).toBe(deckName);

    // ── 3. Get single deck ───────────────────────────────────────────────────
    const getRes = await apiRequest(request, 'get', `${apiBase}/flashcards/decks/${deckId}`);
    expect(getRes.status, `GET /flashcards/decks/${deckId} → ${getRes.status}`).toBe(200);
    const deck = getRes.json as { id: number; name: string; cards: Array<{ front: string }> };
    expect(deck.id).toBe(deckId);
    expect(deck.name).toBe(deckName);
    expect(deck.cards.length, 'Deck has 5 cards').toBe(5);
    expect(deck.cards[0].front).toBe('What is RAG?');

    // ── 4. Delete deck ───────────────────────────────────────────────────────
    const deleteRes = await apiRequest(request, 'delete', `${apiBase}/flashcards/decks/${deckId}`);
    expect(deleteRes.status, `DELETE /flashcards/decks/${deckId} → ${deleteRes.status}`).toBe(200);

    // ── 5. Verify deletion ───────────────────────────────────────────────────
    const afterDelete = await apiRequest(request, 'get', `${apiBase}/flashcards/decks/${deckId}`);
    expect(afterDelete.status, 'Deleted deck returns 404').toBe(404);
  });

  test('@smoke deck not found returns 404', async ({ request }) => {
    const apiBase = e2eApiOrigin();
    const res = await apiRequest(request, 'get', `${apiBase}/flashcards/decks/999999`);
    expect(res.status).toBe(404);
  });

  test('@smoke create deck with invalid data fails', async ({ request }) => {
    const apiBase = e2eApiOrigin();

    // Too few cards (< 5) should fail
    const res = await apiRequest(
      request,
      'post',
      `${apiBase}/flashcards/decks`,
      {
        name: 'Invalid Deck',
        cards: [{ front: 'Q', back: 'A' }],
      },
    );
    expect(res.status).toBeGreaterThanOrEqual(400);
  });
});