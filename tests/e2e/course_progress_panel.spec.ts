import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { e2eApiOrigin } from './fixtures/api';
import { e2eScopeQuery, e2eScopeSeed } from './fixtures/course_scope';

test.describe('@smoke Course progress panel', () => {
  test('@smoke active course progress panel shows course metrics', async ({ page, request }) => {
    test.setTimeout(180_000);
    const apiBase = e2eApiOrigin();
    const seed = e2eScopeSeed();
    const courseId = `e2e-progress-${Date.now()}`;

    const generatedRes = await request.post(`${apiBase}/flashcards/generate`, {
      data: {
        scope: 'course',
        source_paths: seed.sourcePaths,
        course_id: courseId,
        course_title: seed.title,
        folder_rel: seed.folderRel,
        num_cards: 5,
      },
      timeout: 60_000,
    });
    expect(generatedRes.status()).toBe(200);
    const generated = (await generatedRes.json()) as {
      cards: Array<{ front?: string; back?: string; tags?: string }>;
      source_identifier: string;
    };
    expect(generated.cards.length).toBeGreaterThanOrEqual(5);

    const savedRes = await request.post(`${apiBase}/flashcards/decks`, {
      data: {
        name: `e2e progress course deck ${Date.now()}`,
        source_type: 'course',
        source_identifier: generated.source_identifier,
        cards: generated.cards,
      },
      timeout: 60_000,
    });
    expect(savedRes.status()).toBe(201);

    await completeFirstRunOnboarding(page);
    await page.goto(`/?${e2eScopeQuery({ e2e_view: 'progress', e2e_seed_ts: String(Date.now()) })}`, {
      waitUntil: 'domcontentloaded',
    });

    await expect(page.getByText('course_workspace').first()).toBeVisible({ timeout: 120_000 });
    await expect(page.getByText(/Due today/i).first()).toBeVisible({ timeout: 30_000 });
    await expect(page.getByText(seed.folderRel).first()).toBeVisible({ timeout: 30_000 });
  });
});
