import type { Page } from '@playwright/test';

const E2E_SCOPE_FOLDER = 'e2e-course-offline';
const E2E_SCOPE_TITLE = 'E2E Курс (offline)';
const E2E_SCOPE_PATHS = [
  'e2e-course-offline/doc-1.md',
  'e2e-course-offline/doc-2.md',
];

export function e2eScopeSeed() {
  return {
    folderRel: E2E_SCOPE_FOLDER,
    title: E2E_SCOPE_TITLE,
    sourcePaths: E2E_SCOPE_PATHS,
  };
}

export function e2eScopeQuery(extra?: Record<string, string>) {
  const params = new URLSearchParams({
    e2e_scope_folder: E2E_SCOPE_FOLDER,
    e2e_scope_title: E2E_SCOPE_TITLE,
    e2e_scope_paths: E2E_SCOPE_PATHS.join(','),
    ...(extra || {}),
  });
  return params.toString();
}

export async function ensureCourseScopeAvailable(page: Page): Promise<boolean> {
  const params = new URLSearchParams({
    e2e_view: 'qa',
    e2e_scope_folder: E2E_SCOPE_FOLDER,
    e2e_scope_title: E2E_SCOPE_TITLE,
    e2e_scope_paths: E2E_SCOPE_PATHS.join(','),
    e2e_seed_ts: String(Date.now()),
  });
  await page.goto(`/?${params.toString()}`, { waitUntil: 'domcontentloaded' });
  return true;
}
