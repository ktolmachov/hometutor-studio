/**
 * @smoke Session Persistence — Multi-turn Save/Restore
 *
 * Проверяет:
 *   - GET /sessions/{session_id} returns 404 for non-existent
 *   - DELETE /sessions/{session_id} returns 200 even if not exists (idempotent)
 *   - GET /sessions returns list of sessions
 *
 * Note: Сессии создаются только через /ask с успешным ответом LLM.
 * В offline-режиме полный цикл не тестируется — только базовые операции.
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
  const res = await request[method as 'get' | 'post' | 'put' | 'delete' | 'patch'](url, {
    timeout,
    data: body,
  });
  const json = res.ok() ? ((await res.json()) as Record<string, unknown>) : {};
  return { status: res.status(), json };
}

test.describe('@smoke Session Persistence', () => {
  test('@smoke non-existent session returns 404', async ({ request }) => {
    const apiBase = e2eApiOrigin();
    const res = await apiRequest(request, 'get', `${apiBase}/sessions/does-not-exist-12345`);
    expect(res.status).toBe(404);
  });

  test('@smoke delete non-existent session is idempotent', async ({ request }) => {
    const apiBase = e2eApiOrigin();
    // Delete non-existent should return 200 (idempotent)
    const res = await apiRequest(request, 'delete', `${apiBase}/sessions/non-existent-12345`);
    expect(res.status).toBe(200);
  });

  test('@smoke list sessions endpoint works', async ({ request }) => {
    const apiBase = e2eApiOrigin();
    
    const listRes = await apiRequest(request, 'get', `${apiBase}/sessions?limit=10`);
    expect(listRes.status).toBe(200);
    
    const sessions = listRes.json as Array<{ session_id: string; last_updated: string }>;
    expect(Array.isArray(sessions), 'Should return array').toBe(true);
    
    // If there are sessions, verify structure
    if (sessions.length > 0) {
      expect(sessions[0].session_id).toBeDefined();
      expect(sessions[0].last_updated).toBeDefined();
    }
  });

  test('@smoke session store returns proper record structure', async ({ request }) => {
    const apiBase = e2eApiOrigin();
    
    // First get sessions list
    const listRes = await apiRequest(request, 'get', `${apiBase}/sessions?limit=1`);
    expect(listRes.status).toBe(200);
    
    const sessions = listRes.json as Array<{ session_id: string }>;
    
    if (sessions.length > 0) {
      // If there are sessions, verify get works
      const getRes = await apiRequest(request, 'get', `${apiBase}/sessions/${sessions[0].session_id}`);
      expect(getRes.status).toBe(200);
      
      const session = getRes.json as {
        session_id: string;
        messages: unknown[];
        metadata: unknown;
        last_updated: string;
        created_at: string;
      };
      expect(session.session_id).toBe(sessions[0].session_id);
      expect(session.messages).toBeDefined();
      expect(session.metadata).toBeDefined();
      expect(session.last_updated).toBeDefined();
      expect(session.created_at).toBeDefined();
    }
  });
});