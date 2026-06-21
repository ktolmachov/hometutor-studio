import { test, expect, type Locator, type Page } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { e2eApiOrigin } from './fixtures/api';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { waitForStreamlitReady } from './fixtures/streamlit_ready';

function e2eUserStateDbTargets(dbPath?: string): string[] {
  const root = process.cwd();
  const rawMain =
    dbPath?.trim() ||
    (process.env.USER_STATE_DB ?? '').trim() ||
    path.join(root, '.e2e', 'state-main.db');
  const absMain = path.isAbsolute(rawMain) ? rawMain : path.resolve(root, rawMain);
  const worker0 = (process.env.USER_STATE_DB_0 ?? '').trim();
  const absWorker0 = worker0
    ? path.isAbsolute(worker0)
      ? worker0
      : path.resolve(root, worker0)
    : path.join(root, '.e2e', 'state-0.db');
  return Array.from(new Set([absMain, absWorker0]));
}

/**
 * Сбрасывает flashcards в E2E SQLite. Нельзя полагаться на GET /flashcards/decks при
 * HOME_RAG_E2E_OFFLINE=1 — API отдаёт stub, а Streamlit считает due из реальной БД.
 */
function clearE2eFlashcardStateInDbs(dbPath?: string): void {
  const root = process.cwd();
  const targets = e2eUserStateDbTargets(dbPath);
  const py = resolveRepoPython(root);
  const code = `
import os, sys
sys.path.insert(0, ${JSON.stringify(root)})
from app.user_state import _with_db
for db_path in sys.argv[1].split("|"):
    os.environ["USER_STATE_DB"] = db_path
    def _work(conn):
        conn.execute("DELETE FROM flashcards")
        conn.execute("DELETE FROM flashcard_decks")
        conn.commit()
    _with_db(_work, write=True)
`;
  execFileSync(py, ['-c', code, targets.join('|')], {
    cwd: root,
    stdio: 'inherit',
    env: { ...process.env, USER_STATE_DB: targets[0] },
  });
}

/** MC-баннер: детали в `<details>` — без раскрытия Playwright видит узлы как hidden. */
async function expandMissionControlSsrDetails(banner: Locator): Promise<void> {
  const details = banner.locator('details.ssr-details').first();
  await expect(details).toBeAttached({ timeout: 10_000 });
  const isOpen = await details.evaluate((el) => (el as HTMLDetailsElement).open);
  if (!isOpen) {
    await banner.locator('summary.ssr-details-toggle').click();
  }
  await expect(details).toHaveJSProperty('open', true, { timeout: 10_000 });
}

async function goToMissionControlMain(page: Page): Promise<{ main: Locator; banner: Locator }> {
  const mainLink = page.getByRole('link', { name: /^main$/i });
  if (await mainLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
    await mainLink.click();
  }
  const main = page.locator('[data-testid="stMain"]').first();
  const banner = main.locator('[data-testid="mission-control-ssr-banner"]').first();
  await expect(banner).toBeVisible({ timeout: 90_000 });
  return { main, banner };
}

function resolveRepoPython(root: string): string {
  const fromEnv = (process.env.PYTHON ?? '').trim();
  if (fromEnv) {
    return fromEnv;
  }
  const win = process.platform === 'win32';
  const venv = win
    ? path.join(root, '.venv', 'Scripts', 'python.exe')
    : path.join(root, '.venv', 'bin', 'python3');
  if (fs.existsSync(venv)) {
    return venv;
  }
  return win ? 'python' : 'python3';
}

/** Seeds tutor resume (quiz_failed) + persisted ladder step for offline SSR recovery smoke. */
function seedRecoveryLadderE2eState(step: number, dbPath?: string): void {
  const root = process.cwd();
  const targets = e2eUserStateDbTargets(dbPath);
  const absMain = targets[0];
  const py = resolveRepoPython(root);
  const code = `
import os, sys
sys.path.insert(0, ${JSON.stringify(root)})
from app.user_state import upsert_tutor_learning_resume
from app.learner_model_service import persist_concept_recovery_ladder
step = int(sys.argv[1])
for db_path in sys.argv[2].split("|"):
    os.environ["USER_STATE_DB"] = db_path
    upsert_tutor_learning_resume(
        session_id="e2e-recovery-ladder",
        topic="attention mechanism",
        mastery_level="intermediate",
        last_action_kind="micro_quiz",
        last_action_label="Мини-quiz",
        quiz_feedback={"status": "incorrect", "message": "E2E recovery seed"},
    )
    persist_concept_recovery_ladder(step, concept_anchor="attention mechanism")
`;
  execFileSync(py, ['-c', code, String(step), targets.join('|')], {
    cwd: root,
    stdio: 'inherit',
    env: { ...process.env, USER_STATE_DB: absMain },
  });
}

