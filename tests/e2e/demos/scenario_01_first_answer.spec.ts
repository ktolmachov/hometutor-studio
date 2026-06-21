import { test } from "@playwright/test";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";

/**
 * Demo scenario #01 — Первый запуск: от папки до первого ответа.
 *
 * Сценарий снимает 5 кадров соответствующих doc/scenarios/scenario_01_first_answer.yaml.
 * Под e2e-стеком HOME_RAG_E2E_OFFLINE=1 (см. scripts/e2e_run_stack.mjs) backend
 * отдаёт детерминированный stub-ответ (`app/routers/query.py:50+`). Поэтому поток
 * «ввод → ответ → источники» снимается одинаково и без `OPENAI_API_KEY`.
 *
 * Запуск: npm run test:e2e:demo
 */
test.describe("@demo Scenario 01 — first answer", () => {
  test("@demo captures home → quick answer → sources", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_01");

    try {
      await completeFirstRunOnboarding(page);

      // Shot 01 — Home mode selector: фиксируем стабильный Home.
      let homeReady = false;
      for (let attempt = 1; attempt <= 2; attempt += 1) {
        await gotoAndWaitForStreamlitReady(page, "/");
        homeReady = await Promise.race([
          page
            .locator(".mode-card")
            .first()
            .waitFor({ state: "visible", timeout: DEMO.visibleMs })
            .then(() => true)
            .catch(() => false),
          page
            .getByText(/Обзор тем|Быстрый ответ|К повторению/i)
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
        if (homeReady) {
          break;
        }
        await page.waitForTimeout(300);
      }
      if (!homeReady) {
        throw new Error("Scenario 01: home mode selector did not render");
      }
      await demo.shot("01_home_mode_selector", {
        caption: "Home Mode Selector: 7 карточек режимов",
        narration: "UI встречает семью режимами, а не пустым чатом.",
        waitMs: 800,
        fullPage: true,
      });

      // Переход в Quick Answer через e2e_view, чтобы не зависеть от текста CTA.
      let quickAnswerReady = false;
      for (let attempt = 1; attempt <= 3; attempt += 1) {
        await gotoAndWaitForStreamlitReady(page, "/?e2e_view=qa");
        const input = page.getByRole("textbox").first();
        quickAnswerReady = await input
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false);
        if (quickAnswerReady) {
          break;
        }
        await page.waitForTimeout(300);
      }
      if (!quickAnswerReady) {
        throw new Error("Scenario 01: Quick Answer input did not become visible");
      }
      const input = page.getByRole("textbox").first();
      await input.scrollIntoViewIfNeeded();
      await demo.shot("02_quick_answer_empty", {
        caption: "Быстрый ответ: готов принять вопрос",
        narration: "Аня спрашивает как есть — без магических промптов.",
      });

      await input.click();
      await input.fill("Что такое retrieval augmented generation?");
      await waitForStreamlitReady(page);
      const submitBtn = page.getByRole("button", { name: /Получить ответ/i }).first();
      if (await submitBtn.isVisible({ timeout: DEMO.ctaMs }).catch(() => false)) {
        await submitBtn.click();
      } else {
        await input.press("Enter");
      }
      const answerReady = await Promise.race([
        page
          .getByText(/E2E offline stub response|offline stub|Stub source/i)
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
        page
          .getByText("Ответ", { exact: true })
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
        page
          .getByText("Источники", { exact: true })
          .first()
          .waitFor({ state: "visible", timeout: DEMO.visibleMs })
          .then(() => true)
          .catch(() => false),
      ]);
      if (!answerReady) {
        throw new Error("Scenario 01: answer block did not become visible");
      }
      await waitForStreamlitReady(page);
      await page.getByText("Ответ", { exact: true }).scrollIntoViewIfNeeded();

      await demo.shot("03_quick_answer_with_sources", {
        caption: "Ответ получен: confidence + источники",
        narration:
          "Ответ — с confidence-оценкой и точными фрагментами из её лекций.",
        fullPage: false,
      });

      await page.getByText("Источники", { exact: true }).scrollIntoViewIfNeeded();
      await page.mouse.wheel(0, 420);
      await demo.shot("04_sources_expanded", {
        caption: "Раскрытые источники с превью",
        narration:
          "Никаких галлюцинаций: каждый тезис подкреплён фрагментом.",
        fullPage: false,
      });

      // Shot 05 — CTA «Учить эту тему». Поднимаем кнопку в viewport: это и
      // показывает следующий шаг, и гарантирует отдельный кадр после sources.
      const learnCta = page
        .getByRole("button", { name: /Учить эту тему/i })
        .first();
      await learnCta.waitFor({ state: "visible", timeout: DEMO.ctaMs });
      await learnCta.scrollIntoViewIfNeeded();
      await demo.shot("05_learn_this_topic_cta", {
        caption: "Кнопка «Учить эту тему 5 минут»",
        narration:
          "А если вдруг захотелось разобраться — одна кнопка превращает ответ в учебный разбор.",
        fullPage: false,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
