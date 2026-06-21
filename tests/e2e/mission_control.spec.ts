import { test, expect } from '@playwright/test';
import { execFileSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';
import { completeFirstRunOnboarding } from './fixtures/onboarding';
import { ensureSidebarOpen } from './fixtures/sidebar';
import { gotoAndWaitForStreamlitReady } from './fixtures/streamlit_ready';
import { e2eScopeQuery, e2eScopeSeed } from './fixtures/course_scope';

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

function seedFirstSessionArtifactForE2e(): void {
  const root = process.cwd();
  const py = resolveRepoPython(root);
  const seed = e2eScopeSeed();
  const code = `
from app.course_cache import course_scope_hash, save_first_session_artifact

paths = ${JSON.stringify(seed.sourcePaths)}
folder = ${JSON.stringify(seed.folderRel)}
artifact = {
    "course_id": folder,
    "scope_hash": course_scope_hash(paths),
    "built_at": "2026-01-01T00:00:00+00:00",
    "outline_blocks": [],
    "seed_questions": [
        {
            "q": "E2E первый вопрос по курсу",
            "retrieval_trace": {"source_paths": [paths[0]], "chunk_ids": []},
            "draft_answer": None,
        }
    ],
    "baseline_mission": {
        "title": "E2E First Session",
        "primary_cta": "Начать с первого вопроса",
        "deterministic": True,
    },
    "candidate_flashcards": [],
}
save_first_session_artifact(folder, artifact)
`;
  execFileSync(py, ['-c', code], { cwd: root, env: process.env, stdio: 'inherit' });
}

const tiles = [
  'tutor',
  'quiz',
  'flashcards',
  'quick_question',
  'topics',
  'course',
  'adaptive_plan',
];

test.describe('@smoke Mission Control', () => {
  test('@smoke renders SSR banner and seven destination tiles', async ({ page }) => {
    test.setTimeout(180_000);
    await completeFirstRunOnboarding(page);

    await expect(page.locator('[data-testid="mission-control-ssr-banner"]').first()).toBeVisible({
      timeout: 60_000,
    });
    for (const tile of tiles) {
      await expect(page.locator(`[data-testid="mission-tile-${tile}"]`).first()).toBeVisible({
        timeout: 30_000,
      });
    }
    await expect(page.locator('.mode-card.smart-recommended').first()).toBeVisible({
      timeout: 30_000,
    });
  });

  test('@smoke tile navigation shows breadcrumb back to home', async ({ page }) => {
    test.setTimeout(180_000);
    await completeFirstRunOnboarding(page);

    await page.getByRole('button', { name: /Спросить/i }).first().click();
    await expect(page.getByRole('button', { name: /Mission Control/i }).first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByRole('combobox').first()).toHaveAttribute(
      'aria-label',
      /Быстрый ответ/i,
      { timeout: 60_000 },
    );

    await page.getByRole('button', { name: /Mission Control/i }).first().click();
    await expect(page.locator('[data-testid="mission-control-ssr-banner"]').first()).toBeVisible({
      timeout: 60_000,
    });
  });

  test('@smoke sidebar exposes relocated secondary tools', async ({ page }) => {
    test.setTimeout(180_000);
    await completeFirstRunOnboarding(page);
    await ensureSidebarOpen(page);

    const sidebar = page.locator('[data-testid="stSidebar"]');
    const toolsToggle = sidebar.getByText(/Инструменты/i).first();
    await expect(toolsToggle).toBeVisible({ timeout: 60_000 });
    await toolsToggle.click();
    await expect(sidebar.getByRole('button', { name: /История/i }).first()).toBeVisible({
      timeout: 30_000,
    });
    await expect(sidebar.getByRole('button', { name: /Метрики/i }).first()).toBeVisible({
      timeout: 30_000,
    });
  });

  test('@smoke responsive view keeps mission tiles reachable', async ({ page }) => {
    test.setTimeout(180_000);
    await page.setViewportSize({ width: 800, height: 600 });
    await gotoAndWaitForStreamlitReady(page, '/?e2e_view=home');
    await expect(page.locator('[data-testid="mission-tile-tutor"]').first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.locator('[data-testid="mission-tile-adaptive_plan"]').first()).toBeVisible({
      timeout: 60_000,
    });
  });

  test('@smoke cold open shows first session hero without primary chat LLM', async ({ page }) => {
    test.setTimeout(300_000);
    seedFirstSessionArtifactForE2e();
    await gotoAndWaitForStreamlitReady(
      page,
      `/?${e2eScopeQuery({ e2e_view: 'home', e2e_seed_ts: String(Date.now()) })}`,
      240_000,
    );
    await expect(page.locator('[data-testid="first-session-hero"]').first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByRole('heading', { name: /E2E First Session/i }).first()).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.locator('[data-testid="e2e-primary-chat-call-count"]').first()).toHaveText('0');
    await expect(page.locator('[data-testid="mission-control-ssr-banner"]').first()).toBeVisible({
      timeout: 60_000,
    });
  });
});
