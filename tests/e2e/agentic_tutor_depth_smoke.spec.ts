import { test, expect, type Page } from "@playwright/test";
import { waitForStreamlitReady } from "./fixtures/streamlit_ready";
import { completeFirstRunOnboarding } from "./fixtures/onboarding";

/**
 * audit group_09 / wave-agentic-tutor-depth — видимые поверхности плана (gap/routing)
 * и подсказок по шагам разбора (remediation CTA copy), без live LLM.
 * Якорь готовности: шапка tutor tab (subtitle из tutor_chat_intro), без st.chat_input
 * (он внизу длинной страницы и в CI может не попадать во viewport).
 */

async function openTutorView(page: Page): Promise<void> {
  await completeFirstRunOnboarding(page);
  await page.goto("/?e2e_view=tutor", { waitUntil: "domcontentloaded" });
  await waitForStreamlitReady(page, 90_000);
  await expect(page.getByText(/Главный режим для обучения/i).first()).toBeVisible({
    timeout: 90_000,
  });
}

test.describe("@smoke wave-agentic-tutor-depth (group_09)", () => {
  test("@smoke epoch-mastery-gap-routing: tutor shows adaptive plan expander with recalc control", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await openTutorView(page);

    const planExpander = page.getByText(/Адаптивный план и прогноз/i).first();
    await expect(planExpander).toBeVisible({ timeout: 30_000 });
    await planExpander.click();

    await expect(page.getByText(/Adaptive Daily Plan/i).first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("button", { name: /Пересчитать план/i }).first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test("@smoke epoch-concept-remediation-step: tutor intro lists remediation quick-action verbs", async ({
    page,
  }) => {
    test.setTimeout(180_000);
    await openTutorView(page);

    const remediationHint = page.getByText(
      /Объясни проще|Дай пример|Проверь меня|Следующий шаг/i,
    );
    await expect(remediationHint.first()).toBeVisible({ timeout: 30_000 });
  });
});
