import { Page } from '@playwright/test';
import fs from 'node:fs';
import path from 'node:path';
import { DEMO } from './demo_timeouts';
import { waitForStreamlitReady } from './streamlit_ready';

/**
 * Папка прогона: `YYYY-MM-DD` (локальная дата, не UTC).
 */
function localRunFolderName(): string {
  const d = new Date();
  const y = d.getFullYear();
  const mo = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${mo}-${day}`;
}

/** `DEMO_SHOT_RUN` = `YYYY-MM-DD`. */
const DEMO_SHOT_RUN_RE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Корень кадров: `doc/screenshots/<run>/`.
 * Задаётся `DEMO_SHOT_RUN` или новая папка `YYYY-MM-DD` (`localRunFolderName()`).
 * Не задавай `DEMO_SHOT_RUN` на существующий каталог, если папка прогона должна остаться
 * неизменяемым архивом — съём в тот же `<run>` снова очистит `…/<run>/<scenario_id>/`.
 */
export function resolveDemoScreenshotsRoot(): string {
  const fromEnv = process.env.DEMO_SHOT_RUN?.trim();
  const run =
    fromEnv && DEMO_SHOT_RUN_RE.test(fromEnv) ? fromEnv : localRunFolderName();
  return path.resolve(process.cwd(), 'doc', 'screenshots', run);
}

export interface DemoShotMeta {
  step: number;
  slug: string;
  caption?: string;
  narration?: string;
  duration_sec?: number;
  file: string;
  taken_at: string;
  viewport: { width: number; height: number };
  timings_ms?: {
    wait: number;
    streamlit_ready: number;
    screenshot: number;
    total: number;
  };
}

export interface DemoSessionMeta {
  scenario_id: string;
  started_at: string;
  finished_at?: string;
  status: 'running' | 'passed' | 'failed';
  shots: DemoShotMeta[];
  total_duration_ms?: number;
  shot_count?: number;
  timings_summary?: Record<string, { sum: number; avg: number; p95: number }>;
  env: Record<string, string | undefined>;
}

/**
 * `DemoRecorder` — тонкая обёртка над `page.screenshot` для demo-тестов.
 *
 * Каждый вызов `.shot(slug, caption?)` делает PNG в
 * `doc/screenshots/<YYYY-MM-DD>/<scenario_id>/<NN>_<slug>.png` и пишет JSON-метаданные
 * в `.../meta.json`. Каталог дня — `resolveDemoScreenshotsRoot()` / `DEMO_SHOT_RUN`.
 * Этот JSON потом читает
 * `scripts/generate_demo_doc.py` чтобы собрать smart-документ.
 *
 * Префикс `NN_` добавляется автоматически (01_, 02_, ...) — порядок в slug-ах
 * YAML-манифеста не обязателен, но рекомендуется совпадать.
 */
export class DemoRecorder {
  private readonly outDir: string;
  private readonly meta: DemoSessionMeta;
  private readonly testStartedAt = Date.now();
  private readonly perfPath: string;
  private counter = 0;

  constructor(
    private readonly page: Page,
    scenarioId: string,
    rootDir: string = resolveDemoScreenshotsRoot(),
  ) {
    this.outDir = path.join(rootDir, scenarioId);
    this.perfPath = path.join(this.outDir, 'perf.jsonl');
    fs.mkdirSync(this.outDir, { recursive: true });
    this.meta = {
      scenario_id: scenarioId,
      started_at: new Date().toISOString(),
      status: 'running',
      shots: [],
      env: {
        HOME_RAG_E2E_OFFLINE: process.env.HOME_RAG_E2E_OFFLINE,
        E2E_API_PORT: process.env.E2E_API_PORT,
        E2E_STREAMLIT_PORT: process.env.E2E_STREAMLIT_PORT,
      },
    };
    // Чистим предыдущий прогон: старые скрины того же сценария
    for (const name of fs.readdirSync(this.outDir)) {
      if (name.endsWith('.png') || name === 'meta.json' || name === 'perf.jsonl') {
        fs.rmSync(path.join(this.outDir, name), { force: true });
      }
    }
  }

  /**
   * Снять текущий viewport страницы. По умолчанию — только видимая область;
   * передай `{ fullPage: true }` для полной страницы Streamlit.
   */
  async shot(
    slug: string,
    options: {
      caption?: string;
      narration?: string;
      fullPage?: boolean;
      mask?: string[];
      waitMs?: number;
      skipReady?: boolean;
      watermark?: string;
    } = {},
  ): Promise<void> {
    this.counter += 1;
    const prefix = String(this.counter).padStart(2, '0');
    const safeSlug = slug.replace(/[^a-z0-9_.-]/gi, '_');
    // Если slug уже начинается с «NN_» (как в YAML-манифестах) — не добавляем второй префикс,
    // чтобы файл назывался `01_home_mode_selector.png`, а не `01_01_home_mode_selector.png`.
    const hasNumericPrefix = /^\d{2}_/.test(safeSlug);
    const filename = hasNumericPrefix ? `${safeSlug}.png` : `${prefix}_${safeSlug}.png`;
    const absPath = path.join(this.outDir, filename);

    const startedAt = Date.now();
    const waitStartedAt = Date.now();
    if (options.waitMs && options.waitMs > 0) {
      await this.page.waitForTimeout(options.waitMs);
    }
    const readyStartedAt = Date.now();
    // Streamlit может докрашивать интерфейс — даём одному кадру отстояться.
    if (!options.skipReady) {
      await waitForStreamlitReady(this.page, DEMO.streamlitReadyMs).catch(() => undefined);
    }

    const screenshotStartedAt = Date.now();
    const watermarkId = '__demo_shot_watermark__';
    const watermarkText = options.watermark ?? `${this.meta.scenario_id} • step_${prefix}`;
    if (watermarkText) {
      await this.page.evaluate(
        ({ id, text }) => {
          const existing = document.getElementById(id);
          if (existing) existing.remove();
          const badge = document.createElement('div');
          badge.id = id;
          badge.textContent = text;
          badge.setAttribute(
            'style',
            [
              'position:fixed',
              'right:12px',
              'top:12px',
              'z-index:2147483647',
              'padding:4px 8px',
              'border-radius:6px',
              'background:rgba(17,24,39,0.75)',
              'color:#fff',
              'font:600 12px/1.2 system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
              'letter-spacing:.02em',
              'pointer-events:none',
            ].join(';'),
          );
          document.body.appendChild(badge);
        },
        { id: watermarkId, text: watermarkText },
      );
    }
    try {
      await this.page.screenshot({
        path: absPath,
        fullPage: options.fullPage ?? false,
        mask: (options.mask ?? []).map((sel) => this.page.locator(sel)),
        animations: 'disabled',
      });
    } finally {
      if (watermarkText) {
        await this.page
          .evaluate((id) => document.getElementById(id)?.remove(), watermarkId)
          .catch(() => undefined);
      }
    }
    const finishedAt = Date.now();

    const viewport = this.page.viewportSize() ?? { width: 0, height: 0 };
    const timings = {
      wait: readyStartedAt - waitStartedAt,
      streamlit_ready: screenshotStartedAt - readyStartedAt,
      screenshot: finishedAt - screenshotStartedAt,
      total: finishedAt - startedAt,
    };

    const shotMeta: DemoShotMeta = {
      step: this.counter,
      slug: safeSlug,
      caption: options.caption,
      narration: options.narration,
      file: filename,
      taken_at: new Date().toISOString(),
      viewport,
      timings_ms: timings,
    };
    this.meta.shots.push(shotMeta);
    fs.appendFileSync(
      this.perfPath,
      JSON.stringify({
        scenario_id: this.meta.scenario_id,
        step: this.counter,
        slug: safeSlug,
        file: filename,
        timings_ms: timings,
        taken_at: shotMeta.taken_at,
      }) + '\n',
      'utf-8',
    );
  }

  /** Вызывается в afterEach / после всех кадров для фиксации статуса и meta.json. */
  async finalize(status: 'passed' | 'failed' = 'passed'): Promise<void> {
    const metaPath = path.join(this.outDir, 'meta.json');
    if (status === 'failed') {
      // Fail-fast cleanup: stale meta.json must not survive failed runs.
      fs.rmSync(metaPath, { force: true });
      return;
    }
    this.meta.status = status;
    this.meta.finished_at = new Date().toISOString();
    this.meta.total_duration_ms = Date.now() - this.testStartedAt;
    this.meta.shot_count = this.meta.shots.length;
    this.meta.timings_summary = summarizeTimings(this.meta.shots);
    fs.writeFileSync(
      metaPath,
      JSON.stringify(this.meta, null, 2),
      'utf-8',
    );
  }
}

function summarizeTimings(
  shots: DemoShotMeta[],
): Record<string, { sum: number; avg: number; p95: number }> {
  const phases = ['wait', 'streamlit_ready', 'screenshot', 'total'] as const;
  const out: Record<string, { sum: number; avg: number; p95: number }> = {};
  for (const phase of phases) {
    const values = shots
      .map((shot) => shot.timings_ms?.[phase] ?? 0)
      .sort((a, b) => a - b);
    const sum = values.reduce((acc, value) => acc + value, 0);
    const p95Index = values.length ? Math.ceil(values.length * 0.95) - 1 : 0;
    out[phase] = {
      sum,
      avg: values.length ? Math.round(sum / values.length) : 0,
      p95: values.length ? values[Math.max(0, p95Index)] : 0,
    };
  }
  return out;
}

/**
 * Синтаксический сахар: createDemoRecorder(page, 'scenario_01')
 * используется в `test.beforeEach` или в теле теста.
 */
export function createDemoRecorder(page: Page, scenarioId: string): DemoRecorder {
  return new DemoRecorder(page, scenarioId);
}
