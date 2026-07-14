import { test, type Page } from "@playwright/test";
import { createDemoRecorder } from "../fixtures/demo_recorder";
import { DEMO } from "../fixtures/demo_timeouts";
import { completeFirstRunOnboarding } from "../fixtures/onboarding";
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from "../fixtures/streamlit_ready";

function main(page: Page) {
  return page.locator('[data-testid="stMain"]').first();
}

async function requireVisibleText(page: Page, pattern: RegExp, label: string) {
  const target = main(page).getByText(pattern).first();
  await target.waitFor({ state: "visible", timeout: DEMO.visibleMs }).catch(() => {
    throw new Error(`${label} was not visible. Check that offline demo data contains a living konspekt with this feature.`);
  });
  await target.scrollIntoViewIfNeeded().catch(() => undefined);
  await waitForStreamlitReady(page);
}

async function addFirstSectionToWorkbench(page: Page) {
  const addButton = page.getByRole("button", { name: /^➕$/ }).first();
  await addButton.waitFor({ state: "visible", timeout: DEMO.visibleMs });
  await addButton.click({ timeout: DEMO.visibleMs });
  await page.getByRole("tab", { name: /Читать/i }).waitFor({ state: "visible", timeout: DEMO.visibleMs });
  await waitForStreamlitReady(page);
}

async function openFirstAvailableExpander(page: Page, pattern: RegExp) {
  const expander = page.getByText(pattern).last();
  await expander.waitFor({ state: "visible", timeout: DEMO.visibleMs });
  await expander.scrollIntoViewIfNeeded().catch(() => undefined);
  await expander.click({ timeout: 5_000 }).catch(() => undefined);
  await page.waitForTimeout(500);
}

test.describe("@demo Scenario 37 — конспект: качество и статусы", () => {
  test("@demo captures quality passport, section statuses and counters", async ({ page }) => {
    test.setTimeout(180_000);
    const demo = createDemoRecorder(page, "scenario_37");

    try {
      await completeFirstRunOnboarding(page);
      await gotoAndWaitForStreamlitReady(page, "/?e2e_view=living_konspekt");
      await waitForStreamlitReady(page);
      await addFirstSectionToWorkbench(page);
      await page.getByRole("tab", { name: /Читать/i }).click({ timeout: DEMO.visibleMs });
      await waitForStreamlitReady(page);

      await requireVisibleText(page, /богатый\s*\+\s*рубрика|рубрика/i, "quality passport marker");
      await demo.shot("01_konspekt_quality_passport", {
        caption: "Паспорт качества конспекта",
        narration: "В паспорте раздела видно, что конспект богатый и прошёл рубрику качества.",
        fullPage: true,
        waitMs: 700,
      });

      await openFirstAvailableExpander(page, /Содержимое раздела/i);
      await requireVisibleText(page, /Понял|Сомневаюсь|Не понял/i, "section status controls");
      await demo.shot("02_konspekt_status_controls", {
        caption: "Статусы раздела: понял, сомневаюсь, не понял",
        narration: "После чтения можно зафиксировать состояние знания и оставить вопрос тьютору.",
        fullPage: true,
        waitMs: 700,
      });

      await page.getByRole("button", { name: /Понял/i }).first().click({ timeout: DEMO.visibleMs });
      await page.getByText(/Статус:\s*Понял|В корзине:\s*[1-9]/i).first().waitFor({
        state: "visible",
        timeout: DEMO.visibleMs,
      });
      await page.evaluate(() => window.scrollTo(0, 0));
      await requireVisibleText(page, /В корзине:\s*[1-9]|Статус:\s*Понял|нового для тебя/i, "konspekt status counters");
      await demo.shot("03_konspekt_status_counters", {
        caption: "Счётчики прогресса по конспекту",
        narration: "Система собирает статусы в общий обзор: что закрыто, что сомнительно, где остались вопросы.",
        fullPage: true,
        waitMs: 700,
      });

      await demo.finalize("passed");
    } catch (err) {
      await demo.finalize("failed");
      throw err;
    }
  });
});
