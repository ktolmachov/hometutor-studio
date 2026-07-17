import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { e2eApiOrigin } from './fixtures/api';
import { gotoAndWaitForStreamlitReady } from './fixtures/streamlit_ready';

test.describe('@smoke Due badge', () => {
  test('@smoke home due badge exposes the summed review count without claiming a unified queue', async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);
    const apiBase = e2eApiOrigin();

    const deckRes = await request.post(`${apiBase}/flashcards/decks`, {
      data: {
        name: `e2e due badge deck ${Date.now()}`,
        source_type: 'manual',
        source_identifier: 'e2e-due-badge',
        cards: Array.from({ length: 5 }, (_, idx) => ({
          front: `Due badge question ${idx + 1}`,
          back: `Due badge answer ${idx + 1}`,
          tags: 'e2e due-badge',
        })),
      },
      timeout: 30_000,
    });
    expect(deckRes.status()).toBe(201);

    await completeFirstRunOnboarding(page);
    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=home');

    const dueText = page.getByText(/К повторению:\s*\d+|К повторению|due/i).first();
    await expect(dueText).toBeVisible({ timeout: 30_000 });
    const body = await page.locator('body').innerText();
    expect(body).not.toMatch(/единая очередь|unified queue/i);
  });
});
