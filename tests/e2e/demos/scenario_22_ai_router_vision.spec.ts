import { test, expect } from '@playwright/test';
import type { Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { createDemoRecorder } from '../fixtures/demo_recorder';
import { DEMO } from '../fixtures/demo_timeouts';

function assetDataUri(relativePath: string): string {
  const abs = path.resolve(process.cwd(), relativePath);
  const bytes = fs.readFileSync(abs);
  return `data:image/png;base64,${bytes.toString('base64')}`;
}

const routerVisual = assetDataUri(
  'doc/screenshots/mastery_engine/mastery_engine_slide_06.png',
);

function aiVisionStoryboardHtml(): string {
  return `<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8" />
    <title>SSR AI Vision storyboard</title>
    <style>
      :root {
        color-scheme: light;
        font-family: Inter, "Segoe UI", Arial, sans-serif;
        background: #f8faf7;
        color: #142019;
      }
      body {
        margin: 0;
        background:
          linear-gradient(120deg, rgba(219, 240, 232, .72), rgba(255, 250, 239, .92)),
          #f8faf7;
      }
      .stage {
        min-height: 100vh;
        padding: 44px 56px;
        box-sizing: border-box;
      }
      .eyebrow {
        color: #31533d;
        font-size: 18px;
        font-weight: 800;
        letter-spacing: .08em;
        text-transform: uppercase;
      }
      h1 {
        margin: 14px 0 18px;
        font-size: 58px;
        line-height: 1.02;
        max-width: 980px;
      }
      h2 {
        margin: 0 0 22px;
        font-size: 44px;
        line-height: 1.08;
      }
      p {
        font-size: 22px;
        line-height: 1.42;
        max-width: 880px;
      }
      .hero-grid {
        display: grid;
        grid-template-columns: 1.05fr .95fr;
        gap: 36px;
        align-items: center;
      }
      .hero-img {
        width: 100%;
        border-radius: 8px;
        box-shadow: 0 24px 60px rgba(49, 83, 61, .20);
      }
      .rail {
        display: grid;
        gap: 14px;
        margin-top: 28px;
      }
      .signal {
        border-left: 8px solid #317f65;
        background: rgba(255, 255, 255, .76);
        padding: 16px 18px;
        border-radius: 8px;
        font-size: 22px;
        font-weight: 760;
      }
      .levels {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 16px;
        margin-top: 34px;
      }
      .level {
        min-height: 250px;
        background: #ffffff;
        border: 2px solid #d6e2da;
        border-radius: 8px;
        padding: 18px;
        box-shadow: 0 18px 40px rgba(44, 67, 52, .12);
      }
      .num {
        display: inline-grid;
        place-items: center;
        width: 42px;
        height: 42px;
        border-radius: 50%;
        background: #1f6f5b;
        color: white;
        font-weight: 900;
        margin-bottom: 18px;
      }
      .level h3 {
        margin: 0 0 10px;
        font-size: 24px;
        line-height: 1.1;
      }
      .level p {
        margin: 0;
        font-size: 18px;
      }
      .compare {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 26px;
        margin-top: 28px;
      }
      .panel {
        background: white;
        border-radius: 8px;
        padding: 24px;
        min-height: 330px;
        box-shadow: 0 18px 42px rgba(44, 67, 52, .13);
        border-top: 8px solid #a85b33;
      }
      .panel.ai {
        border-top-color: #1f6f5b;
      }
      .quote {
        font-size: 25px;
        line-height: 1.35;
        font-weight: 780;
      }
      .caption {
        margin-top: 24px;
        font-size: 19px;
        color: #4d5f54;
      }
      .feedback {
        display: grid;
        grid-template-columns: .9fr 1.1fr;
        gap: 28px;
        align-items: stretch;
      }
      .loop {
        background: #203529;
        color: #f8fff9;
        border-radius: 8px;
        padding: 28px;
      }
      .loop div {
        font-size: 28px;
        font-weight: 850;
        margin: 22px 0;
      }
      .metrics {
        display: grid;
        gap: 14px;
      }
      .metric {
        background: #ffffff;
        border-radius: 8px;
        padding: 18px;
        border-left: 8px solid #1f6f5b;
        font-size: 22px;
        font-weight: 760;
      }
    </style>
  </head>
  <body>
    <section class="stage" data-shot="overview">
      <div class="hero-grid">
        <div>
          <div class="eyebrow">Smart Study Router · AI Vision</div>
          <h1>От жёстких правил к персональному учебному проводнику</h1>
          <p>Базовый SSR остаётся объяснимым policy engine. AI-уровни добавляются поверх него: локальная память, живое объяснение, недельный план, граф prerequisites и feedback loop.</p>
          <div class="rail">
            <div class="signal">Правила принимают решение предсказуемо</div>
            <div class="signal">ML персонализирует приоритеты локально</div>
            <div class="signal">LLM объясняет, но не ломает маршрут</div>
          </div>
        </div>
        <img class="hero-img" src="${routerVisual}" alt="Smart Study Router visual" />
      </div>
    </section>

    <section class="stage" data-shot="levels12">
      <h2>Уровни 1–2: память конкретного человека + объяснение человеческим языком</h2>
      <div class="compare">
        <div class="panel">
          <div class="eyebrow">Версия 2.0</div>
          <p class="quote">«Повторить 5 карточек. Почему: очередь SM-2 наступила сегодня.»</p>
          <p class="caption">Надёжно, объяснимо, local-first. Но одинаково для всех.</p>
        </div>
        <div class="panel ai">
          <div class="eyebrow">AI Vision · Levels 1–2</div>
          <p class="quote">«Повторите 3 карточки сейчас: ваша кривая забывания показывает риск провала через 36 часов. Остальные 2 лучше оставить на вечер.»</p>
          <p class="caption">ML меняет приоритет, LLM превращает причину в понятный совет.</p>
        </div>
      </div>
    </section>

    <section class="stage" data-shot="levels34">
      <h2>Уровни 3–4: недельный план + граф prerequisites</h2>
      <div class="levels">
        <div class="level"><span class="num">1</span><h3>Local ML</h3><p>Предсказывает риск забывания по quiz и review history.</p></div>
        <div class="level"><span class="num">2</span><h3>LLM Explanation</h3><p>Пишет понятное «почему сейчас», decision остаётся rule-safe.</p></div>
        <div class="level"><span class="num">3</span><h3>Weekly Planner</h3><p>Собирает неделю из целей, времени и weak spots.</p></div>
        <div class="level"><span class="num">4</span><h3>Concept Graph</h3><p>Не даёт перейти к сложной теме раньше базовой.</p></div>
        <div class="level"><span class="num">5</span><h3>Feedback Loop</h3><p>Учит роутер на отклонённых рекомендациях.</p></div>
      </div>
    </section>

    <section class="stage" data-shot="feedback">
      <div class="feedback">
        <div class="loop">
          <div>Рекомендация</div>
          <div>→ Действие пользователя</div>
          <div>→ Feedback signal</div>
          <div>→ Новая стратегия</div>
        </div>
        <div class="metrics">
          <div class="metric">+15% выполнение повторений · цель Level 1</div>
          <div class="metric">+0.8 балла понятности · цель Level 2</div>
          <div class="metric">+15% выполнение плана · цель Level 3</div>
          <div class="metric">-20% нарушений последовательности · цель Level 4</div>
          <div class="metric">+15% принятие рекомендаций · цель Level 5</div>
        </div>
      </div>
    </section>
  </body>
</html>`;
}

async function scrollToShot(page: Page, name: string): Promise<void> {
  const section = page.locator(`[data-shot="${name}"]`).first();
  await expect(section).toBeVisible({ timeout: DEMO.visibleMs });
  await section.evaluate((element: HTMLElement) => {
    element.scrollIntoView({ block: 'start', inline: 'nearest' });
  });
  await page.waitForTimeout(250);
}

/**
 * Demo scenario #22 — SSR AI Vision concept storyboard.
 *
 * Запуск: npm run test:e2e:demo -- --grep "@demo Scenario 22"
 */
test.describe('@demo Scenario 22 — SSR AI Vision', () => {
  test('@demo captures five-level AI Vision storyboard', async ({ page }) => {
    test.setTimeout(DEMO.testTimeoutMs);
    const demo = createDemoRecorder(page, 'scenario_22');

    try {
      await page.setViewportSize({ width: 1400, height: 900 });
      await page.setContent(aiVisionStoryboardHtml(), { waitUntil: 'domcontentloaded' });

      await scrollToShot(page, 'overview');
      await demo.shot('01_ai_vision_overview', {
        caption: 'AI Vision: от правил к персональному проводнику',
        narration:
          'Базовый SSR остаётся страховочной сеткой, а AI-уровни добавляются поверх него.',
        fullPage: false,
        skipReady: true,
        watermark: 'scenario_22 • AI Vision',
      });

      await scrollToShot(page, 'levels12');
      await demo.shot('02_levels_1_2_personal_memory', {
        caption: 'Уровни 1–2: локальная память + живое объяснение',
        narration:
          'ML меняет приоритеты по кривой забывания, LLM объясняет решение человеческим языком.',
        fullPage: false,
        skipReady: true,
        watermark: 'scenario_22 • Levels 1-2',
      });

      await scrollToShot(page, 'levels34');
      await demo.shot('03_levels_3_4_planner_graph', {
        caption: 'Уровни 3–4: недельный план + граф prerequisites',
        narration:
          'Система ведёт дальше одного клика и не предлагает сложную тему раньше базовой.',
        fullPage: false,
        skipReady: true,
        watermark: 'scenario_22 • Levels 3-4',
      });

      await scrollToShot(page, 'feedback');
      await demo.shot('04_level_5_feedback_loop', {
        caption: 'Уровень 5: feedback loop',
        narration:
          'Если пользователь отклоняет рекомендации, стратегия меняется и остаётся объяснимой.',
        fullPage: false,
        skipReady: true,
        watermark: 'scenario_22 • Level 5',
      });

      await demo.finalize('passed');
    } catch (err) {
      await demo.finalize('failed');
      throw err;
    }
  });
});
