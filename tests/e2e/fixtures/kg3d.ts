import type { Frame, Locator, Page } from '@playwright/test';
import { DEMO } from './demo_timeouts';
import { gotoAndWaitForStreamlitReady, waitForStreamlitReady } from './streamlit_ready';

export async function openKnowledgeGraph(page: Page): Promise<void> {
  await gotoAndWaitForStreamlitReady(page, '/?e2e_view=kg');
  await page
    .getByText(/Knowledge Graph|граф|подграф|3D/i)
    .first()
    .waitFor({ state: 'visible', timeout: DEMO.visibleMs })
    .catch(() => undefined);
  await waitForStreamlitReady(page);
}

export async function findFrameWithSelector(
  page: Page,
  selector: string,
  label: string,
  timeoutMs = DEMO.visibleMs,
): Promise<Frame> {
  const deadline = Date.now() + timeoutMs;
  let scannedFrames = 0;
  while (Date.now() < deadline) {
    const frames = page.frames();
    scannedFrames = frames.length;
    for (const frame of frames) {
      const match = frame.locator(selector).first();
      if (await match.count().catch(() => 0)) {
        return frame;
      }
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`${label} not found in any Playwright frame; scanned ${scannedFrames} frame(s).`);
}

export async function findKg3dFrame(page: Page, timeoutMs = DEMO.visibleMs): Promise<Frame> {
  const selectors = [
    '#topbar',
    '.kgx-action-primary',
    '#onboard',
    '.stop-check',
    'canvas',
  ];
  const deadline = Date.now() + timeoutMs;
  let lastError: unknown;
  while (Date.now() < deadline) {
    for (const selector of selectors) {
      try {
        const frame = await findFrameWithSelector(page, selector, `KG 3D selector ${selector}`, 1_000);
        const hasCanvas = await frame.locator('canvas').first().isVisible({ timeout: 500 }).catch(() => false);
        const has3dUi = await frame
          .locator('#topbar, #side, .kgx-action-primary, #onboard, .stop-check')
          .first()
          .isVisible({ timeout: 500 })
          .catch(() => false);
        if (hasCanvas && has3dUi) return frame;
      } catch (err) {
        lastError = err;
      }
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`KG 3D frame not found. Last probe error: ${String(lastError ?? 'none')}`);
}

export async function firstVisible(
  locators: Locator[],
  timeoutMs = 1_500,
): Promise<Locator | null> {
  for (const locator of locators) {
    if (await locator.first().isVisible({ timeout: timeoutMs }).catch(() => false)) {
      return locator.first();
    }
  }
  return null;
}

export async function clickFirstVisible(
  locators: Locator[],
  label: string,
  timeoutMs = DEMO.visibleMs,
): Promise<Locator> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const target = await firstVisible(locators, 500);
    if (target) {
      await target.click({ timeout: 5_000 });
      return target;
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`${label} was not visible.`);
}

export async function canvasHasNonBlankPixels(frame: Frame): Promise<boolean> {
  return frame.locator('canvas').first().evaluate((canvas: HTMLCanvasElement) => {
    const ctx = canvas.getContext('2d');
    if (!ctx || canvas.width <= 0 || canvas.height <= 0) return false;
    const sampleW = Math.min(canvas.width, 120);
    const sampleH = Math.min(canvas.height, 120);
    const x = Math.max(0, Math.floor((canvas.width - sampleW) / 2));
    const y = Math.max(0, Math.floor((canvas.height - sampleH) / 2));
    const data = ctx.getImageData(x, y, sampleW, sampleH).data;
    let nonTransparent = 0;
    let nonBackground = 0;
    for (let i = 0; i < data.length; i += 4) {
      const r = data[i] ?? 0;
      const g = data[i + 1] ?? 0;
      const b = data[i + 2] ?? 0;
      const a = data[i + 3] ?? 0;
      if (a > 0) nonTransparent += 1;
      if (a > 0 && (r > 25 || g > 25 || b > 25)) nonBackground += 1;
    }
    return nonTransparent > 0 && nonBackground > 20;
  });
}

export function collectButtons(frame: Frame): Locator[] {
  return [
    frame.getByRole('button', { name: /В конспект|Собрать|Collect/i }).first(),
    frame.locator('[data-action="collect"], .kgx-action-collect, .kgx-action-primary').first(),
  ];
}

export function startButtons(frame: Frame): Locator[] {
  return [
    frame.getByRole('button', { name: /Начать|Start|Учить|Quiz|Квиз|Flashcards|Карточки/i }).first(),
    frame.locator('[data-action="start"], .kgx-action-start, .kgx-action-primary').first(),
  ];
}
