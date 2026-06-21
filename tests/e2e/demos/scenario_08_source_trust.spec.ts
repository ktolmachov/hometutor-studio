import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";

/**
 * Demo scenario #08 — Доверие к ответу: источники и confidence.
 *
 * Снимает 4 кадра по doc/scenarios/scenario_08_source_trust.yaml.
 * Под HOME_RAG_E2E_OFFLINE=1 открывает qa-view, оффлайн-стаб содержит sources.
 *
 * Запуск: npm run test:e2e:demo
 */
test.describe("@demo @smoke scenario_08_source_trust", () => {
  test("@demo @smoke scenario_08_source_trust captures confidence chip → sources → preview → deep link", async ({
    page,
  }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, "scenario_08");

    try {

      // Shot 01 — qa-view с confidence-чипом.
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=qa");
      const input = page.getByRole("textbox").first();
      const hasInput = await input.isVisible({ timeout: DEMO.visibleMs }).catch(() => false);

      const hasLiveLlm = Boolean(process.env.OPENAI_API_KEY);
      if (hasLiveLlm && hasInput) {
        await input.click();
        await input.pressSequentially("Что такое retrieval augmented generation?", { delay: 30 });
        await waitForStreamlitReady(page);
        const submitBtn = page.getByRole("button", { name: /Получить ответ/i }).first();
        await submitBtn.waitFor({ state: "visible", timeout: DEMO.ctaMs });
        await submitBtn.click();
        await page
          .getByText(/E2E offline stub response|offline stub|Stub source/i)
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs });
      }
      await waitForStreamlitReady(page).catch(() => undefined);
      await demo.shot("01_answer_with_confidence_chip", {
        caption: "Ответ + чип «Confidence 87%»",
        narration: "Система сама показывает насколько уверена в ответе.",
        fullPage: true,
        waitMs: 600,
        watermark: "scenario_08 • step_01",
      });

      // Shot 02 — список источников.
      await page.evaluate(() => window.scrollTo(0, 260));
      await demo.shot("02_three_sources_listed", {
        caption: "3 источника с именами файлов и match-score",
        narration: "Каждый источник — с весом релевантности, не просто список.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_08 • step_02",
      });

      // Shot 03 — раскрытый фрагмент источника.
      const sourceExpander = page
        .getByRole("button", { name: /Источник|Source|Фрагмент|Подробнее/i })
        .first();
      if (await sourceExpander.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await sourceExpander.click();
        await waitForStreamlitReady(page);
      }
      await page.evaluate(() => window.scrollTo(0, 520));
      await demo.shot("03_source_preview_expanded", {
        caption: "Фрагмент источника с подсвеченным текстом",
        narration: "Раскрыла источник — видит точный абзац из лекции.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_08 • step_03",
      });

      // Shot 04 — deep link к строке в файле.
      const deepLink = page.getByRole("link", { name: /\.pdf|\.txt|\.md|стр\.|line/i }).first();
      if (await deepLink.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await deepLink.scrollIntoViewIfNeeded();
      }
      await page.evaluate(() => window.scrollTo(0, 740));
      await demo.shot("04_jump_to_file_at_line", {
        caption: "Deep link к строке в исходном файле",
        narration: "Хочет читать полный контекст — один клик до файла.",
        fullPage: false,
        waitMs: 400,
        watermark: "scenario_08 • step_04",
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