/**
 * US-20.x: explainable Smart Study Router — на Home через Mission Control banner;
 * на Progress / Flashcards hub — полная карточка `e2e-smart-study-next-step`.
 */
test.describe('@smoke Smart Study Router card', () => {
  test.beforeEach(async () => {
    test.setTimeout(120_000);
  });

  test('@smoke home renders explainable SSR banner (Mission Control)', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    const { banner } = await goToMissionControlMain(page);
    await expect(banner.getByText(/Умный следующий шаг/i)).toBeVisible({ timeout: 10_000 });

    /** «Почему сейчас» текст — в этом же блоке markdown. */
    await expect(banner.getByText(/Почему сейчас/i)).toBeVisible({ timeout: 10_000 });

    await expandMissionControlSsrDetails(banner);

    /** Streamlit санитизирует `data-testid` на этом блоке MC — см. текст заголовка. */
    const whyNot = banner.getByText(/Почему не тьютор\s*\/\s*quiz/i).first();
    await expect(whyNot).toBeVisible({ timeout: 10_000 });
    await expect(whyNot).toContainText(/quiz/i);
    await expect(whyNot).toContainText(/прогресс/i);
    await expect(whyNot).toContainText(/карточ/i);
    await expect(whyNot).toContainText(/тьютор/i);
  });

  /**
   * US-20.6: landmark + причина + контраст + текст о вторичных входах (quiz/progress и др.).
   */
  test('@smoke home SSR banner exposes region landmark, reason, contrast and secondary hints', async ({
    page,
  }) => {
    await completeFirstRunOnboarding(page);

    const { main, banner } = await goToMissionControlMain(page);
    await expect(banner).toHaveAttribute('role', 'region');

    const labelledBy = await banner.getAttribute('aria-labelledby');
    expect(labelledBy, 'SSR banner must reference title id').toBeTruthy();
    await expect(main.getByRole('heading', { name: /Умный следующий шаг/i })).toBeVisible({
      timeout: 10_000,
    });

    await expect(banner.getByText(/Почему сейчас/i)).toBeVisible({ timeout: 10_000 });
    await expandMissionControlSsrDetails(banner);
    await expect(main.getByText(/Контраст с альтернативой/i).first()).toBeVisible({ timeout: 15_000 });

    await expect(
      page.getByText(/Дополнительно:.*quiz.*прогресс/i).first(),
    ).toBeVisible({ timeout: 20_000 });

    await expect(page.getByTestId('mission-tile-quiz').first()).toBeVisible({ timeout: 15_000 });
    await expect(page.getByTestId('mission-tile-flashcards').first()).toBeVisible({ timeout: 15_000 });
  });

  /**
   * US-20.3 / core policies: на поверхности Home виден маршрут cards_due при ненулевой due-очереди (API, без LLM).
   */
  test('@smoke home SSR shows cards_due policy when flashcards are due', async ({ page, request }) => {
    test.setTimeout(120_000);

    await completeFirstRunOnboarding(page);
    const apiBase = e2eApiOrigin();

    const createRes = await request.post(`${apiBase}/flashcards/decks`, {
      timeout: 30_000,
      data: {
        name: `e2e ssr cards_due ${Date.now()}`,
        source_type: 'upload',
        cards: [
          { front: 'SSR Q1', back: 'A1' },
          { front: 'SSR Q2', back: 'A2' },
          { front: 'SSR Q3', back: 'A3' },
          { front: 'SSR Q4', back: 'A4' },
          { front: 'SSR Q5', back: 'A5' },
        ],
      },
    });
    expect(createRes.ok(), `POST /flashcards/decks → ${createRes.status()}`).toBeTruthy();
    const created = (await createRes.json()) as { deck_id?: number };
    const deckId = created.deck_id;
    expect(deckId, 'deck_id from API').toBeDefined();

    try {
      const dueRes = await request.get(`${apiBase}/flashcards/due?limit=10&deck_id=${deckId}`);
      expect(dueRes.ok()).toBeTruthy();
      const dueJson = (await dueRes.json()) as { cards?: unknown[] };
      expect((dueJson.cards ?? []).length).toBeGreaterThan(0);

      await page.goto('/', { waitUntil: 'domcontentloaded' });
      await waitForStreamlitReady(page, 90_000);
      const mainLink = page.getByRole('link', { name: /^main$/i });
      if (await mainLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await mainLink.click();
      }

      const { main, banner } = await goToMissionControlMain(page);
      await expect(banner).toHaveAttribute('data-router-hint', 'cards_due');
      await expandMissionControlSsrDetails(banner);
      /** US-20.9 Learning Debt Queue: педагогическая метка «долг удержания» на маршруте retention. */
      const pedagogy = main.getByTestId('e2e-ssr-route-pedagogy').first();
      await expect(pedagogy).toBeVisible({ timeout: 15_000 });
      await expect(pedagogy).toContainText(/долг удержания|интервальн/i);
      await expect(main.getByRole('button', { name: /^Повторить$/ }).first()).toBeVisible({ timeout: 20_000 });
    } finally {
      await request.delete(`${apiBase}/flashcards/decks/${deckId}`);
    }
  });

  test('@smoke flashcards hub SSR quiet mode keeps primary reason and landmarks', async ({ page }) => {
    /** Quiet: чекбокс рендерится в strip умного следующего шага (хаб Flashcards), не на Mission Control. */
    test.setTimeout(240_000);

    await completeFirstRunOnboarding(page);

    await page.goto('/?e2e_view=flashcards', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 90_000);

    const quiet = page.getByRole('checkbox', { name: /Тихий режим карточки умного следующего шага/i });
    await expect(quiet).toBeAttached({ timeout: 90_000 });
    await quiet.scrollIntoViewIfNeeded();
    await quiet.evaluate((el) => {
      const inp = el as HTMLInputElement;
      if (!inp.checked) {
        inp.click();
      }
    });
    await waitForStreamlitReady(page, 60_000);

    const main = page.locator('[data-testid="stMain"]').first();
    const card = main.locator('[data-testid="e2e-smart-study-next-step"]').first();
    await expect(card).toBeVisible({ timeout: 30_000 });
    await expect(card.getByText(/Умный следующий шаг/i)).toBeVisible();
    /** Заголовок «Почему сейчас» из streaming-блока — отдельный markdown-чанк ниже контейнера карточки. */
    await expect(main.getByText(/Почему сейчас/i).first()).toBeVisible({ timeout: 20_000 });
    /** Primary-кнопка SSR: текст на кнопке; ищем снизу вверх, отсекая навигацию хаба. */
    const primaryRx =
      /Короткая учебная сессия с тьютором|Учить тему|^Повторить$|Повторить концепт|Разобрать слабое место|Следовать шагу плана/i;
    const stripButtons = main.locator('[data-testid="stButton"] button');
    await expect(stripButtons.first()).toBeVisible({ timeout: 25_000 });
    const cnt = await stripButtons.count();
    expect(cnt, 'должен быть хотя бы один виджет кнопки в main').toBeGreaterThan(0);

    let primaryRouterBtn = stripButtons.nth(cnt - 1);
    let matched = false;

    const hubNavRx = /Колоды|Создать|Повторение|^🗂|^✨|^🔁/;
    for (let i = cnt - 1; i >= 0; i -= 1) {
      const b = stripButtons.nth(i);
      const txt = ((await b.textContent()) || '').replace(/\s+/g, ' ').trim();
      if (!txt || hubNavRx.test(txt)) {
        continue;
      }
      if (primaryRx.test(txt)) {
        primaryRouterBtn = b;
        matched = true;
        break;
      }
    }
    if (!matched) {
      for (let i = cnt - 1; i >= 0; i -= 1) {
        const b = stripButtons.nth(i);
        const txt = ((await b.textContent()) || '').replace(/\s+/g, ' ').trim();
        if (txt && !hubNavRx.test(txt)) {
          primaryRouterBtn = b;
          break;
        }
      }
    }
    await expect(primaryRouterBtn).toBeVisible({ timeout: 20_000 });

    /** После quiet: основная кнопка SSR остаётся фокусируемой для клавиатуры/SR-сценариев. */
    await primaryRouterBtn.focus({ timeout: 10_000 });
    await expect(primaryRouterBtn).toBeFocused({ timeout: 15_000 });
  });

  test('@smoke flashcards hub renders explainable next-step card', async ({ page }) => {
    await completeFirstRunOnboarding(page);
    await page.goto('/?e2e_view=flashcards', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 60_000);

    const main = page.locator('[data-testid="stMain"]').first();
    const card = main.locator('[data-testid="e2e-smart-study-next-step"]').first();
    await expect(card).toBeVisible({ timeout: 90_000 });
    await expect(card.getByText(/Умный следующий шаг/i)).toBeVisible({ timeout: 10_000 });
    await expect(main.getByText(/Почему сейчас/i).first()).toBeVisible({ timeout: 20_000 });
    /** Текст why-not может быть разнесён по inline-узлам после санитизации HTML. */
    const whyXPath =
      "//*[contains(normalize-space(.), 'Почему не тьютор') and contains(., 'quiz')]";
    await expect(main.locator(`xpath=${whyXPath}`).first()).toBeVisible({ timeout: 30_000 });
  });

  test('@smoke progress tab renders explainable next-step card', async ({ page }) => {
    await completeFirstRunOnboarding(page);
    await page.goto('/?e2e_view=progress', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 60_000);

    const main = page.locator('[data-testid="stMain"]').first();
    const card = main.locator('[data-testid="e2e-smart-study-next-step"]').first();
    await expect(card).toBeVisible({ timeout: 90_000 });
    await expect(card.getByText(/Умный следующий шаг/i)).toBeVisible({ timeout: 10_000 });
    await expect(main.getByText(/Почему сейчас/i).first()).toBeVisible({ timeout: 20_000 });
    const whyXPath =
      "//*[contains(normalize-space(.), 'Почему не тьютор') and contains(., 'quiz')]";
    await expect(main.locator(`xpath=${whyXPath}`).first()).toBeVisible({ timeout: 30_000 });
  });

  /**
   * US-20.1 / surface parity: при одном session snapshot совпадает `data-router-hint` на Home, Progress и Flashcards hub.
   */
  test('@smoke SSR router hint parity home progress flashcards', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    const { banner: bannerHome } = await goToMissionControlMain(page);
    const hintHome = await bannerHome.getAttribute('data-router-hint');
    expect(hintHome, 'home data-router-hint').toBeTruthy();

    await page.goto('/?e2e_view=progress', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 60_000);
    const cardProg = page.locator('[data-testid="e2e-smart-study-next-step"]').first();
    await expect(cardProg).toBeVisible({ timeout: 90_000 });
    await expect(cardProg).toHaveAttribute('data-router-hint', hintHome!);

    await page.goto('/?e2e_view=flashcards', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 60_000);
    const cardFc = page.locator('[data-testid="e2e-smart-study-next-step"]').first();
    await expect(cardFc).toBeVisible({ timeout: 90_000 });
    await expect(cardFc).toHaveAttribute('data-router-hint', hintHome!);
  });

  /**
   * US-20.10: при cards_due на хабе Flashcards видна группа «локальный руль» (radios рядом с карточкой SSR).
   */
  test('@smoke flashcards hub SSR shows steering controls when cards due', async ({ page, request }) => {
    test.setTimeout(120_000);

    await completeFirstRunOnboarding(page);
    const apiBase = e2eApiOrigin();

    const createRes = await request.post(`${apiBase}/flashcards/decks`, {
      timeout: 30_000,
      data: {
        name: `e2e ssr steer_strip ${Date.now()}`,
        source_type: 'upload',
        cards: [
          { front: 'ST Q1', back: 'A1' },
          { front: 'ST Q2', back: 'A2' },
          { front: 'ST Q3', back: 'A3' },
          { front: 'ST Q4', back: 'A4' },
          { front: 'ST Q5', back: 'A5' },
        ],
      },
    });
    expect(createRes.ok(), `POST /flashcards/decks → ${createRes.status()}`).toBeTruthy();
    const created = (await createRes.json()) as { deck_id?: number };
    const deckId = created.deck_id;
    expect(deckId, 'deck_id from API').toBeDefined();

    try {
      const dueRes = await request.get(`${apiBase}/flashcards/due?limit=10&deck_id=${deckId}`);
      expect(dueRes.ok()).toBeTruthy();
      const dueJson = (await dueRes.json()) as { cards?: unknown[] };
      expect((dueJson.cards ?? []).length).toBeGreaterThan(0);

      await page.goto('/?e2e_view=flashcards', { waitUntil: 'domcontentloaded' });
      await waitForStreamlitReady(page, 90_000);

      const card = page.locator('[data-testid="e2e-smart-study-next-step"]').first();
      await expect(card).toBeVisible({ timeout: 90_000 });
      await expect(card).toHaveAttribute('data-router-hint', 'cards_due');

      const mainPanel = page.locator('[data-testid="stMain"]').first();
      await expect(
        mainPanel.getByText(/Локальный руль следующего шага/i).first(),
      ).toBeVisible({ timeout: 40_000 });
    } finally {
      if (typeof deckId === 'number') {
        await request.delete(`${apiBase}/flashcards/decks/${deckId}`);
      }
    }
  });

  /**
   * US-20.7 + US-20.8: на Home видны контрастное пояснение и блок «Локальные сигналы» (evidence ledger).
   */
  test('@smoke home SSR shows contrastive copy and evidence ledger', async ({ page }) => {
    await completeFirstRunOnboarding(page);

    const { main, banner } = await goToMissionControlMain(page);
    await expandMissionControlSsrDetails(banner);

    const contrast = main.getByText(/Контраст с альтернативой/i).first();
    await expect(contrast).toBeVisible({ timeout: 15_000 });
    await expect(contrast).toContainText(
      /чем|альтернатив|Важнее|Лучше|Недостаточно|Прямого сравнения|Спокойная проверка/i,
    );

    const ledger = main.getByTestId('e2e-ssr-evidence').first();
    await expect(ledger).toBeVisible({ timeout: 15_000 });
    await expect(ledger).toContainText(/Локальные сигналы/i);
    await expect(ledger).toContainText(/не облачн|внешнего профиля/i);
  });

  /**
   * US-20.13: what-if preview shows counterfactual on SSR secondary action click.
   * Full what-if ❓ buttons live on the expandable SSR card (Progress / Flashcards), not Mission Control banner.
   */
  test('@smoke progress SSR card what-if preview shows counterfactual for secondary action', async ({
    page,
  }) => {
    await completeFirstRunOnboarding(page);
    clearE2eFlashcardStateInDbs();
    seedRecoveryLadderE2eState(1);

    await page.goto('/?e2e_view=progress', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 60_000);

    const main = page.locator('[data-testid="stMain"]').first();
    const card = main.locator('[data-testid="e2e-smart-study-next-step"]').first();
    await expect(card).toBeVisible({ timeout: 90_000 });
    await expect(card).toHaveAttribute('data-router-hint', 'quiz_failed');

    /** Emoji «❓» в DOM; hasText точнее getByRole(name) для виджета Streamlit */
    const whatIfBtn = main.locator('button').filter({ hasText: /❓/ }).first();
    await expect(whatIfBtn).toBeVisible({ timeout: 30_000 });
    await whatIfBtn.click();
    await waitForStreamlitReady(page, 90_000);
    await expect(main.locator('button').filter({ hasText: /^✕$/ }).first()).toBeVisible({
      timeout: 30_000,
    });

    const preview = main.getByText(/Что если выбрать/i).first();
    await expect(preview).toBeVisible({ timeout: 30_000 });

    const secondaryBtns = main.getByRole('button').filter({ hasText: /Открыть|Попросить|Создать/i });
    const btnCount = await secondaryBtns.count();
    expect(btnCount).toBeGreaterThanOrEqual(1);
  });
});

