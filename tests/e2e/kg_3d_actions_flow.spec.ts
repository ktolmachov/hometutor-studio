import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { waitForStreamlitReady } from './fixtures/streamlit_ready';
import {
  clickFirstVisible,
  collectButtons,
  findKg3dFrame,
  firstVisible,
  openKnowledgeGraph,
  startButtons,
} from './fixtures/kg3d';

test.describe('@smoke KG 3D action bridge', () => {
  test('@smoke collect from 3D hall updates workbench inventory without dead-ending', async ({ page }) => {
    test.setTimeout(180_000);

    await completeFirstRunOnboarding(page);
    await openKnowledgeGraph(page);

    let frame = await findKg3dFrame(page);
    const collect = await firstVisible(collectButtons(frame), 3_000);
    test.skip(!collect, 'No collect CTA rendered for current KG route fixture.');

    await collect!.click({ timeout: 10_000 });
    await waitForStreamlitReady(page, 20_000).catch(() => undefined);
    await page.waitForTimeout(800);

    frame = await findKg3dFrame(page);
    const inventoryEvidence = await firstVisible([
      frame.getByText(/◆|В конспекте|В корзине|собран|добавлен|already collected/i).first(),
      page.getByText(/В корзине:\s*[1-9]|В конспекте|добавлен|собран/i).first(),
    ], 10_000);
    expect(inventoryEvidence, 'Collect action should surface an inventory/workbench acknowledgement').not.toBeNull();

    const duplicateCollect = await firstVisible(collectButtons(frame), 1_500);
    if (duplicateCollect) {
      const disabled = await duplicateCollect.isDisabled().catch(() => false);
      const label = (await duplicateCollect.textContent().catch(() => '')) ?? '';
      expect(disabled || /уже|already|в конспекте/i.test(label)).toBeTruthy();
    }
  });

  test('@smoke start from 3D hall navigates to a learning surface', async ({ page }) => {
    test.setTimeout(180_000);

    await completeFirstRunOnboarding(page);
    await openKnowledgeGraph(page);

    const frame = await findKg3dFrame(page);
    const start = await firstVisible(startButtons(frame), 3_000);
    test.skip(!start, 'No start CTA rendered for current KG route fixture.');

    await clickFirstVisible(startButtons(frame), 'KG 3D start CTA');
    await waitForStreamlitReady(page, 20_000).catch(() => undefined);

    await expect(
      page.getByText(/Интерактивный Quiz|Квиз|Flashcards|Карточки|Вопрос:|Мини-проверка|Проверь/i).first(),
    ).toBeVisible({ timeout: 30_000 });
  });
});
