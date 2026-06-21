import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { e2eScopeSeed } from './fixtures/course_scope';

test.describe('@smoke Flashcards course generation', () => {
  test('@smoke generate and save deck from active course', async ({ request }) => {
    test.setTimeout(60_000);
    const apiBase = e2eApiOrigin();
    const seed = e2eScopeSeed();

    const generatedRes = await request.post(`${apiBase}/flashcards/generate`, {
      data: {
        scope: 'course',
        source_paths: seed.sourcePaths,
        course_id: 'e2e-course-id',
        course_title: seed.title,
        folder_rel: seed.folderRel,
        num_cards: 5,
      },
      timeout: 60_000,
    });
    expect(generatedRes.status()).toBe(200);
    const generated = (await generatedRes.json()) as {
      success: boolean;
      cards: Array<{ tags?: string }>;
      deck_title: string;
      source_identifier: string;
    };
    expect(generated.success).toBeTruthy();
    expect(generated.deck_title).toBe(seed.title);
    expect(generated.cards.length).toBeGreaterThan(0);
    expect(generated.cards[0]?.tags ?? '').toContain('course:e2e-course-id');

    const deckName = `e2e course deck ${Date.now()}`;
    const savedRes = await request.post(`${apiBase}/flashcards/decks`, {
      data: {
        name: deckName,
        source_type: 'course',
        source_identifier: generated.source_identifier,
        cards: generated.cards,
      },
      timeout: 60_000,
    });
    expect(savedRes.status()).toBe(201);
    const saved = (await savedRes.json()) as { deck_id: number; card_count: number };
    expect(saved.card_count).toBeGreaterThanOrEqual(5);

    const dueRes = await request.get(`${apiBase}/flashcards/due?limit=20&tags=course:e2e-course-id`, {
      timeout: 30_000,
    });
    expect(dueRes.status()).toBe(200);
  });
});
