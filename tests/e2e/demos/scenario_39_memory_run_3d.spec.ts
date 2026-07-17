import { test, expect } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { canvasHasNonBlankPixels, findKg3dFrame, openKnowledgeGraph } from "../fixtures/kg3d";

test.describe("@demo Scenario 39 — Memory Run 3D", () => {
  test("@demo captures embedded 3D Memory Run hall", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_39");

    try {
      await completeFirstRunOnboarding(page);
      await openKnowledgeGraph(page);
      const frame = await findKg3dFrame(page);
      await expect(frame.locator("canvas").first()).toBeVisible({ timeout: DEMO.visibleMs });
      expect(await canvasHasNonBlankPixels(frame)).toBeTruthy();

      await demo.shot("01_memory_run_hall", {
        caption: "Memory Run: маршрут дня в 3D-зале",
        narration: "3D-зал открывается сразу на маршруте: видно, какая остановка первая и почему она важна.",
        fullPage: true,
        waitMs: 800,
      });

      await frame.locator("#side, aside, .kgx-side").first().scrollIntoViewIfNeeded().catch(() => undefined);
      await demo.shot("02_stop_value_card", {
        caption: "Карточка ценности остановки",
        narration: "Узел показывает роль, ценность, mastery и доступные действия без отдельной легенды.",
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
