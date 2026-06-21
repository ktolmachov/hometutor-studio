import { execFileSync } from 'node:child_process';
import * as fs from 'node:fs';
import * as path from 'node:path';

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

/**
 * Seeds deterministic adaptive plan KV so «Что изменилось в плане» shows added/removed lines.
 * Must match Streamlit `--server` DB (defaults to `.e2e/state-main.db` in PR smoke stack).
 */
export function seedAdaptivePlanConceptsDeltaE2eDb(dbPath?: string): void {
  const root = process.cwd();
  const raw =
    dbPath?.trim() ||
    (process.env.USER_STATE_DB ?? '').trim() ||
    path.join(root, '.e2e', 'state-main.db');
  const abs = path.isAbsolute(raw) ? raw : path.resolve(root, raw);
  const py = resolveRepoPython(root);
  const script = path.join(root, 'tests', 'e2e', 'fixtures', 'seed_adaptive_plan_diff_kv.py');
  execFileSync(py, [script, abs], { cwd: root, stdio: 'inherit', env: process.env });
}
