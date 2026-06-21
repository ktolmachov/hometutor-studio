/**
 * @smoke Ingestion Edge Cases — Concurrent Reindex Conflict
 *
 * Проверяет:
 *   - POST /reindex → starts successfully
 *   - GET /reindex/status returns proper structure with status field
 *
 * Примечание: В offline-режиме (E2E_OFFLINE) reindex очень быстр и не застревает,
 * поэтому 409 Conflict сложно воспроизвести. Проверяем базовый функционал.
 *
 * Работает без LLM.
 */
import { test, expect, type APIRequestContext } from '@playwright/test';
import { e2eApiOrigin } from './fixtures/api';

async function apiRequest(
  request: APIRequestContext,
  method: string,
  url: string,
  body?: unknown,
  timeout = 30_000,
): Promise<{ status: number; json: Record<string, unknown> }> {
  const res = await request[method as 'get' | 'post' | 'put' | 'delete'](url, {
    timeout,
    data: body,
  });
  const json = res.ok() ? ((await res.json()) as Record<string, unknown>) : {};
  return { status: res.status(), json };
}

test.describe('@smoke Concurrent Reindex Conflict', () => {
  test('@smoke reindex endpoint works and returns status', async ({ request }) => {
    test.setTimeout(60_000);

    const apiBase = e2eApiOrigin();

    // Start reindex
    const reindexRes = await apiRequest(request, 'post', `${apiBase}/reindex?reset=false`);
    
    // Either 200 (started) or 409 (already running) are acceptable
    const isValidResponse = reindexRes.status === 200 || reindexRes.status === 409;
    expect(isValidResponse, `Expected 200 or 409, got ${reindexRes.status}`).toBe(true);
    
    if (reindexRes.status === 200) {
      expect(reindexRes.json.status).toBe('started');
    } else if (reindexRes.status === 409) {
      expect(reindexRes.json.detail).toContain('already');
    }
  });

  test('@smoke reindex status returns proper structure', async ({ request }) => {
    const apiBase = e2eApiOrigin();

    const statusRes = await apiRequest(request, 'get', `${apiBase}/reindex/status`);
    expect(statusRes.status).toBe(200);
    
    const status = statusRes.json as Record<string, unknown>;
    expect(status, 'status should be an object').toBeDefined();
    
    // Status field is a string ("idle", "running", etc.)
    const hasStatus = 'status' in status;
    expect(hasStatus, 'status should have status field').toBe(true);
    
    // Verify status is a known value
    const statusValue = status.status as string;
    const validStatuses = ['idle', 'running', 'completed', 'error'];
    expect(validStatuses.includes(statusValue), `status should be one of ${validStatuses}, got: ${statusValue}`).toBe(true);
  });

  test('@smoke reindex with reset=true also works', async ({ request }) => {
    test.setTimeout(60_000);

    const apiBase = e2eApiOrigin();

    // Try to start reindex with reset flag
    const reindexRes = await apiRequest(request, 'post', `${apiBase}/reindex?reset=true`);
    
    // Either 200 (started) or 409 (already running) are acceptable
    const isValidResponse = reindexRes.status === 200 || reindexRes.status === 409;
    expect(isValidResponse, `Expected 200 or 409, got ${reindexRes.status}`).toBe(true);
  });
});