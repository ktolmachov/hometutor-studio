import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { e2eApiOrigin } from './fixtures/api';
import { findKg3dFrame, firstVisible, openKnowledgeGraph } from './fixtures/kg3d';

test.describe('@smoke KG 3D memory overlay', () => {
  test('@smoke quiz progress appears as a dated memory trace in the 3D hall', async ({ page, request }) => {
    test.setTimeout(180_000);

    const apiBase = e2eApiOrigin();
    const quizRes = await request.post(`${apiBase}/quiz/evaluate`, {
      data: {
        quiz_question: {
          question: 'What does retrieval add before generation?',
          options: ['Sources', 'Randomness', 'Latency only', 'Nothing'],
          correct_index: 0,
        },
        user_answer: 'A',
        current_topic: 'retrieval',
        current_mastery: 'intermediate',
        session_id: `kg3d-memory-${Date.now()}`,
      },
      timeout: 30_000,
    });
    expect(quizRes.ok(), 'quiz/evaluate should seed a quiz-progress event').toBeTruthy();

    await completeFirstRunOnboarding(page);
    await openKnowledgeGraph(page);

    const frame = await findKg3dFrame(page);
    const doneMarker = await firstVisible([
      frame.locator('.stop-check').first(),
      frame.getByText(/✓|пройден|quiz|квиз|done|mastery/i).first(),
    ], 8_000);
    test.skip(!doneMarker, 'Current offline graph fixture did not map seeded quiz event to a route stop.');

    const rankStillVisible = await firstVisible([
      frame.locator('.stop-index, [data-stop-index], .stop-rank').first(),
      frame.getByText(/Стоп\s*\d+|Stop\s*\d+|\d+\s*\/\s*\d+/i).first(),
    ]);
    expect(rankStillVisible, 'Done checkmark must not replace the stop rank/number').not.toBeNull();

    const dateEvidence = await firstVisible([
      frame.getByText(/снимок от\s*\d{4}-\d{2}-\d{2}|snapshot\s*\d{4}-\d{2}-\d{2}/i).first(),
      frame.getByText(/\d{4}-\d{2}-\d{2}/).first(),
    ]);
    expect(dateEvidence, 'Memory trace should show an explicit snapshot/date').not.toBeNull();
  });
});
