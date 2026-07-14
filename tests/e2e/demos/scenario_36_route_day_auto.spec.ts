import { test, type Frame, type Page } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

async function findFrameWithSelector(page: Page, selector: string, label: string): Promise<Frame> {
  const deadline = Date.now() + DEMO.visibleMs;
  let scannedFrames = 0;
  while (Date.now() < deadline) {
    const frames = page.frames();
    scannedFrames = frames.length;
    for (const frame of frames) {
      const match = frame.locator(selector).first();
      if (await match.count().catch(() => 0)) {
        return frame;
      }
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`${label} not found in any Playwright frame; scanned ${scannedFrames} frame(s).`);
}

test.describe("@demo Scenario 36 — маршрут дня", () => {
  test("@demo captures KG auto day route", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_36");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=kg");
      await page.getByText(/Knowledge Graph|подграф|граф/i).first().waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      }).catch(() => null);
      await waitForStreamlitReady(page);

      const graph = await findFrameWithSelector(page, "#routebtn", "KG route toolbar");
      await graph.locator("#routebtn").click({ timeout: DEMO.visibleMs });
      await graph.locator("#rp-day").click({ timeout: DEMO.visibleMs });
      await graph.locator("#rp-steps").getByText(/Маршрут дня|остановок по ценности/i).first().waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      });
      await waitForStreamlitReady(page);

      await demo.shot("01_route_day_auto", {
        caption: "Knowledge Graph: авто-маршрут дня",
        narration: "Один клик выбирает 4–6 узлов с максимальной учебной ценностью и подсвечивает путь на графе.",
        fullPage: true,
        waitMs: 800,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
