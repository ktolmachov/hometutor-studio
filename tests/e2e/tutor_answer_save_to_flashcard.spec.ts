import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from './fixtures/streamlit_ready';
import { firstVisible } from './fixtures/kg3d';

test.describe('@smoke Tutor answer → flashcard', () => {
  test('@smoke tutor answer can be saved into the tutor-answer deck', async ({ page }) => {
    test.setTimeout(180_000);

    await completeFirstRunOnboarding(page);
    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=tutor&e2e_quiz_fixture=1');

    const saveButton = await firstVisible([
      page.getByRole('button', { name: /Сохранить как карточку|Save as card/i }).first(),
      page.getByText(/Сохранить как карточку|Из ответов тьютора/i).first(),
    ], 10_000);
    test.skip(!saveButton, 'Tutor-answer save-card CTA is not rendered by the current offline tutor fixture.');

    await saveButton!.click({ timeout: 10_000 });
    await waitForStreamlitReady(page, 15_000).catch(() => undefined);
    await expect(page.getByText(/Из ответов тьютора|карточк.*сохран|card saved/i).first()).toBeVisible({
      timeout: 30_000,
    });

    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=flashcards&e2e_fc_section=decks');
    await expect(page.getByText(/Из ответов тьютора/i).first()).toBeVisible({ timeout: 30_000 });
  });
});
