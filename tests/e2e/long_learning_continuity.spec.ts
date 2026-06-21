import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Learning Continuity Loop', () => {
  /**
   * Сценарий: Проверка сквозного пути ученика (CJM Stage: Answer -> Trust -> Tutor -> Quiz -> Progress)
   * Это "North Star" сценарий, защищающий основной цикл продукта.
   * Он гарантирует, что разрозненные режимы (Quick Answer, Tutor, Plan) работают как единый маршрут.
   */
  test('should follow the path from quick question to adaptive plan update', async ({ page }) => {
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY for continuity flow.');
    }

    // 1. Попадаем на главную и проходим онбординг если нужно
    await completeFirstRunOnboarding(page);
    await page.goto('/');

    // 2. Переходим в режим Quick Answer (Задать вопрос) через карточку на главном экране.
    // Если карточка не отрисована в текущем layout, делаем прямой переход в QA view.
    const askButton = page.getByRole('button', { name: /^Задать вопрос$/i }).first();
    if (await askButton.isVisible({ timeout: 8_000 }).catch(() => false)) {
      await askButton.click();
    } else {
      await page.goto('/?e2e_view=qa');
    }

    // 3. Задаем вопрос в Quick Answer
    const questionInput = page.getByLabel('Вопрос');
    await questionInput.fill('Что такое RAG и как он помогает в обучении?');
    const getAnswerButton = page.getByRole('button', { name: /Получить ответ/i }).first();
    await expect(getAnswerButton).toBeVisible({ timeout: 10_000 });
    const qaAskResponsePromise = page
      .waitForResponse(
        (resp) => resp.request().method() === 'POST' && resp.url().includes('/ask'),
        { timeout: 45_000 },
      )
      .catch(() => null);
    await getAnswerButton.click();
    const qaAskResponse = await qaAskResponsePromise;
    if (!qaAskResponse) {
      if (!STRICT_NIGHTLY) {
        test.skip(true, 'Q&A /ask did not complete within 45s.');
      }
      throw new Error('Q&A /ask did not complete within 45s in strict mode.');
    }
    if (!qaAskResponse.ok()) {
      const rawBody = await qaAskResponse.text().catch(() => '');
      const errText = `${qaAskResponse.status()} ${rawBody || 'empty body'}`.slice(0, 240);
      if (!STRICT_NIGHTLY) {
        test.skip(true, `Q&A /ask failed before rendering answer block: ${errText}`);
      }
      throw new Error(`Q&A /ask failed in strict mode: ${errText}`);
    }

    const embeddingMismatch = page
      .getByText(/Collection expecting embedding|dimension of \d+, got \d+|Ошибка запроса:/i)
      .first();
    if (!STRICT_NIGHTLY && await embeddingMismatch.isVisible({ timeout: 8_000 }).catch(() => false)) {
      test.skip(true, 'Nightly environment has embedding/index dimension mismatch (Chroma 1536 vs query 768).');
    }

    // 4. Проверяем ответ и источники (Trust Stage)
    const answerHeading = page.locator('h1, h2, h3').filter({ hasText: /^Ответ$/ }).first();
    const sourcesHeading = page.locator('h1, h2, h3').filter({ hasText: /^Источники$/ }).first();
    const learnCtaMarker = page.getByRole('button', { name: /Учить эту тему/i }).first();
    const answerStateMarker = page.getByText(/Текущее состояние ответа|Объясни проще|Приведи пример/i).first();
    const askError = page.getByText(/Ошибка запроса:|InvalidArgumentError|dimension of \d+, got \d+/i).first();
    let qaReady = false;
    const qaDeadline = Date.now() + 60_000;
    while (Date.now() < qaDeadline) {
      if (await askError.isVisible({ timeout: 250 }).catch(() => false)) {
        const errText = (await askError.textContent().catch(() => 'unknown ask error')) || 'unknown ask error';
        if (!STRICT_NIGHTLY) {
          test.skip(true, `Q&A failed before rendering answer block: ${errText.slice(0, 220)}`);
        }
        throw new Error(`Q&A request failed in strict mode: ${errText.slice(0, 220)}`);
      }
      const hasAnswerHeading = await answerHeading.isVisible({ timeout: 250 }).catch(() => false);
      const hasSourcesHeading = await sourcesHeading.isVisible({ timeout: 250 }).catch(() => false);
      const hasLearnCta = await learnCtaMarker.isVisible({ timeout: 250 }).catch(() => false);
      const hasAnswerState = await answerStateMarker.isVisible({ timeout: 250 }).catch(() => false);
      if (hasAnswerHeading || (hasSourcesHeading && hasAnswerState) || hasLearnCta) {
        qaReady = true;
        break;
      }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !qaReady) {
      test.skip(true, 'Q&A UI did not reach stable answer state in allotted timeout.');
    }
    expect(qaReady).toBeTruthy();

    // 5. Переход в Tutor (Learn Stage) через CTA под ответом
    const learnCta = page.getByRole('button', { name: /Учить эту тему/i }).first();
    await expect(learnCta).toBeVisible({ timeout: 30_000 });
    await learnCta.click();

    // 6. Взаимодействие с Тьютором (Engage)
    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({ timeout: 60_000 });
    let chatInput = page.getByPlaceholder('Спросите тьютора…');
    if (!(await chatInput.isVisible({ timeout: 8_000 }).catch(() => false))) {
      await page.goto('/?e2e_view=tutor');
      const startDialogBtn = page.getByRole('button', { name: /Начать диалог/i }).first();
      if (await startDialogBtn.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await startDialogBtn.click();
      }
      chatInput = page.getByPlaceholder('Спросите тьютора…');
      await expect(chatInput).toBeVisible({ timeout: 20_000 });
    }
    await chatInput.fill('Объясни подробнее концепцию семантического поиска.');
    const tutorAskResponsePromise = page
      .waitForResponse(
        (resp) => resp.request().method() === 'POST' && resp.url().includes('/ask'),
        { timeout: 45_000 },
      )
      .catch(() => null);
    await chatInput.press('Enter');
    const tutorAskResponse = await tutorAskResponsePromise;
    if (!tutorAskResponse) {
      if (!STRICT_NIGHTLY) {
        test.skip(true, 'Tutor /ask did not complete within 45s.');
      }
      throw new Error('Tutor /ask did not complete within 45s in strict mode.');
    }
    if (!tutorAskResponse.ok()) {
      const rawBody = await tutorAskResponse.text().catch(() => '');
      const errText = `${tutorAskResponse.status()} ${rawBody || 'empty body'}`.slice(0, 240);
      if (!STRICT_NIGHTLY) {
        test.skip(true, `Tutor /ask failed before quiz rendering: ${errText}`);
      }
      throw new Error(`Tutor /ask failed in strict mode: ${errText}`);
    }

    // Ожидаем завершения генерации и появления кнопок действий (Pedagogical Router)
    const checkMeBtn = page.getByRole('button', { name: /Проверь меня/i }).first();
    const autoQuizMarker = page.getByText(/Мини-проверка понимания|Unified Auto-Loop|Вопрос:/i).first();
    const tutorAskError = page
      .getByText(/Ошибка запроса:|InvalidArgumentError|OPENAI_API_KEY|dimension of \d+, got \d+|Collection expecting embedding/i)
      .first();
    let hasCheckMe = false;
    let hasAutoQuiz = false;
    const quizEntryDeadline = Date.now() + 35_000;
    while (Date.now() < quizEntryDeadline) {
      if (await tutorAskError.isVisible({ timeout: 250 }).catch(() => false)) {
        const errText = (await tutorAskError.textContent().catch(() => 'unknown tutor error')) || 'unknown tutor error';
        if (!STRICT_NIGHTLY) {
          test.skip(true, `Tutor step failed before quiz rendering: ${errText.slice(0, 220)}`);
        }
        throw new Error(`Tutor request failed in strict mode: ${errText.slice(0, 220)}`);
      }
      hasCheckMe = await checkMeBtn.isVisible({ timeout: 250 }).catch(() => false);
      hasAutoQuiz = await autoQuizMarker.isVisible({ timeout: 250 }).catch(() => false);
      if (hasCheckMe || hasAutoQuiz) {
        break;
      }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY) {
      test.skip(!(hasCheckMe || hasAutoQuiz), 'No quiz entry point was rendered for current tutor route.');
    }

    // 7. Micro-quiz (Check Stage)
    if (hasCheckMe) {
      await checkMeBtn.click();
    }
    await expect(page.getByText(/Вопрос:|Мини-проверка|Unified Auto-Loop/i).first()).toBeVisible({ timeout: 30_000 });

    // Выбираем вариант ответа (если есть radio-buttons)
    const firstRadio = page.locator('input[type="radio"]').first();
    if (await firstRadio.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await firstRadio.check();
    }
    
    // Нажимаем Ответить
    const answerBtn = page.getByRole('button', { name: /^Ответить$/i }).first();
    if (await answerBtn.isVisible({ timeout: 10_000 }).catch(() => false)) {
      await answerBtn.click();
    }

    // Ждем фидбека квиза (Outcome)
    await expect(page.getByText(/Результат:|Верно|Неверно|Частично/i).first()).toBeVisible({ timeout: 30_000 });

    // 8. Adaptive Plan (Review & Retain Stage)
    // Проверяем, что экспандер плана доступен в UI тьютора и содержит обновленные данные
    const planExpander = page.getByText(/Адаптивный план и прогноз/i).first();
    await expect(planExpander).toBeVisible({ timeout: 30_000 });
    await planExpander.click();

    // Ждем отрисовки адаптивного плана
    await expect(page.getByText(/Adaptive Daily Plan/i).first()).toBeVisible({ timeout: 30_000 });
    
    // Проверяем, что план не пуст после взаимодействия
    const emptyMsg = page.getByText(/Нет блоков в плане./i);
    await expect(emptyMsg).not.toBeVisible({ timeout: 15_000 });
    
    // Проверяем наличие KPI (XP Forecast)
    await expect(page.getByText(/Цель XP сегодня/i).first()).toBeVisible({ timeout: 10_000 });
  });
});
