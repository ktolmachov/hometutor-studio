import { test, expect } from '@playwright/test';
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from '../fixtures/demo_recorder';
import { DEMO } from '../fixtures/demo_timeouts';
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

/**
 * Demo scenario #05 — Flashcards: сгенерировать, отредактировать, сохранить.
 * Использует HOME_RAG_E2E_OFFLINE=1 для детерминированных stub-карточек.
 * Манифест: doc/scenarios/scenario_05_flashcards_create.yaml.
 */
test.describe('@demo Scenario 05 — flashcards create', () => {
  test('@demo captures create → preview → save', async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, 'scenario_05');

    try {
      await completeFirstRunOnboarding(page);
      const createTab = page.getByRole('button', { name: '✨ Создать', exact: true });
      let flashcardsReady = false;
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        await gotoAndWaitForStreamlitReady(page, '/?e2e_view=flashcards&e2e_fc_source=upload');
        flashcardsReady = await createTab
          .waitFor({ state: 'visible', timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false);
        if (flashcardsReady) {
          break;
        }
        await page.waitForTimeout(300);
      }
      if (!flashcardsReady) {
        throw new Error('Scenario 05: flashcards create tab did not become visible');
      }

      await demo.shot('01_flashcards_section', {
        caption: 'Раздел Flashcards: три подвкладки',
        narration: 'Три зоны: что есть, что создать, что повторить.',
        fullPage: true,
      });

      // Точное имя навигационной кнопки — иначе после других demo-тестов `.first()`
      // может схватить другой control с «Создать» в дереве страницы.
      await createTab.click();
      await expect(page.getByLabel(/Загрузи файл \(PDF, TXT, MD, DOCX\)/i)).toBeVisible({
        timeout: DEMO.visibleMs,
      });
      await waitForStreamlitReady(page);
      await demo.shot('02_create_new_upload', {
        caption: 'Создание карточек: загрузка файла',
        narration: '5–20 карточек из любого документа.',
      });

      const main = page.locator('[data-testid="stMain"]').first();
      const dropzone = page.getByLabel(/Загрузи файл \(PDF, TXT, MD, DOCX\)/i);
      await expect(dropzone).toBeVisible({ timeout: DEMO.visibleMs });
      const fileInput = dropzone.locator('input[type="file"]');
      await fileInput.setInputFiles({
        name: 'demo-source.md',
        mimeType: 'text/markdown',
        buffer: Buffer.from(
          [
            '# Retrieval Augmented Generation',
            '',
            'RAG объединяет поиск по базе знаний с генерацией ответа.',
            'Чанкинг разбивает документы на меньшие фрагменты.',
            'Эмбеддинги помогают сравнивать семантическую близость.',
            'Ретривер отбирает релевантные фрагменты перед моделью.',
            'Хорошие промпты и источники — ключ к качеству ответа.',
          ].join('\n'),
          'utf-8',
        ),
      });

      await page
        .locator('[data-testid="e2e-fc-generate"]')
        .first()
        .waitFor({ state: 'attached', timeout: DEMO.visibleMs });
      await main.getByRole('button', { name: /Сгенерировать карточки/i }).click();

      await expect(
        main.getByRole('heading', { name: /Предпросмотр — \d+ карточек/ }),
      ).toBeVisible({ timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);

      await demo.shot('03_preview_generated', {
        caption: 'Preview сгенерированных карточек',
        narration: 'LLM даёт first draft — человек проверяет.',
        fullPage: true,
      });

      await page
        .locator('[data-testid="e2e-fc-save-deck"]')
        .first()
        .waitFor({ state: 'attached', timeout: DEMO.visibleMs });
      const deckTitle = `demo deck ${Date.now()}`;
      await main.getByLabel('Название колоды').fill(deckTitle);
      await main.getByRole('button', { name: /Сохранить колоду/i }).click();

      await expect(
        page.locator('[data-testid="e2e-fc-active-section"]').first(),
      ).toContainText(/decks/i, { timeout: DEMO.ctaMs });
      await waitForStreamlitReady(page);

      await demo.shot('04_save_deck', {
        caption: 'Сохранение колоды',
        narration: 'Минимум 5 валидных карточек — колода в базе.',
        fullPage: true,
      });

      await demo.finalize('passed');
    } catch (err) {
      await demo.finalize('failed');
      throw err;
    }
  });
});
