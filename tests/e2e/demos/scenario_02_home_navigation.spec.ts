import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

test.describe("@demo Scenario 02 - home navigation", () => {
  test("@demo captures mode selector and transitions", async ({ page }) => {
    test.setTimeout(240_000);
    const demo = createDemoRecorder(page, "scenario_02");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/");
      
      const homeReady = await Promise.race([
        page.locator(".mode-card").first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).then(() => true).catch(() => false),
        page.locator('[data-testid="mission-control-ssr-banner"]').waitFor({ state: "visible", timeout: DEMO.visibleMs }).then(() => true).catch(() => false)
      ]);
      if (!homeReady) {
        throw new Error("Scenario 02: home did not become visible");
      }
      await demo.shot("01_home_initial", {
        caption: "Home screen: mode selector",
        narration: "The first screen shows the main learning modes.",
        fullPage: true,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=topics");
      const topicsReady = await Promise.race([
        page.getByRole("button", { name: /Обновить каталог тем/i }).waitFor({ state: "visible", timeout: DEMO.visibleMs }).then(() => true).catch(() => false),
        page.getByText(/Темы и synthesis/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).then(() => true).catch(() => false),
      ]);
      if (!topicsReady) {
        throw new Error("Scenario 02: topics view did not become visible");
      }
      await page.waitForTimeout(250);
      await demo.shot("02_click_topics", {
        caption: "Topics opened from Home",
        narration: "One click opens the topic overview.",
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=qa");
      await page.locator('[data-testid="e2e-view-switcher"]').first().waitFor({ state: "attached", timeout: DEMO.visibleMs });
      await page.evaluate(() => window.scrollTo(0, 0));
      await page.waitForTimeout(250);
      await demo.shot("03_back_to_home", {
        caption: "Back to the Home header",
        narration: "The section switcher keeps navigation predictable.",
        fullPage: false,
        skipReady: true,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=progress");
      const progressReady = await Promise.race([
        page
          .getByText(/Сводка Progress|Сводка прогресса|Прогресс обучения/i)
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
        page
          .locator('[data-testid="e2e-view-switcher"]')
          .first()
          .waitFor({ state: "attached", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
      ]);
      if (!progressReady) {
        throw new Error("Scenario 02: progress view did not become visible");
      }
      await page.waitForTimeout(250);
      await demo.shot("04_click_progress", {
        caption: "Progress opened from Home",
        narration: "Progress is one click away from the mode selector.",
        fullPage: true,
        skipReady: true,
      });

      // Show the SSR banner instead of the removed secondary tools
      await gotoAndWaitForStreamlitReady(page, "/");
      const ssrBanner = page.locator('[data-testid="mission-control-ssr-banner"]').first();
      await ssrBanner.waitFor({ state: "visible", timeout: DEMO.visibleMs });
      await demo.shot("05_ssr_banner", {
        caption: "SSR Banner on home screen",
        narration: "Smart routing suggests the next best step immediately.",
        fullPage: true,
        skipReady: true,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
