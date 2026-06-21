import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { e2eScopeSeed } from './fixtures/course_scope';

test.describe('@smoke Course scope activation', () => {
  test('@smoke course scope payload is accepted by generation API', async ({ request }) => {
    test.setTimeout(60_000);
    const seed = e2eScopeSeed();
    const apiBase = e2eApiOrigin();

    const res = await request.post(`${apiBase}/flashcards/generate`, {
      data: {
        scope: 'course',
        source_paths: seed.sourcePaths,
        course_id: 'e2e-scope-activation',
        course_title: seed.title,
        folder_rel: seed.folderRel,
        num_cards: 5,
      },
      timeout: 60_000,
    });
    expect(res.status()).toBe(200);
    const body = (await res.json()) as { success: boolean; source_identifier: string; deck_title: string };
    expect(body.success).toBeTruthy();
    expect(body.deck_title).toBe(seed.title);
    expect(body.source_identifier).toContain(seed.folderRel);
  });

  test('@smoke course scope without source_paths returns 400', async ({ request }) => {
    const apiBase = e2eApiOrigin();
    const res = await request.post(`${apiBase}/flashcards/generate`, {
      data: {
        scope: 'course',
        course_id: 'e2e-missing-paths',
        course_title: 'Invalid scope payload',
        folder_rel: 'e2e-course-offline',
        num_cards: 5,
      },
      timeout: 30_000,
    });
    expect(res.status()).toBe(400);
    const body = (await res.json()) as { detail?: string };
    expect(String(body.detail || '')).toContain('source_paths');
  });
});
