import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { clickFirstVisible, collectButtons, findKg3dFrame, openKnowledgeGraph } from "../fixtures/kg3d";

test.describe("@demo Scenario 40 — 3D collect to konspekt", () => {
  test("@demo captures collect action and inventory acknowledgement", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_40");

    try {
      await completeFirstRunOnboarding(page);
      await openKnowledgeGraph(page);
      let frame = await findKg3dFrame(page);

      await demo.shot("01_collect_action", {
        caption: "Действие «В конспект» в 3D-зале",
        narration: "Остановка маршрута предлагает собрать связанные разделы в Живой конспект.",
        fullPage: true,
        waitMs: 800,
      });

      await clickFirstVisible(collectButtons(frame), "KG 3D collect CTA", DEMO.visibleMs);
      await waitForStreamlitReady(page, 20_000).catch(() => undefined);
      frame = await findKg3dFrame(page);
      await frame.getByText(/◆|В конспекте|В корзине|собран|добавлен/i).first()
        .waitFor({ state: "visible", timeout: DEMO.visibleMs })
        .catch(() => undefined);

      await demo.shot("02_inventory_ack", {
        caption: "Инвентарь обновлён",
        narration: "После подтверждения продукт возвращает обновлённый счётчик и маркер собранного узла.",
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
