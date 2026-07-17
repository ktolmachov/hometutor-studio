import { test, expect } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { e2eApiOrigin } from "../fixtures/api";
import { findKg3dFrame, openKnowledgeGraph } from "../fixtures/kg3d";

test.describe("@demo Scenario 41 — 3D yesterday trace", () => {
  test("@demo captures quiz trace and snapshot date", async ({ page, request }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_41");

    try {
      const apiBase = e2eApiOrigin();
      const quizRes = await request.post(`${apiBase}/quiz/evaluate`, {
        data: {
          quiz_question: {
            question: "What does retrieval add before generation?",
            options: ["Sources", "Randomness", "Latency only", "Nothing"],
            correct_index: 0,
          },
          user_answer: "A",
          current_topic: "retrieval",
          current_mastery: "intermediate",
          session_id: `demo-kg3d-trace-${Date.now()}`,
        },
        timeout: 30_000,
      });
      expect(quizRes.ok()).toBeTruthy();

      await completeFirstRunOnboarding(page);
      await openKnowledgeGraph(page);
      const frame = await findKg3dFrame(page);
      await frame.getByText(/✓|quiz|квиз|mastery|пройден/i).first()
        .waitFor({ state: "visible", timeout: DEMO.visibleMs })
        .catch(() => undefined);

      await demo.shot("01_quiz_trace", {
        caption: "След quiz-прогресса на маршруте",
        narration: "Пройденная остановка отмечена, а номер маршрута не исчезает под галочкой.",
        fullPage: true,
        waitMs: 800,
      });

      await frame.getByText(/снимок|snapshot|\d{4}-\d{2}-\d{2}/i).first()
        .waitFor({ state: "visible", timeout: DEMO.visibleMs })
        .catch(() => undefined);
      await demo.shot("02_snapshot_date", {
        caption: "Дата снимка прогресса",
        narration: "Зал показывает дату снимка, чтобы старый экспорт оставался честным.",
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
