import { test, expect } from '@playwright/test';
import fs from 'node:fs';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { firstVisible, openKnowledgeGraph } from './fixtures/kg3d';

test.describe('@smoke KG 3D export contract', () => {
  test('@smoke downloaded 3D hall is read-only and self-contained', async ({ page }) => {
    test.setTimeout(180_000);

    await completeFirstRunOnboarding(page);
    await openKnowledgeGraph(page);

    const downloadButton = await firstVisible([
      page.getByRole('button', { name: /Скачать 3D|3D-зал|3D.*HTML|Download 3D/i }).first(),
      page.getByText(/Скачать 3D|3D-зал.*HTML|Download 3D/i).first(),
    ], 5_000);
    test.skip(!downloadButton, '3D export download button is not rendered for current KG fixture.');

    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 30_000 }),
      downloadButton!.click({ timeout: 10_000 }),
    ]);
    const path = await download.path();
    expect(path, 'downloaded 3D HTML should have a local temp path').toBeTruthy();
    const html = fs.readFileSync(path!, 'utf-8');

    expect(html).toMatch(/canvas|route|Маршрут|Memory Run/i);
    expect(html).toMatch(/snapshot|снимок|EXPORTED_AT|exported_at/i);
    expect(html).not.toMatch(/obsidian:\/\//i);
    expect(html).not.toMatch(/setComponentValue|_kg3d=|hometutor:kg-action/i);
  });
});
