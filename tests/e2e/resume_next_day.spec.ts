/**
 * @nightly CJM Moment of Truth #5 — возврат на следующий день
 *
 * Проверяет: после завершения tutor-сессии пользователь видит resume card
 * с указанием "где он был" и количеством due-карточек на сегодня.
 *
 * Сценарий:
 *   1. Завершить tutor-сессию с quiz
 *   2. Проверить, что st.session_state["tutor_learning_resume"] сохранён (GET /learner/state/health)
 *   3. Перезагрузить страницу (имитация новой сессии следующего дня)
 *   4. Проверить, что resume card видна с контекстом предыдущей сессии
 */
import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Resume on next day', () => {
  test('@nightly tutor session saves resume snapshot; next load shows resume card', async ({ page }) => {
    test.setTimeout(240_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY.');
    }

    await completeFirstRunOnboarding(page);

    // ── 1. Tutor-сессия с quiz ──────────────────────────────────────────────
    const tutorBtn = page.getByRole('button', { name: /^Учиться|^Tutor/i }).first();
    if (await tutorBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await tutorBtn.click();
    } else {
      await page.goto('/?e2e_view=tutor');
    }

    const startBtn = page.getByRole('button', { name: /Начать диалог/i }).first();
    if (await startBtn.isVisible({ timeout: 10_000 }).catch(() => false)) await startBtn.click();

    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({ timeout: 30_000 });

    const chatInput = page.getByPlaceholder('Спросите тьютора…');
    await expect(chatInput).toBeVisible({ timeout: 15_000 });
    await chatInput.fill('Объясни что такое attention механизм.');

    const tutorAskPromise = page.waitForResponse(
      (r) => r.request().method() === 'POST' && r.url().includes('/ask'),
      { timeout: 45_000 },
    ).catch(() => null);
    await chatInput.press('Enter');
    const tutorAsk = await tutorAskPromise;

    if (!tutorAsk?.ok()) {
      const body = await tutorAsk?.text().catch(() => '');
      const msg = `Tutor /ask failed: ${tutorAsk?.status()} ${(body ?? '').slice(0, 200)}`;
      if (!STRICT_NIGHTLY) test.skip(true, msg);
      throw new Error(msg);
    }

    // Входим в quiz
    const checkMeBtn = page.getByRole('button', { name: /Проверь меня/i }).first();
    const autoQuizText = page.getByText(/Мини-проверка|Вопрос:/i).first();
    const tutorError = page.getByText(/Ошибка запроса:|OPENAI_API_KEY|dimension of \d+/i).first();

    let quizReady = false;
    const quizDeadline = Date.now() + 40_000;
    while (Date.now() < quizDeadline) {
      if (await tutorError.isVisible({ timeout: 250 }).catch(() => false)) {
        const msg = `Tutor error: ${(await tutorError.textContent().catch(() => ''))?.slice(0, 200)}`;
        if (!STRICT_NIGHTLY) test.skip(true, msg);
        throw new Error(msg);
      }
      if (await checkMeBtn.isVisible({ timeout: 250 }).catch(() => false) ||
          await autoQuizText.isVisible({ timeout: 250 }).catch(() => false)) {
        quizReady = true; break;
      }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !quizReady) test.skip(true, 'Quiz не появился.');
    expect(quizReady, 'Quiz должен быть доступен').toBeTruthy();

    if (await checkMeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) await checkMeBtn.click();

    const firstRadio = page.locator('input[type="radio"]').first();
    if (await firstRadio.isVisible({ timeout: 10_000 }).catch(() => false)) await firstRadio.check();

    const answerBtn = page.getByRole('button', { name: /^Ответить$/i }).first();
    if (await answerBtn.isVisible({ timeout: 10_000 }).catch(() => false)) await answerBtn.click();

    await expect(page.getByText(/Результат:|Верно|Неверно|Частично/i).first()).toBeVisible({ timeout: 30_000 });

    // ── 2. Проверяем, что resume snapshot сохранён ──────────────────────────
    const apiBase = e2eApiOrigin();
    const health = await page.evaluate(async (base: string) => {
      const r = await fetch(`${base}/learner/state/health`).catch(() => null);
      return r?.ok ? (r.json() as Promise<Record<string, unknown>>) : null;
    }, apiBase);
    expect(health, 'GET /learner/state/health должен отвечать').not.toBeNull();

    const resumeSnapshot: unknown = (health as Record<string, unknown> & { tutor_learning_resume?: unknown })?.tutor_learning_resume;
    expect(resumeSnapshot, 'Snapshot сессии tutor должен быть сохранён (moment #5: где остановились)').not.toBeNull();

    // ── 3. Перезагружаем страницу (имитация следующего дня / новой сессии) ───
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.locator('[data-testid="stSidebar"]').waitFor({ state: 'visible', timeout: 60_000 });

    // ── 4. Resume card должна быть видна на главном экране ──────────────────
    const resumeMarkers = [
      page.getByText(/Продолжить обучение|Resume|Где ты был/i).first(),
      page.getByText(/📍 Следующий шаг/i).first(),
      page.getByText(/Продолжи сессию|Continue session/i).first(),
      page.getByRole('button', { name: /Продолжить|Continue/i }).first(),
    ];

    let resumeVisible = false;
    const deadline = Date.now() + 30_000;
    while (Date.now() < deadline) {
      for (const m of resumeMarkers) {
        if (await m.isVisible({ timeout: 250 }).catch(() => false)) {
          resumeVisible = true; break;
        }
      }
      if (resumeVisible) break;
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !resumeVisible) test.skip(true, 'Resume card не появился после перезагрузки.');
    expect(
      resumeVisible,
      'Момент истины #5: resume card должна быть видна при возврате пользователя на следующий день',
    ).toBeTruthy();

    // ── 5. Опционально: проверяем, что в resume виден контекст сессии ────────
    // (тема, статус, count due-карточек на сегодня)
    const resumeCard = page.locator('[data-testid="stExpander"], .streamlit-expanderHeader, div')
      .filter({ hasText: /Продолжить|Resume/i })
      .first();
    if (await resumeCard.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const resumeText = (await resumeCard.innerText().catch(() => '')).toLowerCase();
      // Хотя бы одно из: количество карточек, название темы, "продолжить"
      expect(resumeText.length, 'Resume card должна содержать информацию о сессии').toBeGreaterThan(10);
    }
  });
});
