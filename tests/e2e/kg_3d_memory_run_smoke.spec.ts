import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import {
  canvasHasNonBlankPixels,
  findKg3dFrame,
  firstVisible,
  openKnowledgeGraph,
  startButtons,
  collectButtons,
} from './fixtures/kg3d';

test.describe('@smoke KG 3D Memory Run', () => {
  test('@smoke embedded 3D hall renders route-first Memory Run UI', async ({ page }) => {
    test.setTimeout(180_000);

    await completeFirstRunOnboarding(page);
    await openKnowledgeGraph(page);

    const frame = await findKg3dFrame(page);
    await expect(frame.locator('canvas').first()).toBeVisible({ timeout: 30_000 });
    expect(await canvasHasNonBlankPixels(frame), '3D hall canvas should not be blank').toBeTruthy();

    await expect(frame.locator('#topbar, [data-testid="kg3d-topbar"], .kgx-topbar').first()).toBeVisible({
      timeout: 30_000,
    });
    await expect(frame.locator('#side, aside, [data-testid="kg3d-side"], .kgx-side').first()).toBeVisible({
      timeout: 30_000,
    });

    const routeEvidence = await firstVisible([
      frame.locator('.stop-index, [data-stop-index], .stop-rank').first(),
      frame.getByText(/Стоп\s*\d+|Stop\s*\d+|\d+\s*\/\s*\d+|Маршрут|route/i).first(),
    ]);
    expect(routeEvidence, 'Route stop number/rank should be visible').not.toBeNull();

    const actionEvidence = await firstVisible([...startButtons(frame), ...collectButtons(frame)]);
    expect(actionEvidence, 'At least one product action CTA should be visible in embedded hall').not.toBeNull();
  });
});
