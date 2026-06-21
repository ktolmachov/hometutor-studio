/**
 * @smoke API Contract — Learner Goal Snapshot Lifecycle
 *
 * Проверяет:
 *   - PUT /learner/goal-snapshot → create/update
 *   - GET /learner/goal-snapshot → retrieve
 *   - DELETE /learner/goal-snapshot → clear
 *   - Пустой snapshot возвращает null goal_context
 *
 * Работает без LLM — только API.
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

test.describe('@smoke Learner Goal Snapshot Lifecycle', () => {
  test('@smoke PUT → GET → DELETE cycle', async ({ request }) => {
    test.setTimeout(60_000);

    const apiBase = e2eApiOrigin();

    // ── 1. GET initial state (empty) ─────────────────────────────────────────
    const initialRes = await apiRequest(request, 'get', `${apiBase}/learner/goal-snapshot`);
    expect(initialRes.status).toBe(200);
    const initial = initialRes.json as { goal_context: unknown };
    // First run may have no snapshot
    const hasInitial = initial.goal_context !== null && initial.goal_context !== undefined;

    // ── 2. PUT new snapshot ──────────────────────────────────────────────────
    const putRes = await apiRequest(request, 'put', `${apiBase}/learner/goal-snapshot`, {
      topic: 'Python',
      subtopic: 'async/await',
      target_level: 'intermediate',
      desired_outcome: 'Understand concurrent programming',
      time_budget_min: 30,
    });
    expect(putRes.status, `PUT /learner/goal-snapshot → ${putRes.status}`).toBe(200);
    const saved = putRes.json as { goal_context: Record<string, unknown> };
    expect(saved.goal_context).toBeDefined();
    expect(saved.goal_context.topic).toBe('Python');
    expect(saved.goal_context.subtopic).toBe('async/await');
    expect(saved.goal_context.target_level).toBe('intermediate');

    // ── 3. GET returns saved snapshot ────────────────────────────────────────
    const getRes = await apiRequest(request, 'get', `${apiBase}/learner/goal-snapshot`);
    expect(getRes.status).toBe(200);
    const retrieved = getRes.json as { goal_context: Record<string, unknown> };
    expect(retrieved.goal_context.topic).toBe('Python');
    expect(retrieved.goal_context.subtopic).toBe('async/await');
    expect(retrieved.goal_context.desired_outcome).toBe('Understand concurrent programming');
    expect(retrieved.goal_context.time_budget_min).toBe(30);

    // ── 4. PUT update existing ───────────────────────────────────────────────
    const updateRes = await apiRequest(request, 'put', `${apiBase}/learner/goal-snapshot`, {
      topic: 'Python',
      subtopic: 'generators',
      target_level: 'advanced',
    });
    expect(updateRes.status).toBe(200);
    const updated = updateRes.json as { goal_context: Record<string, unknown> };
    expect(updated.goal_context.subtopic).toBe('generators');
    expect(updated.goal_context.target_level).toBe('advanced');

    // ── 5. DELETE clears snapshot ────────────────────────────────────────────
    const deleteRes = await apiRequest(request, 'delete', `${apiBase}/learner/goal-snapshot`);
    expect(deleteRes.status, `DELETE → ${deleteRes.status}`).toBe(200);
    expect(deleteRes.json.status).toBe('cleared');

    // ── 6. GET after delete returns empty ────────────────────────────────────
    const afterDeleteRes = await apiRequest(request, 'get', `${apiBase}/learner/goal-snapshot`);
    expect(afterDeleteRes.status).toBe(200);
    const afterDelete = afterDeleteRes.json as { goal_context: unknown };
    expect(afterDelete.goal_context).toBeNull();

    // ── 7. Restore original state if needed ─────────────────────────────────
    if (hasInitial) {
      await apiRequest(request, 'put', `${apiBase}/learner/goal-snapshot`, initial);
    }
  });

  test('@smoke partial update replaces all fields (not merge)', async ({ request }) => {
    const apiBase = e2eApiOrigin();

    // Set full snapshot first
    await apiRequest(request, 'put', `${apiBase}/learner/goal-snapshot`, {
      topic: 'Math',
      subtopic: 'Calculus',
      target_level: 'beginner',
      desired_outcome: 'Pass exam',
      time_budget_min: 60,
    });

    // Update only one field - other fields should be reset to defaults
    const res = await apiRequest(request, 'put', `${apiBase}/learner/goal-snapshot`, {
      target_level: 'advanced',
    });
    expect(res.status).toBe(200);
    const updated = res.json as { goal_context: Record<string, unknown> };

    // Non-specified fields are replaced with defaults (not preserved)
    expect(updated.goal_context.topic).toBe('general'); // default, not 'Math'
    expect(updated.goal_context.subtopic).toBeNull(); // not 'Calculus'
    expect(updated.goal_context.desired_outcome).toBeNull(); // not 'Pass exam'
    expect(updated.goal_context.time_budget_min).toBeNull(); // not 60
    expect(updated.goal_context.target_level).toBe('advanced');

    // Cleanup
    await apiRequest(request, 'delete', `${apiBase}/learner/goal-snapshot`);
  });
});