test.describe('@smoke Smart Study Router recovery ladder @grep recovery', () => {
  test.beforeEach(async () => {
    test.setTimeout(120_000);
    clearE2eFlashcardStateInDbs();
  });

  test('@smoke progress SSR shows quiz_failed ladder step 1 labels', async ({ page }) => {
    await completeFirstRunOnboarding(page);
    clearE2eFlashcardStateInDbs();
    seedRecoveryLadderE2eState(1);

    await page.goto('/?e2e_view=progress', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 60_000);

    const main = page.locator('[data-testid="stMain"]').first();
    const card = main.locator('[data-testid="e2e-smart-study-next-step"]').first();
    await expect(card).toBeVisible({ timeout: 90_000 });
    await expect(card).toHaveAttribute('data-router-hint', 'quiz_failed');

    const ladderStep = main.locator('[data-testid="e2e-ssr-recovery-ladder-step"]').first();
    await expect(ladderStep).toBeAttached({ timeout: 15_000 });
    await expect(ladderStep).toHaveAttribute('data-recovery-ladder-step', '1');

    await expect(main.getByText(/лестниц[^\n]{0,48}шаг 1|шаг 1[^\n]{0,48}лестниц/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });

  test('@smoke progress SSR reflects persisted ladder step 2', async ({ page }) => {
    await completeFirstRunOnboarding(page);
    clearE2eFlashcardStateInDbs();
    seedRecoveryLadderE2eState(2);

    await page.goto('/?e2e_view=progress', { waitUntil: 'domcontentloaded' });
    await waitForStreamlitReady(page, 60_000);

    const main = page.locator('[data-testid="stMain"]').first();
    const ladderStep = main.locator('[data-testid="e2e-ssr-recovery-ladder-step"]').first();
    await expect(ladderStep).toBeAttached({ timeout: 90_000 });
    await expect(ladderStep).toHaveAttribute('data-recovery-ladder-step', '2');
    await expect(main.getByText(/шаг 2 лестницы восстановления/i).first()).toBeVisible({
      timeout: 15_000,
    });
  });
});
