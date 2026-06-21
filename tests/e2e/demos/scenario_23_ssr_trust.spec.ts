import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 23 — SSR Trust", () => {
  test("@demo captures SSR trust and evidence", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_23");

    try {
      await completeFirstRunOnboarding(page);

      await gotoAndWaitForStreamlitReady(page, "/");
      const ssrBanner = page.locator('[data-testid="mission-control-ssr-banner"]').first();
      await ssrBanner.waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      
      // 01_recommendation_with_reason
      await demo.shot("01_recommendation_with_reason", {
        caption: "SSR показывает следующий шаг и короткую причину",
        narration: "Рекомендация начинается с простого объяснения, привязанного к локальному состоянию.",
        waitMs: 800,
      });

      // 02_evidence_panel
      const whyBtn = page.getByText(/Почему это\?/i).first();
      if (await whyBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await whyBtn.click();
      }
      await waitForStreamlitReady(page);
      await demo.shot("02_evidence_panel", {
        caption: "Evidence Panel: сигналы и альтернативы",
        narration: "Пользователь раскрывает доказательства и видит, почему выбрано именно это действие.",
        waitMs: 800,
      });

      // 03_local_first_trust
      await demo.shot("03_local_first_trust", {
        caption: "Local-first доверие",
        narration: "Все доказательства берутся из локального learner state, без облачного профиля.",
        waitMs: 400,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
