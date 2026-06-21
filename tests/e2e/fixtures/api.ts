/**
 * Базовый URL FastAPI для вызовов из `page.evaluate`: страница живёт на Streamlit
 * (PLAYWRIGHT_BASE_URL, обычно :8501), относительный `fetch('/…')` попадает в HTML UI, не в API.
 * Должен совпадать с `scripts/e2e_run_stack.mjs` (E2E_API_HOST / E2E_API_PORT).
 */
export function e2eApiOrigin(): string {
  const host = process.env.E2E_API_HOST ?? '127.0.0.1';
  const port = process.env.E2E_API_PORT ?? '18000';
  return `http://${host}:${port}`;
}
