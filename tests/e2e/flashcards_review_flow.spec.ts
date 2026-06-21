import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

test.describe('@smoke Flashcards review flow', () => {
  test('@smoke user can generate a deck and complete one review session', async ({ page }) => {
    test.setTimeout(180_000);
    await completeFirstRunOnboarding(page);
    // Не фиксировать e2e_fc_section=create в URL: main.py при каждом rerun снова принудит create
    // и отменит переход на колоды после сохранения.
    await page.goto('/?e2e_view=flashcards&e2e_fc_source=upload', {
      waitUntil: 'domcontentloaded',
    });
    await page.getByRole('button', { name: /Создать/i }).first().click();
    await expect(page.locator('[data-testid="e2e-fc-active-section"]').first()).toContainText(/create/i, {
      timeout: 60_000,
    });

    const main = page.locator('[data-testid="stMain"]').first();

    // Не использовать первый input[type=file] на странице: в сайдбаре есть backup JSON uploader.
    const fcUploadDropzone = page.getByLabel(/Загрузи файл \(PDF, TXT, MD, DOCX\)/i);
    await expect(fcUploadDropzone).toBeVisible({ timeout: 120_000 });
    const fileInput = fcUploadDropzone.locator('input[type="file"]');

    await fileInput.setInputFiles({
      name: 'flashcards-source.md',
      mimeType: 'text/markdown',
      buffer: Buffer.from(
        [
          '# Retrieval Augmented Generation',
          '',
          'RAG combines retrieval from a knowledge base with generation.',
          'Chunking splits documents into smaller pieces.',
          'Embeddings help compare semantic similarity between question and chunks.',
          'A retriever selects relevant chunks before the model answers.',
          'Good prompts and trusted sources improve answer quality.',
        ].join('\n'),
        'utf-8',
      ),
    });

    await page.locator('[data-testid="e2e-fc-generate"]').first().waitFor({ state: 'attached', timeout: 10_000 });
    await main.getByRole('button', { name: /Сгенерировать карточки/i }).click();

    await expect(main.getByRole('heading', { name: /Предпросмотр — \d+ карточек/ })).toBeVisible({
      timeout: 90_000,
    });

    await page.locator('[data-testid="e2e-fc-save-deck"]').first().waitFor({ state: 'attached', timeout: 10_000 });
    const deckTitle = `e2e deck ${Date.now()}`;
    await main.getByLabel('Название колоды').fill(deckTitle);
    await main.getByRole('button', { name: /Сохранить колоду/i }).click();

    // После сохранения сразу st.rerun() в колоды — toasts могут не успеть поймать.
    await expect(page.locator('[data-testid="e2e-fc-active-section"]').first()).toContainText(/decks/i, {
      timeout: 30_000,
    });

    await page.getByRole('button', { name: /Повторение/i }).first().click();

    await page.getByRole('button', { name: /Загрузить очередь/i }).click();
    await expect(page.getByText(/Карточка 1 из|Показать ответ|Сейчас нет карточек к повторению/i).first()).toBeVisible({
      timeout: 30_000,
    });

    const flip = page.getByRole('button', { name: /Показать ответ/i }).first();
    if (await flip.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await flip.click();
      await page.getByRole('button', { name: /Снова|Трудно|Хорошо|Легко/i }).first().click();
      await expect(page.getByText(/Карточка|Сессия завершена|Осталось:/i).first()).toBeVisible({
        timeout: 30_000,
      });
    }
  });
});
