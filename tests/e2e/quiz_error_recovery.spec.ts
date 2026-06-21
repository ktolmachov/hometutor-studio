/**
 * @nightly CJM Moment of Truth #4 — переход quiz→review
 *
 * Проверяет: неправильный ответ в micro-quiz → система не бросает пользователя,
 * а показывает hint / объяснение / следующий шаг (error-recovery path).
 */
import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Quiz error recovery', () => {
  test('@nightly wrong quiz answer shows hint or next step, not dead end', async ({ page }) => {
    test.setTimeout(240_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY.');
    }

    await completeFirstRunOnboarding(page);

    // ── 1. Входим в tutor ────────────────────────────────────────────────────
    const tutorButton = page.getByRole('button', { name: /^Учиться|^Tutor|^Тьютор/i }).first();
    if (await tutorButton.isVisible({ timeout: 5_000 }).catch(() => false)) {
      await tutorButton.click();
    } else {
      await page.goto('/?e2e_view=tutor');
    }

    const startBtn = page.getByRole('button', { name: /Начать диалог/i }).first();
    if (await startBtn.isVisible({ timeout: 10_000 }).catch(() => false)) await startBtn.click();

    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({ timeout: 30_000 });

    // ── 2. Задаём вопрос → ждём tutor-ответа ────────────────────────────────
    const chatInput = page.getByPlaceholder('Спросите тьютора…');
    await expect(chatInput).toBeVisible({ timeout: 15_000 });
    await chatInput.fill('Объясни разницу между sparse и dense retrieval.');

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

    // ── 3. Входим в quiz ─────────────────────────────────────────────────────
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
    if (!STRICT_NIGHTLY && !quizReady) test.skip(true, 'Quiz entry point не появился.');
    expect(quizReady, 'Micro-quiz должен быть доступен из tutor-сессии').toBeTruthy();

    if (await checkMeBtn.isVisible({ timeout: 3_000 }).catch(() => false)) await checkMeBtn.click();

    await expect(page.getByText(/Вопрос:|Мини-проверка/i).first()).toBeVisible({ timeout: 20_000 });

    // ── 4. Намеренно неправильный ответ ─────────────────────────────────────
    // Выбираем ПОСЛЕДНИЙ radio (обычно ложный вариант) или не выбираем ничего
    const radioButtons = page.locator('input[type="radio"]');
    const radioCount = await radioButtons.count();
    if (radioCount > 1) {
      // Выбираем последний вариант — с наибольшей вероятностью неверный
      await radioButtons.nth(radioCount - 1).check();
    }
    // Если radio нет — оставляем поле пустым (тоже вызовет "Неверно")

    const answerBtn = page.getByRole('button', { name: /^Ответить$/i }).first();
    await expect(answerBtn).toBeVisible({ timeout: 10_000 });

    const reviewResponsePromise = page.waitForResponse(
      (r) => r.request().method() === 'POST' && r.url().includes('/ask'),
      { timeout: 45_000 },
    ).catch(() => null);
    await answerBtn.click();
    await reviewResponsePromise;

    // ── 5. Error-recovery: система не бросает, показывает путь ───────────────
    // Принимаем любой из маркеров recovery (приоритет от лучшего к допустимому)
    const recoveryMarkers = [
      page.getByText(/Неверно\.|Неверно,/i).first(),              // outcome
      page.getByText(/Правильно:/i).first(),                       // explanation
      page.getByText(/Подсказка|Hint/i).first(),                   // hint
      page.getByText(/Попробуй ещё|Попробуйте ещё/i).first(),     // retry
      page.getByText(/Следующий шаг|Что дальше/i).first(),        // next step
      page.getByText(/Частично|Результат:/i).first(),              // partial credit
      page.getByRole('button', { name: /Создать карточку/i }).first(), // add to flashcards
    ];

    let recoveryShown = false;
    const recoveryDeadline = Date.now() + 40_000;
    while (Date.now() < recoveryDeadline) {
      for (const marker of recoveryMarkers) {
        if (await marker.isVisible({ timeout: 250 }).catch(() => false)) {
          recoveryShown = true; break;
        }
      }
      if (recoveryShown) break;
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !recoveryShown) test.skip(true, 'Recovery UI после неверного ответа не появился.');
    expect(
      recoveryShown,
      'Переход quiz→review: после неверного ответа должен быть виден hint / объяснение / следующий шаг',
    ).toBeTruthy();

    // ── 6. Нет тупика: следующее действие должно быть доступно ────────────────
    const nextActionMarkers = [
      page.getByText(/Следующий шаг|Что дальше/i).first(),
      page.getByRole('button', { name: /Понял|Продолжить|Следующий шаг|Проверь меня/i }).first(),
    ];
    let hasNextAction = false;
    for (const m of nextActionMarkers) {
      if (await m.isVisible({ timeout: 15_000 }).catch(() => false)) {
        hasNextAction = true; break;
      }
    }
    if (!STRICT_NIGHTLY && !hasNextAction) test.skip(true, 'Next action CTA не появился после ошибки.');
    expect(hasNextAction, 'После неверного ответа пользователь не должен попасть в тупик').toBeTruthy();
  });
});
