import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { e2eApiOrigin } from './fixtures/api';
import { e2eScopeQuery, e2eScopeSeed } from './fixtures/course_scope';
import { waitForStreamlitReady } from './fixtures/streamlit_ready';

/**
 * Consolidated offline smoke for wave-course-learning-v2 / course-workspace:
 * API course deck → UI активная область курса → Progress (course_workspace) → Flashcards.
 * Флаг RAG_COURSE_COCKPIT_V2 в e2e-стеке по умолчанию выключен; полный cockpit — unit tests.
 */
test.describe('@smoke Course learning wave', () => {
  test('@smoke scoped learner path topics progress flashcards', async ({ page, request }) => {
    test.setTimeout(300_000);
    const apiBase = e2eApiOrigin();
    const seed = e2eScopeSeed();
    const courseId = `e2e-wave-smoke-${Date.now()}`;

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
      cards: unknown[];
      source_identifier: string;
    };
    expect(generated.cards.length).toBeGreaterThanOrEqual(5);

    const savedRes = await request.post(`${apiBase}/flashcards/decks`, {
      data: {
        name: `e2e wave smoke deck ${Date.now()}`,
        source_type: 'course',
        source_identifier: generated.source_identifier,
        cards: generated.cards,
      },
      timeout: 60_000,
    });
    expect(savedRes.status()).toBe(201);

    await completeFirstRunOnboarding(page);

    const navReadyMs = 120_000;

    await page.goto(
      `/?${e2eScopeQuery({ e2e_view: 'topics', e2e_seed_ts: String(Date.now()) })}`,
      { waitUntil: 'domcontentloaded' },
    );
    await waitForStreamlitReady(page, navReadyMs);
    await expect(page.getByTestId('e2e-active-scope')).toContainText(seed.folderRel, {
      timeout: 120_000,
    });

    await page.goto(
      `/?${e2eScopeQuery({ e2e_view: 'progress', e2e_seed_ts: String(Date.now()) })}`,
      { waitUntil: 'domcontentloaded' },
    );
    await waitForStreamlitReady(page, navReadyMs);
    await expect(page.getByText('course_workspace').first()).toBeVisible({ timeout: 120_000 });
    await expect(page.getByText(/Due today/i).first()).toBeVisible({ timeout: 30_000 });

    await page.goto(
      `/?${e2eScopeQuery({
        e2e_view: 'flashcards',
        e2e_fc_section: 'review',
        e2e_seed_ts: String(Date.now()),
      })}`,
      { waitUntil: 'domcontentloaded' },
    );
    await waitForStreamlitReady(page, navReadyMs);
    await expect(page.locator('[data-testid="stMain"]').first()).toBeVisible({
      timeout: 120_000,
    });
  });
});
