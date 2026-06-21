import { test } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

test.describe("@demo Scenario 26 — knowledge graph", () => {
  test("@demo captures home KG card → graph view → subgraph → recommendation", async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_26");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/");
      await page.locator('[data-testid="mc-kg-card"]').first().scrollIntoViewIfNeeded();
      await waitForStreamlitReady(page);
      await demo.shot("01_home_kg_card", {
        caption: "Mission Control: карточка Knowledge Graph",
        narration: "Главный экран подсказывает открыть визуальную карту знаний.",
        fullPage: true,
        waitMs: 500,
      });

      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=kg");
      await page.getByText(/Knowledge Graph|подграф|граф/i).first().waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => null);
      await waitForStreamlitReady(page);
      await demo.shot("02_kg_view_open", {
        caption: "Раздел Knowledge Graph открыт",
        narration: "Подграф показывает связи и уровень освоения по узлам.",
        fullPage: true,
        waitMs: 500,
      });

      await page.evaluate(() => window.scrollTo(0, 320));
      await waitForStreamlitReady(page);
      await demo.shot("03_subgraph_mastery", {
        caption: "Персональный подграф + mastery",
        narration: "Видно, какие концепты уже устойчивы, а какие на границе frontier.",
        fullPage: false,
        waitMs: 400,
      });

      await page.getByText(/рекоменда|следующ|weak|mastery/i).first().scrollIntoViewIfNeeded().catch(() => undefined);
      await waitForStreamlitReady(page);
      await demo.shot("04_weak_node_cta", {
        caption: "Рекомендация по слабому узлу",
        narration: "Система предлагает следующий шаг из топологии графа.",
        fullPage: true,
        waitMs: 400,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
