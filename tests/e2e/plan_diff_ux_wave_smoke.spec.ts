import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { waitForStreamlitReady } from './fixtures/streamlit_ready';
import { seedAdaptivePlanConceptsDeltaE2eDb } from './fixtures/plan_diff_e2e_seed';

/**
 * audit group_12 / wave-plan-visibility — US-6.2 expander «Что изменилось в плане»
 * (added/removed concepts), без live LLM.
 */
test.describe('@smoke wave-plan-visibility (group_12)', () => {
  test('@smoke epoch-plan-diff-ux: adaptive plan delta expander lists added and removed concepts', async ({
    page,
  }) => {
    test.setTimeout(180_000);
    seedAdaptivePlanConceptsDeltaE2eDb();
    await completeFirstRunOnboarding(page);
    await page.goto('/?e2e_view=tutor', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 90_000);
    await expect(page.getByText(/Главный режим для обучения/i).first()).toBeVisible({
      timeout: 90_000,
    });

    const planSection = page.getByText(/Адаптивный план и прогноз/i).first();
    await expect(planSection).toBeVisible({ timeout: 30_000 });
    await planSection.click();

    await expect(page.getByText(/Adaptive Daily Plan/i).first()).toBeVisible({ timeout: 15_000 });

    const deltaExpander = page.getByText(/Что изменилось в плане/i).first();
    await expect(deltaExpander).toBeVisible({ timeout: 15_000 });
    await deltaExpander.click();

    await expect(page.getByText(/Появились в шагах/i).first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText(/E2EAlphaDiff/).first()).toBeVisible();
    await expect(page.getByText(/Исчезли из шагов/i).first()).toBeVisible();
    await expect(page.getByText(/E2EBetaDiff/).first()).toBeVisible();
  });
});
