import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { e2eApiOrigin } from './fixtures/api';
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from './fixtures/streamlit_ready';

test.describe('@smoke Agent one-button gate', () => {
  test('@smoke agent mode API is gated without server errors', async ({ request }) => {
    const apiBase = e2eApiOrigin();
    const res = await request.post(`${apiBase}/ask`, {
      data: {
        question: 'Build a short study plan for retrieval practice.',
        query_mode: 'agent',
      },
      timeout: 60_000,
    });

    expect(res.status(), 'agent query_mode must not crash the API').toBeLessThan(500);
    if (res.ok()) {
      const body = (await res.json()) as Record<string, unknown>;
      const debug = body.debug as Record<string, unknown> | undefined;
      expect(String(debug?.query_mode ?? body.query_mode ?? 'agent')).toMatch(/agent/i);
      expect(JSON.stringify(body)).toMatch(/agent|trace|scenario|tool|plan/i);
    }
  });

  test('@smoke agent tile is either hidden by gate or opens an agent surface', async ({ page }) => {
    test.setTimeout(120_000);

    await completeFirstRunOnboarding(page);
    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=home');

    const agentTile = page.locator('[data-testid="mission-tile-agent"]').first();
    const visibleTile = await agentTile.isVisible({ timeout: 8_000 }).catch(() => false);
    if (!visibleTile) {
      await expect(page.getByText(/Traceback|StreamlitAPIException|Exception:/i)).toHaveCount(0);
      return;
    }

    await agentTile.click({ timeout: 10_000 });
    await waitForStreamlitReady(page, 15_000).catch(() => undefined);
    await expect(page.getByText(/Agent|агент|trace|scenario|tool/i).first()).toBeVisible({ timeout: 30_000 });
  });
});
