import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { e2eScopeSeed } from './fixtures/course_scope';

test.describe('@smoke Course scope deactivation', () => {
  test('@smoke generation without folder_rel omits folder tags', async ({ request }) => {
    test.setTimeout(60_000);
    const seed = e2eScopeSeed();
    const apiBase = e2eApiOrigin();

    const generatedRes = await request.post(`${apiBase}/flashcards/generate`, {
      data: {
        scope: 'course',
        source_paths: seed.sourcePaths,
        course_id: 'e2e-no-folder-tag',
        course_title: seed.title,
        num_cards: 5,
      },
      timeout: 60_000,
    });
    expect(generatedRes.status()).toBe(200);
    const generated = (await generatedRes.json()) as { cards: Array<{ tags?: string }> };
    expect(generated.cards.length).toBeGreaterThan(0);
    expect(generated.cards[0]?.tags ?? '').not.toContain('folder:');
  });
});
