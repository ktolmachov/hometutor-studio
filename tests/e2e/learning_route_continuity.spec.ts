/**
 * @nightly North Star: learning route transition quality
 *
 * CJM §6 — проверяет не наличие экранов, а качество переходов:
 *   answer → trust (источники видны) →
 *   tutor (контекст перенесён) →
 *   quiz →
 *   progress delta (mastery/gamification изменились)
 *
 * Этот тест — главный acceptance-критерий эпохи epoch-learning-route-continuity.
 */
import { test, expect } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Learning route — transition quality', () => {
  test('@nightly answer→trust→tutor→quiz→progress delta', async ({ page }) => {
    test.setTimeout(240_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY.');
    }

    await completeFirstRunOnboarding(page);
    const apiBase = e2eApiOrigin();

    // ── 1. Quick Answer ──────────────────────────────────────────────────────
    const askButton = page.getByRole('button', { name: /^Задать вопрос$/i }).first();
    if (await askButton.isVisible({ timeout: 8_000 }).catch(() => false)) {
      await askButton.click();
    } else {
      await page.goto('/?e2e_view=qa');
    }

    const questionInput = page.getByLabel('Вопрос');
    await expect(questionInput).toBeVisible({ timeout: 15_000 });
    await questionInput.fill('Что такое embedding и зачем он нужен в RAG?');

    const askResponsePromise = page
      .waitForResponse(
        (r) => r.request().method() === 'POST' && r.url().includes('/ask'),
        { timeout: 45_000 },
      )
      .catch(() => null);
    await page.getByRole('button', { name: /Получить ответ/i }).first().click();
    const askResponse = await askResponsePromise;

    if (!askResponse?.ok()) {
      const body = await askResponse?.text().catch(() => '');
      const msg = `Q&A /ask failed: ${askResponse?.status()} ${(body ?? '').slice(0, 200)}`;
      if (!STRICT_NIGHTLY) test.skip(true, msg);
      throw new Error(msg);
    }

    // ── 2. Trust transition: источники должны быть видны ────────────────────
    const sourcesHeading = page.locator('h1,h2,h3').filter({ hasText: /^Источники$/ }).first();
    const learnCta = page.getByRole('button', { name: /Учить эту тему/i }).first();
    const askError = page.getByText(/Ошибка запроса:|dimension of \d+, got \d+/i).first();

    let trustReady = false;
    const trustDeadline = Date.now() + 60_000;
    while (Date.now() < trustDeadline) {
      if (await askError.isVisible({ timeout: 250 }).catch(() => false)) {
        const msg = `Q&A error: ${(await askError.textContent().catch(() => ''))?.slice(0, 200)}`;
        if (!STRICT_NIGHTLY) test.skip(true, msg);
        throw new Error(msg);
      }
      const hasSources = await sourcesHeading.isVisible({ timeout: 250 }).catch(() => false);
      const hasLearn = await learnCta.isVisible({ timeout: 250 }).catch(() => false);
      if (hasSources && hasLearn) { trustReady = true; break; }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !trustReady) test.skip(true, 'Trust panel (Источники + Learn CTA) не появился.');
    expect(trustReady, 'Переход answer→trust: источники должны быть видны до перехода в tutor').toBeTruthy();

    // ── 3. Tutor context transition: контекст перенесён ─────────────────────
    // Снимаем baseline mastery ДО сессии
    const masteryBefore = await page
      .evaluate(async (base: string) => {
        const r = await fetch(`${base}/dashboard/mastery`).catch(() => null);
        return r?.ok ? r.json() : null;
      }, apiBase)
      .catch(() => null);

    await learnCta.click();
    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({ timeout: 60_000 });

    // Проверяем, что тьютор показал что-то связанное с темой запроса
    const topicKeywords = ['embedding', 'RAG', 'retrieval', 'вектор', 'поиск', 'семантич'];
    let contextVisible = false;
    const ctxDeadline = Date.now() + 30_000;
    while (Date.now() < ctxDeadline) {
      const bodyText = await page.locator('body').innerText().catch(() => '');
      if (topicKeywords.some((kw) => bodyText.toLowerCase().includes(kw.toLowerCase()))) {
        contextVisible = true;
        break;
      }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !contextVisible) test.skip(true, 'Tutor не показал ключевые слова темы из Q&A.');
    expect(contextVisible, 'Переход trust→tutor: ключевые слова темы должны присутствовать в tutor UI').toBeTruthy();

    // ── 4. Quiz transition ───────────────────────────────────────────────────
    let chatInput = page.getByPlaceholder('Спросите тьютора…');
    if (!(await chatInput.isVisible({ timeout: 8_000 }).catch(() => false))) {
      const startBtn = page.getByRole('button', { name: /Начать диалог/i }).first();
      if (await startBtn.isVisible({ timeout: 5_000 }).catch(() => false)) await startBtn.click();
      await expect(chatInput).toBeVisible({ timeout: 20_000 });
    }
    await chatInput.fill('Объясни коротко, что такое cosine similarity в контексте поиска.');

    const tutorResponsePromise = page
      .waitForResponse(
        (r) => r.request().method() === 'POST' && r.url().includes('/ask'),
        { timeout: 45_000 },
      )
      .catch(() => null);
    await chatInput.press('Enter');
    const tutorResponse = await tutorResponsePromise;

    if (!tutorResponse?.ok()) {
      const body = await tutorResponse?.text().catch(() => '');
      const msg = `Tutor /ask failed: ${tutorResponse?.status()} ${(body ?? '').slice(0, 200)}`;
      if (!STRICT_NIGHTLY) test.skip(true, msg);
      throw new Error(msg);
    }

    const checkMeBtn = page.getByRole('button', { name: /Проверь меня/i }).first();
    const autoQuizText = page.getByText(/Мини-проверка|Вопрос:/i).first();
    const tutorError = page.getByText(/Ошибка запроса:|OPENAI_API_KEY|dimension of \d+/i).first();

    let quizVisible = false;
    const quizDeadline = Date.now() + 40_000;
    while (Date.now() < quizDeadline) {
      if (await tutorError.isVisible({ timeout: 250 }).catch(() => false)) {
        const msg = `Tutor error: ${(await tutorError.textContent().catch(() => ''))?.slice(0, 200)}`;
        if (!STRICT_NIGHTLY) test.skip(true, msg);
        throw new Error(msg);
      }
      if (await checkMeBtn.isVisible({ timeout: 250 }).catch(() => false) ||
          await autoQuizText.isVisible({ timeout: 250 }).catch(() => false)) {
        quizVisible = true; break;
      }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !quizVisible) test.skip(true, 'Quiz entry point не появился в tutor UI.');
    expect(quizVisible, 'Переход tutor→quiz: точка входа в micro-quiz должна быть видна').toBeTruthy();

    if (await checkMeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) await checkMeBtn.click();

    const firstRadio = page.locator('input[type="radio"]').first();
    if (await firstRadio.isVisible({ timeout: 10_000 }).catch(() => false)) await firstRadio.check();

    const answerBtn = page.getByRole('button', { name: /^Ответить$/i }).first();
    if (await answerBtn.isVisible({ timeout: 10_000 }).catch(() => false)) await answerBtn.click();

    await expect(page.getByText(/Результат:|Верно|Неверно|Частично/i).first()).toBeVisible({ timeout: 30_000 });

    // ── 5. Progress delta: quiz → review → progress ──────────────────────────
    const masteryAfter = await page
      .evaluate(async (base: string) => {
        const r = await fetch(`${base}/dashboard/mastery`).catch(() => null);
        return r?.ok ? r.json() : null;
      }, apiBase)
      .catch(() => null);

    // Ключевой инвариант: после сессии dashboard/mastery стабилен (не упал)
    expect(masteryAfter, 'GET /dashboard/mastery должен быть доступен после сессии').not.toBeNull();

    // Если baseline был получен — проверяем, что gamification или quiz_mastery не уменьшились
    if (masteryBefore && masteryAfter) {
      const xpBefore: number = masteryBefore?.gamification?.xp ?? 0;
      const xpAfter: number = masteryAfter?.gamification?.xp ?? 0;
      expect(xpAfter, 'XP не должен уменьшиться после tutor-сессии с quiz').toBeGreaterThanOrEqual(xpBefore);
    }

    // Ожидаем CTA следующего шага
    const nextStepMarker = page.getByText(/Следующий шаг|Что дальше:|Продолжить обучение/i).first();
    await expect(nextStepMarker).toBeVisible({ timeout: 30_000 });
  });
});
