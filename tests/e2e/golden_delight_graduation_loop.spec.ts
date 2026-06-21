import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { e2eScopeQuery, e2eScopeSeed } from './fixtures/course_scope';
import { openQuickAnswerWithOfflineStub } from './fixtures/qa_offline_quick_answer';
import { waitForStreamlitReady } from './fixtures/streamlit_ready';

test.describe('@smoke Golden delight graduation loop', () => {
  test('@smoke Q&A Tutor Quiz Card Review Graduation stays local', async ({ page, request }) => {
    test.setTimeout(300_000);
    const apiBase = e2eApiOrigin();
    const seed = e2eScopeSeed();
    const courseId = `golden-e2e-${Date.now()}`;

    // Q&A
    await openQuickAnswerWithOfflineStub(page);

    // Tutor
    await page.goto(`/?${e2eScopeQuery({ e2e_view: 'tutor' })}`, {
      waitUntil: 'domcontentloaded',
    });
    await waitForStreamlitReady(page, 120_000);
    await expect(page.locator('[data-testid="stMain"]').first()).toBeVisible();

    // Quiz
    const quizRes = await request.post(`${apiBase}/quiz/evaluate`, {
      data: {
        quiz_question: {
          type: 'application',
          prompt: 'Which component grounds an answer in course sources?',
          options: { A: 'Retriever', B: 'Theme', C: 'Timer', D: 'Renderer' },
          correct_option: 'A',
        },
        user_answer_letter: 'A',
        current_topic: 'RAG',
        current_mastery: 'intermediate',
      },
      timeout: 30_000,
    });
    expect(quizRes.ok()).toBeTruthy();
    const quiz = (await quizRes.json()) as { quiz_feedback?: { status?: string } };
    expect(['correct', 'partial', 'incorrect']).toContain(String(quiz.quiz_feedback?.status));

    // Card
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
    expect(generatedRes.ok()).toBeTruthy();
    const generated = (await generatedRes.json()) as {
      cards: unknown[];
      source_identifier: string;
    };
    expect(generated.cards.length).toBeGreaterThanOrEqual(5);

    const savedRes = await request.post(`${apiBase}/flashcards/decks`, {
      data: {
        name: `golden delight deck ${Date.now()}`,
        source_type: 'course',
        source_identifier: generated.source_identifier,
        cards: generated.cards,
      },
      timeout: 60_000,
    });
    expect(savedRes.status()).toBe(201);

    // Review
    await page.goto(
      `/?${e2eScopeQuery({ e2e_view: 'flashcards', e2e_fc_section: 'review' })}`,
      { waitUntil: 'domcontentloaded' },
    );
    await waitForStreamlitReady(page, 120_000);
    await expect(page.locator('[data-testid="e2e-fc-active-section"]').first()).toContainText(
      /review/i,
      { timeout: 60_000 },
    );

    // Graduation: offline-only hook emits the real session-tape event and renders its receipt.
    await page.goto(
      `/?${e2eScopeQuery({
        e2e_view: 'home',
        e2e_delight_complete: '1',
        e2e_delight_session: courseId,
      })}`,
      { waitUntil: 'domcontentloaded' },
    );
    await waitForStreamlitReady(page, 120_000);

    for (const step of ['q-a', 'tutor', 'quiz', 'card', 'review', 'graduation']) {
      await expect(page.getByTestId(`delight-step-${step}`)).toHaveAttribute(
        'data-status',
        'complete',
      );
    }

    const graduation = page.getByTestId('e2e-graduation-metadata');
    await expect(graduation).toHaveAttribute('data-llm-model', /qwen\/qwen3\.6-27b/i);
    await expect(graduation).toHaveAttribute('data-llm-source', 'local');
    await expect(graduation).toHaveAttribute('data-fallback-used', 'false');
  });
});
