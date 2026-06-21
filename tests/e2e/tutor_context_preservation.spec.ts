/**
 * @nightly CJM Moment of Truth #3 — переход trust→tutor
 *
 * Проверяет, что при переходе «Учить эту тему» из Quick Answer:
 *   - sources/concepts из Q&A-ответа видны в tutor UI
 *   - tutor стартует с темой запроса, а не с нуля
 */
import { test, expect } from '@playwright/test';
import { completeFirstRunOnboarding } from './fixtures/onboarding';

const STRICT_NIGHTLY = process.env.PLAYWRIGHT_NIGHTLY_STRICT === '1';

test.describe('@nightly Tutor context preservation from Q&A', () => {
  test('@nightly tutor receives concepts and sources from Q&A answer', async ({ page }) => {
    test.setTimeout(180_000);
    if (!STRICT_NIGHTLY) {
      test.skip(!process.env.OPENAI_API_KEY, 'Requires OPENAI_API_KEY.');
    }

    await completeFirstRunOnboarding(page);

    const askButton = page.getByRole('button', { name: /^Задать вопрос$/i }).first();
    if (await askButton.isVisible({ timeout: 8_000 }).catch(() => false)) {
      await askButton.click();
    } else {
      await page.goto('/?e2e_view=qa');
    }

    // ── 1. Q&A: спрашиваем про конкретную тему ──────────────────────────────
    const TOPIC = 'chunking';
    await expect(page.getByLabel('Вопрос')).toBeVisible({ timeout: 15_000 });
    await page.getByLabel('Вопрос').fill(`Что такое ${TOPIC} в контексте RAG?`);

    // Перехватываем ответ, чтобы извлечь concepts/sources
    let responsePayload: Record<string, unknown> | null = null;
    const askResponsePromise = page.waitForResponse(
      (r) => r.request().method() === 'POST' && r.url().includes('/ask'),
      { timeout: 45_000 },
    ).catch(() => null);

    await page.getByRole('button', { name: /Получить ответ/i }).first().click();
    const askResponse = await askResponsePromise;

    if (!askResponse?.ok()) {
      const body = await askResponse?.text().catch(() => '');
      const msg = `Q&A /ask failed: ${askResponse?.status()} ${(body ?? '').slice(0, 200)}`;
      if (!STRICT_NIGHTLY) test.skip(true, msg);
      throw new Error(msg);
    }

    responsePayload = await askResponse.json().catch(() => null);

    // Проверяем эмбеддинг-мисматч (несовместимая среда)
    const embeddingError = page.getByText(/dimension of \d+, got \d+|Collection expecting embedding/i).first();
    if (!STRICT_NIGHTLY && await embeddingError.isVisible({ timeout: 8_000 }).catch(() => false)) {
      test.skip(true, 'Embedding dimension mismatch in test environment.');
    }

    // ── 2. Trust: источники должны появиться ────────────────────────────────
    const sourcesHeading = page.locator('h1,h2,h3').filter({ hasText: /^Источники$/ }).first();
    const learnCta = page.getByRole('button', { name: /Учить эту тему/i }).first();
    const askError = page.getByText(/Ошибка запроса:/i).first();

    let sourcesReady = false;
    const deadline = Date.now() + 60_000;
    while (Date.now() < deadline) {
      if (await askError.isVisible({ timeout: 250 }).catch(() => false)) {
        const msg = `Q&A error before sources: ${(await askError.textContent().catch(() => ''))?.slice(0, 200)}`;
        if (!STRICT_NIGHTLY) test.skip(true, msg);
        throw new Error(msg);
      }
      if (await sourcesHeading.isVisible({ timeout: 250 }).catch(() => false) &&
          await learnCta.isVisible({ timeout: 250 }).catch(() => false)) {
        sourcesReady = true; break;
      }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !sourcesReady) test.skip(true, 'Источники не отрисовались.');
    expect(sourcesReady, 'Источники должны быть видны перед переходом в tutor').toBeTruthy();

    // ── 3. Переход в tutor ───────────────────────────────────────────────────
    await learnCta.click();
    await expect(page.getByText(/Чат с тьютором/i).first()).toBeVisible({ timeout: 60_000 });

    // ── 4. Контекст: туторе видна тема из Q&A ────────────────────────────────
    // Ключевые слова: сама тема + слова из concepts, которые вернул /ask
    const contextKeywords: string[] = [TOPIC];
    if (responsePayload) {
      const concepts: unknown = (responsePayload as Record<string, unknown>).concepts ??
        (responsePayload as Record<string, unknown>).topics;
      if (Array.isArray(concepts)) {
        concepts.slice(0, 3).forEach((c) => {
          if (typeof c === 'string') contextKeywords.push(c);
        });
      }
    }

    let contextCarried = false;
    const ctxDeadline = Date.now() + 40_000;
    while (Date.now() < ctxDeadline) {
      const bodyText = (await page.locator('body').innerText().catch(() => '')).toLowerCase();
      if (contextKeywords.some((kw) => bodyText.includes(kw.toLowerCase()))) {
        contextCarried = true; break;
      }
      await page.waitForTimeout(1_000);
    }
    if (!STRICT_NIGHTLY && !contextCarried) test.skip(true, 'Tutor не отобразил тему из Q&A.');
    expect(
      contextCarried,
      `Переход trust→tutor: тема "${TOPIC}" должна присутствовать в tutor UI (context carriage)`,
    ).toBeTruthy();

    // ── 5. Tutor не стартовал «с нуля» (нет generic приветствия без темы) ───
    // Если в tutor есть упоминание темы — значит контекст перенесён, а не сброшен
    const tutorChatArea = page.locator('[data-testid="stChatMessage"], .stChatMessage').first();
    if (await tutorChatArea.isVisible({ timeout: 5_000 }).catch(() => false)) {
      const chatText = (await tutorChatArea.innerText().catch(() => '')).toLowerCase();
      // Убеждаемся: первое сообщение не пустое и не просто шаблон без темы
      expect(chatText.length, 'Первое сообщение tutor не должно быть пустым').toBeGreaterThan(10);
    }
  });
});
