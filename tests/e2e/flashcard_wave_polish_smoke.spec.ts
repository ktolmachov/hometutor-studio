/**
 * @smoke Wave flashcard-polish — UI детали колоды (epoch-flashcard-deck-mgmt /
 * epoch-flashcard-export-upload): при HOME_RAG_E2E_OFFLINE список колод приходит
 * из bootstrap-стаба; открываем стаб-колоду и проверяем контроль экспорта Anki
 * и первую карточку в списке (без сохранения — PUT карточки в offline даёт 404).
 *
 * CRUD/API карточек и колод — pytest (`tests/test_flashcard_deck_mgmt.py`).
 */
import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const OFFLINE_STUB_DECK = 'E2E Offline RAG Deck';

test.describe('@smoke Flashcard polish wave', () => {
  test('@smoke deck detail shows Anki export + card row (offline stub deck)', async ({ page }) => {
    test.setTimeout(120_000);

    await completeFirstRunOnboarding(page);

    await page.goto('/?e2e_view=flashcards&e2e_fc_section=decks', {
      waitUntil: 'domcontentloaded',
    });

    const main = page.locator('[data-testid="stMain"]').first();
    await expect(main.getByText(OFFLINE_STUB_DECK)).toBeVisible({ timeout: 90_000 });

    await main.getByRole('button', { name: 'Открыть' }).first().click();

    await expect(main.getByRole('heading', { name: new RegExp(OFFLINE_STUB_DECK, 'i') })).toBeVisible({
      timeout: 30_000,
    });

    await expect(main.getByRole('button', { name: /Anki.*apkg/i }).first()).toBeVisible({
      timeout: 30_000,
    });

    await expect(main.getByText(/What does retrieval add before generation/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });
});
